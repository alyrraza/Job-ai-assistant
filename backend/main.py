# FastAPI app ka main entry point — saare public API endpoints yahan hain.
# WebSocket se real-time pipeline progress frontend ko milti hai.
# Supervisor MCP /supervisor prefix pe mount hai — internal orchestration.

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.database.models import init_db
from backend.supervisor.mcp_server import (
    _PipelineSession,
    _run_pipeline_step,
    _sessions,
    _sessions_lock,
    mcp_app,
)
from backend.supervisor.router import PipelineState, get_next_agent_name
from backend.utils.config import get_settings
from backend.utils.logger import logger

settings = get_settings()


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class WebSocketManager:
    """Session-keyed WebSocket connections — broadcast pipeline state to all subscribers."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(session_id, set()).add(ws)
        logger.debug(f"[WS] Client connected: session={session_id}")

    def disconnect(self, session_id: str, ws: WebSocket) -> None:
        if session_id in self._connections:
            self._connections[session_id].discard(ws)
        logger.debug(f"[WS] Client disconnected: session={session_id}")

    async def broadcast(self, session_id: str, data: dict[str, Any]) -> None:
        conns = self._connections.get(session_id, set()).copy()
        dead: set[WebSocket] = set()
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections[session_id].discard(ws)


ws_manager = WebSocketManager()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: DB init. Shutdown: log."""
    logger.info("CV Interview Coach backend starting...")
    init_db()
    logger.success("Database tables ready.")
    yield
    logger.info("Backend shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CV Interview Coach API",
    description="Multi-agent AI: CV analyze → questions generate → voice interview",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount supervisor at /supervisor
app.mount("/supervisor", mcp_app)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    cv_text: str = Field(..., min_length=50, description="Raw CV/resume text")
    jd_text: str = Field(..., min_length=30, description="Job description text")


class AnalyzeResponse(BaseModel):
    session_id: str
    message: str


class StatusResponse(BaseModel):
    session_id: str
    state: str
    agent1_done: bool
    agent2_done: bool
    agent3_done: bool
    questions_ready: bool
    interview_completed: bool
    error: str | None


class ResultsResponse(BaseModel):
    session_id: str
    state: str
    analysis: dict[str, Any] | None        # Agent 1 output
    questions: dict[str, Any] | None       # Agent 2 output
    interview_report: dict[str, Any] | None  # Agent 3 output
    error: str | None


class InterviewStartResponse(BaseModel):
    session_id: str
    status: str
    room_name: str
    livekit_token: str
    livekit_url: str


# ---------------------------------------------------------------------------
# Background task: run pipeline + broadcast WS on state changes
# ---------------------------------------------------------------------------

async def _dispatch_with_broadcast(session_id: str, agent_name: str) -> None:
    """
    Pipeline step chalao aur har state change pe WebSocket clients ko update karo.
    """
    await _run_pipeline_step(session_id, agent_name)
    session = _sessions.get(session_id)
    if session:
        await ws_manager.broadcast(
            session_id,
            _session_ws_payload(session),
        )


def _session_ws_payload(session: _PipelineSession) -> dict[str, Any]:
    return {
        "type": "state_update",
        "state": session.state.value,
        "agent1_done": session.agent1_result is not None,
        "agent2_done": session.agent2_result is not None,
        "agent3_done": session.agent3_result is not None,
        "questions_ready": session.state in (
            PipelineState.AGENT2_DONE,
            PipelineState.AGENT3_READY,
            PipelineState.AGENT3_RUNNING,
            PipelineState.COMPLETED,
        ),
        "interview_completed": session.state == PipelineState.COMPLETED,
        "error": session.error,
    }


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    """Quick health check."""
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks) -> AnalyzeResponse:
    """
    CV + JD text lo → pipeline shuru karo → session_id return karo.
    Agent 1 (CV Analyzer) + Agent 2 (Question Generator) background mein chalte hain.
    """
    session_id = str(uuid.uuid4())

    async with _sessions_lock:
        session = _PipelineSession(
            session_id=session_id,
            input_data={"cv_text": request.cv_text, "jd_text": request.jd_text},
        )
        _sessions[session_id] = session
        logger.info(f"[API] New analysis session: {session_id}")

    first_agent = get_next_agent_name(PipelineState.IDLE)
    background_tasks.add_task(_dispatch_with_broadcast, session_id, first_agent)

    return AnalyzeResponse(
        session_id=session_id,
        message=f"Analysis started. Poll /api/status/{session_id} for progress.",
    )


@app.get("/api/status/{session_id}", response_model=StatusResponse)
async def get_status(session_id: str) -> StatusResponse:
    """
    Current pipeline state — frontend polling ya WS fallback ke liye.
    """
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return StatusResponse(
        session_id=session_id,
        state=session.state.value,
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
    )


@app.get("/api/results/{session_id}", response_model=ResultsResponse)
async def get_results(session_id: str) -> ResultsResponse:
    """
    Full pipeline results — analysis, questions, interview report.
    Partial results (only agent1 done) bhi return ho sakte hain.
    """
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return ResultsResponse(
        session_id=session_id,
        state=session.state.value,
        analysis=_strip_internal(session.agent1_result),
        questions=session.agent2_result,
        interview_report=session.agent3_result,
        error=session.error,
    )


@app.post("/api/interview/start/{session_id}", response_model=InterviewStartResponse)
async def start_interview(
    session_id: str, background_tasks: BackgroundTasks
) -> InterviewStartResponse:
    """
    Agent 3 (Voice Interview) ko trigger karo.
    Agent 2 pehle complete hona chahiye (questions ready state).
    LiveKit token frontend ko return hota hai.
    """
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if session.agent2_result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Questions not ready yet. Wait for Agent 2 to complete.",
        )

    if session.state == PipelineState.AGENT3_RUNNING:
        raise HTTPException(status_code=409, detail="Interview already in progress.")

    if session.state == PipelineState.COMPLETED:
        raise HTTPException(status_code=409, detail="Interview already completed.")

    # Generate LiveKit token for frontend (if LiveKit configured)
    livekit_token: str = ""
    livekit_url: str = settings.livekit_url or ""
    room_name = f"interview-{session_id[:8]}"
    try:
        from backend.voice.livekit_manager import LiveKitManager
        mgr = LiveKitManager(session_id=session_id)
        livekit_token = mgr.create_frontend_token()
    except Exception as exc:
        # livekit_url intentionally NOT cleared — URL is still valid even if token fails
        logger.warning(f"[API] LiveKit token generation failed (non-fatal): {exc}")

    logger.info(f"LiveKit URL from config: {settings.livekit_url}")
    logger.info(f"LiveKit API Key: {settings.livekit_api_key[:5] if settings.livekit_api_key else 'EMPTY'}")
    logger.info(f"Token generated: {livekit_token[:20] if livekit_token else 'EMPTY'}")
    response_dict = {
        "status": "started",
        "livekit_token": (livekit_token[:20] + "...") if livekit_token else "",
        "livekit_url": livekit_url,
    }
    logger.info(f"Response being sent: {response_dict}")

    # Dispatch Agent 3 with questions as input
    agent3_input = {**session.agent2_result}
    background_tasks.add_task(_run_agent3_with_broadcast, session_id, agent3_input)

    return InterviewStartResponse(
        session_id=session_id,
        status="started",
        room_name=room_name,
        livekit_token=livekit_token,
        livekit_url=livekit_url,
    )


async def _run_agent3_with_broadcast(session_id: str, input_data: dict[str, Any]) -> None:
    """Agent 3 run karo aur WS clients ko notify karo."""
    session = _sessions.get(session_id)
    if not session:
        return
    async with session.lock:
        session.state = PipelineState.AGENT3_RUNNING
        session.touch()

    from backend.supervisor.router import run_agent
    try:
        result = await asyncio.to_thread(run_agent, "voice_interview", session_id, input_data)
    except Exception as exc:
        logger.error(f"[API] Agent 3 crashed: {exc}")
        async with session.lock:
            session.state = PipelineState.FAILED
            session.error = str(exc)
            session.touch()
        await ws_manager.broadcast(session_id, _session_ws_payload(session))
        return

    async with session.lock:
        if result.success:
            session.agent3_result = result.data
            session.state = PipelineState.COMPLETED
        else:
            session.state = PipelineState.FAILED
            session.error = result.error
        session.touch()

    await ws_manager.broadcast(session_id, _session_ws_payload(session))
    logger.info(f"[API] Agent 3 done: session={session_id} state={session.state.value}")


# ---------------------------------------------------------------------------
# WebSocket — real-time pipeline state stream
# ---------------------------------------------------------------------------

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """
    Connect karo → pipeline state ka live stream milega.
    Har 500ms pe state check hoti hai aur sirf changed state broadcast hoti hai.
    """
    await ws_manager.connect(session_id, websocket)
    last_state: str | None = None

    try:
        while True:
            session = _sessions.get(session_id)
            if session:
                current_state = session.state.value
                if current_state != last_state:
                    last_state = current_state
                    await websocket.send_json(_session_ws_payload(session))

                # Stop polling when terminal state reached
                if session.state in (PipelineState.COMPLETED, PipelineState.FAILED):
                    await websocket.send_json({"type": "done", "state": current_state})
                    break
            else:
                await websocket.send_json({"type": "error", "message": "Session not found"})
                break

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(session_id, websocket)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _strip_internal(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """_cv_parsed, _jd_parsed jaise internal keys frontend ko mat bhejo."""
    if data is None:
        return None
    return {k: v for k, v in data.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
