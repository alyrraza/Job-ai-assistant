# Yeh Supervisor MCP Server hai — poori pipeline ka orchestrator.
# State machine yahan manage hoti hai: IDLE → Agent1 → Agent2 → AGENT3_READY.
# POST /dispatch se pipeline shuru hoti hai, /status se progress check karte hain.

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from backend.supervisor.router import (
    PipelineState,
    detect_parallel_ready,
    get_next_agent_name,
    get_running_state,
    run_agent,
    should_auto_advance,
    transition_on_failure,
    transition_on_success,
)
from backend.utils.logger import logger

# ---------------------------------------------------------------------------
# In-memory session store — production mein Redis ya DB se replace karo
# ---------------------------------------------------------------------------

class _PipelineSession:
    """Ek session ki complete state — thread-safe access ke liye lock attach hai."""

    def __init__(self, session_id: str, input_data: dict[str, Any]) -> None:
        self.session_id = session_id
        self.state = PipelineState.IDLE
        self.input_data = input_data

        self.agent1_result: Optional[dict] = None
        self.agent2_result: Optional[dict] = None
        self.agent3_result: Optional[dict] = None

        self.escalations: list[dict] = []
        self.error: Optional[str] = None

        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.lock = asyncio.Lock()

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "agent1_result": self.agent1_result,
            "agent2_result": self.agent2_result,
            "agent3_result": self.agent3_result,
            "error": self.error,
            "escalations": self.escalations,
            "parallel_ready": detect_parallel_ready(self.state),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


_sessions: dict[str, _PipelineSession] = {}
_sessions_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class DispatchRequest(BaseModel):
    """POST /dispatch — pipeline shuru karo ya specific agent chalao."""
    session_id: str = Field(..., min_length=1)
    cv_text: str = Field(..., min_length=10)
    jd_text: str = Field(..., min_length=10)
    force_agent: Optional[str] = Field(
        None,
        description="Specific agent name force karo — normally auto-routed"
    )


class DispatchResponse(BaseModel):
    session_id: str
    agent_dispatched: str
    pipeline_state: str
    message: str


class ReportRequest(BaseModel):
    """POST /report — agent apna result wapas bhejta hai."""
    session_id: str
    agent_name: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    mlflow_run_id: Optional[str] = None


class ReportResponse(BaseModel):
    session_id: str
    pipeline_state: str
    next_action: str  # "continue" | "wait_for_user" | "completed" | "failed"
    message: str


class StatusResponse(BaseModel):
    session_id: str
    pipeline_state: str
    agent1_done: bool
    agent2_done: bool
    agent3_done: bool
    questions_ready: bool
    interview_completed: bool
    error: Optional[str]
    parallel_ready: list[str]
    updated_at: str


class EscalateRequest(BaseModel):
    """POST /escalate — agent max retries hit, supervisor ko batao."""
    session_id: str
    agent_name: str
    error_message: str
    attempt_count: int


class EscalateResponse(BaseModel):
    session_id: str
    pipeline_state: str
    action_taken: str


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

mcp_app = FastAPI(
    title="CV Interview Coach — Supervisor MCP",
    description="Pipeline state machine + agent orchestration",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Helper: get or 404
# ---------------------------------------------------------------------------

def _get_session(session_id: str) -> _PipelineSession:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found. Call /dispatch first.",
        )
    return session


# ---------------------------------------------------------------------------
# Background task: runs agent pipeline steps
# ---------------------------------------------------------------------------

async def _run_pipeline_step(session_id: str, agent_name: str) -> None:
    """
    Background mein agent chalao, result /report pe POST karo.
    Thread-blocking run_agent ko asyncio.to_thread mein wrap kiya hai.
    """
    session = _sessions.get(session_id)
    if not session:
        logger.error(f"[MCP] Background task: session {session_id} not found")
        return

    # Set running state
    async with session.lock:
        running_state = get_running_state(agent_name)
        if running_state:
            session.state = running_state
            session.touch()
        input_data = {**session.input_data}
        # Inject agent1 output as input for agent2
        if agent_name == "question_generator" and session.agent1_result:
            input_data = {**input_data, **session.agent1_result}

    logger.info(f"[MCP] Dispatching {agent_name} | session={session_id}")

    try:
        result = await asyncio.to_thread(run_agent, agent_name, session_id, input_data)
    except Exception as exc:
        logger.error(f"[MCP] Agent {agent_name} crashed: {exc}")
        async with session.lock:
            session.state = PipelineState.FAILED
            session.error = str(exc)
            session.touch()
        return

    # Store result and advance state
    async with session.lock:
        if result.success:
            _store_agent_result(session, agent_name, result.data)
            new_state = transition_on_success(session.state)
            session.state = new_state
            session.touch()
            logger.success(
                f"[MCP] {agent_name} succeeded → state={new_state.value} | session={session_id}"
            )
            # Auto-advance if needed (agent1_done → immediately start agent2)
            if should_auto_advance(new_state):
                next_agent = get_next_agent_name(new_state)
                if next_agent:
                    logger.info(f"[MCP] Auto-advancing to {next_agent}")
        else:
            session.state = transition_on_failure(session.state)
            session.error = result.error
            session.touch()
            logger.error(
                f"[MCP] {agent_name} failed → state=failed | session={session_id} | err={result.error}"
            )
            return

    # Auto-advance outside lock
    if should_auto_advance(new_state):
        next_agent = get_next_agent_name(new_state)
        if next_agent:
            asyncio.ensure_future(_run_pipeline_step(session_id, next_agent))


def _store_agent_result(session: _PipelineSession, agent_name: str, data: dict) -> None:
    """Agent result ko correct slot mein store karo."""
    if agent_name == "cv_analyzer":
        session.agent1_result = data
    elif agent_name == "question_generator":
        session.agent2_result = data
    elif agent_name == "voice_interview":
        session.agent3_result = data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@mcp_app.post("/dispatch", response_model=DispatchResponse)
async def dispatch(request: DispatchRequest, background_tasks: BackgroundTasks) -> DispatchResponse:
    """
    Pipeline shuru karo ya existing session resume karo.
    New session banao → state IDLE → Agent 1 background mein chalao.
    """
    async with _sessions_lock:
        session = _sessions.get(request.session_id)
        if session is None:
            session = _PipelineSession(
                session_id=request.session_id,
                input_data={"cv_text": request.cv_text, "jd_text": request.jd_text},
            )
            _sessions[request.session_id] = session
            logger.info(f"[MCP] New session created: {request.session_id}")

    # Determine which agent to run
    if request.force_agent:
        agent_name = request.force_agent
    else:
        agent_name = get_next_agent_name(session.state)
        if not agent_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot dispatch in state '{session.state.value}'. "
                       f"Pipeline may already be running or completed.",
            )

    background_tasks.add_task(_run_pipeline_step, request.session_id, agent_name)

    return DispatchResponse(
        session_id=request.session_id,
        agent_dispatched=agent_name,
        pipeline_state=session.state.value,
        message=f"Agent '{agent_name}' dispatched in background. Poll /status for progress.",
    )


@mcp_app.post("/report", response_model=ReportResponse)
async def report(request: ReportRequest) -> ReportResponse:
    """
    Agent apna result yahan bhejta hai.
    State machine advance hoti hai aur next action decide hota hai.
    """
    session = _get_session(request.session_id)

    async with session.lock:
        if request.success:
            _store_agent_result(session, request.agent_name, request.data)
            new_state = transition_on_success(session.state)
            session.state = new_state
        else:
            session.state = transition_on_failure(session.state)
            session.error = request.error
        session.touch()

    # Determine next action for caller
    if not request.success:
        next_action = "failed"
        msg = f"Agent {request.agent_name} failed: {request.error}"
    elif session.state == PipelineState.AGENT2_DONE:
        next_action = "wait_for_user"
        msg = "Questions ready. User can start voice interview."
        async with session.lock:
            session.state = PipelineState.AGENT3_READY
    elif session.state == PipelineState.COMPLETED:
        next_action = "completed"
        msg = "Full pipeline completed."
    elif should_auto_advance(session.state):
        next_action = "continue"
        msg = f"Auto-advancing pipeline. Next: {get_next_agent_name(session.state)}"
    else:
        next_action = "continue"
        msg = f"State advanced to {session.state.value}"

    return ReportResponse(
        session_id=request.session_id,
        pipeline_state=session.state.value,
        next_action=next_action,
        message=msg,
    )


@mcp_app.get("/status", response_model=StatusResponse)
async def get_status(session_id: str) -> StatusResponse:
    """Current pipeline state do — frontend polling ke liye."""
    session = _get_session(session_id)
    return StatusResponse(
        session_id=session_id,
        pipeline_state=session.state.value,
        agent1_done=session.agent1_result is not None,
        agent2_done=session.agent2_result is not None,
        agent3_done=session.agent3_result is not None,
        questions_ready=session.state in (
            PipelineState.AGENT2_DONE,
            PipelineState.AGENT3_READY,
            PipelineState.AGENT3_RUNNING,
            PipelineState.COMPLETED,
        ),
        interview_completed=session.state == PipelineState.COMPLETED,
        error=session.error,
        parallel_ready=detect_parallel_ready(session.state),
        updated_at=session.updated_at.isoformat(),
    )


@mcp_app.get("/status/full")
async def get_full_status(session_id: str) -> dict[str, Any]:
    """Debug endpoint — full session data including agent results."""
    session = _get_session(session_id)
    return session.to_dict()


@mcp_app.post("/escalate", response_model=EscalateResponse)
async def escalate(request: EscalateRequest) -> EscalateResponse:
    """
    Agent max retries ke baad yahan notify karta hai.
    Supervisor pipeline ko FAILED state mein le jaata hai.
    """
    session = _get_session(request.session_id)

    async with session.lock:
        escalation_record = {
            "agent_name": request.agent_name,
            "error_message": request.error_message,
            "attempt_count": request.attempt_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        session.escalations.append(escalation_record)
        session.state = PipelineState.FAILED
        session.error = f"[ESCALATED] {request.agent_name}: {request.error_message}"
        session.touch()

    logger.critical(
        f"[MCP] ESCALATION received: agent={request.agent_name} | "
        f"attempts={request.attempt_count} | session={request.session_id} | "
        f"error={request.error_message}"
    )

    return EscalateResponse(
        session_id=request.session_id,
        pipeline_state=PipelineState.FAILED.value,
        action_taken=(
            f"Pipeline marked FAILED after {request.attempt_count} attempts "
            f"by {request.agent_name}. Manual intervention required."
        ),
    )


@mcp_app.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str) -> None:
    """Session cleanup — testing ke liye ya explicit reset."""
    async with _sessions_lock:
        if session_id not in _sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        del _sessions[session_id]
    logger.info(f"[MCP] Session deleted: {session_id}")


@mcp_app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "active_sessions": len(_sessions),
        "states": {sid: s.state.value for sid, s in _sessions.items()},
    }
