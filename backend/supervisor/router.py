# Implements the dynamic routing logic — the supervisor's "brain".
# Looks at the current pipeline state and decides which agent runs next.
# Agent classes are imported here, not in mcp_server.py — to avoid circular imports.

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from backend.agents.base_agent import AgentResult
from backend.agents.cv_analyzer.agent import CVAnalyzerAgent
from backend.agents.question_generator.agent import QuestionGeneratorAgent
from backend.agents.voice_interview.agent import VoiceInterviewAgent
from backend.utils.logger import logger


# ---------------------------------------------------------------------------
# Pipeline state machine
# ---------------------------------------------------------------------------

class PipelineState(str, Enum):
    IDLE = "idle"
    AGENT1_RUNNING = "agent1_running"
    AGENT1_DONE = "agent1_done"
    AGENT2_RUNNING = "agent2_running"
    AGENT2_DONE = "agent2_done"
    AGENT3_READY = "agent3_ready"      # Questions ready, waiting for user to start voice
    AGENT3_RUNNING = "agent3_running"
    COMPLETED = "completed"
    FAILED = "failed"


# Transition table: current state → next state after agent success
_SUCCESS_TRANSITIONS: dict[PipelineState, PipelineState] = {
    PipelineState.AGENT1_RUNNING: PipelineState.AGENT1_DONE,
    PipelineState.AGENT2_RUNNING: PipelineState.AGENT2_DONE,
    PipelineState.AGENT3_RUNNING: PipelineState.COMPLETED,
}

# Which agent runs in each state
_STATE_TO_AGENT: dict[PipelineState, str] = {
    PipelineState.IDLE: "cv_analyzer",
    PipelineState.AGENT1_DONE: "question_generator",
    PipelineState.AGENT3_READY: "voice_interview",
}

# After agent1_done, auto-advance to agent2 (no user gate)
# After agent2_done, wait for user to start voice interview (user gate)
_AUTO_ADVANCE_STATES: set[PipelineState] = {PipelineState.AGENT1_DONE}


def get_next_agent_name(state: PipelineState) -> Optional[str]:
    """Which agent runs after the current state — None means none."""
    return _STATE_TO_AGENT.get(state)


def get_running_state(agent_name: str) -> Optional[PipelineState]:
    """Return the running state for an agent name."""
    mapping = {
        "cv_analyzer": PipelineState.AGENT1_RUNNING,
        "question_generator": PipelineState.AGENT2_RUNNING,
        "voice_interview": PipelineState.AGENT3_RUNNING,
    }
    return mapping.get(agent_name)


def should_auto_advance(state: PipelineState) -> bool:
    """Should the next agent run automatically after this state?"""
    return state in _AUTO_ADVANCE_STATES


def transition_on_success(state: PipelineState) -> PipelineState:
    """What the next state will be after success."""
    return _SUCCESS_TRANSITIONS.get(state, PipelineState.FAILED)


def transition_on_failure(state: PipelineState) -> PipelineState:
    """FAILED state when any running state fails."""
    return PipelineState.FAILED


# ---------------------------------------------------------------------------
# Agent factory — instantiate the correct agent from the session_id
# ---------------------------------------------------------------------------

def build_agent(agent_name: str, session_id: str) -> Any:
    """
    Create an agent instance from the agent name.
    The voice interview agent will be added in Phase 4.
    """
    if agent_name == "cv_analyzer":
        return CVAnalyzerAgent(session_id=session_id)
    if agent_name == "question_generator":
        return QuestionGeneratorAgent(session_id=session_id)
    if agent_name == "voice_interview":
        return VoiceInterviewAgent(session_id=session_id)
    raise NotImplementedError(
        f"Agent '{agent_name}' not registered in router. "
        f"Available: cv_analyzer, question_generator, voice_interview"
    )


# ---------------------------------------------------------------------------
# Synchronous run helper — called from background tasks in mcp_server.py
# ---------------------------------------------------------------------------

def run_agent(
    agent_name: str,
    session_id: str,
    input_data: dict[str, Any],
) -> AgentResult:
    """
    Run the agent synchronously and return an AgentResult.
    Called from a background task — blocking is OK.
    """
    logger.info(f"[Router] Running agent={agent_name} | session={session_id}")
    agent = build_agent(agent_name, session_id)
    result = agent.run(input_data)
    logger.info(
        f"[Router] Agent done: {agent_name} | "
        f"success={result.success} | state={result.state.value} | session={session_id}"
    )
    return result


# ---------------------------------------------------------------------------
# Parallel-ready detection (future use)
# ---------------------------------------------------------------------------

def detect_parallel_ready(state: PipelineState) -> list[str]:
    """
    Which agents can run in parallel in this state?
    Currently none — sub-tasks may run in parallel in the future.
    """
    _parallel_map: dict[PipelineState, list[str]] = {
        # Example: PipelineState.AGENT1_DONE: ["question_generator", "rag_indexer"]
    }
    return _parallel_map.get(state, [])
