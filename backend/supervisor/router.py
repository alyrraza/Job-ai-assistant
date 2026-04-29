# Yeh file dynamic routing logic implement karti hai — supervisor ka "brain".
# Current pipeline state dekh ke decide karta hai konsa agent next chalega.
# Agent classes yahan import hoti hain — mcp_server.py mein nahi — circular import se bacho.

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
    """Current state ke baad konsa agent chalega — None matlab koi nahi."""
    return _STATE_TO_AGENT.get(state)


def get_running_state(agent_name: str) -> Optional[PipelineState]:
    """Agent name se uska running state do."""
    mapping = {
        "cv_analyzer": PipelineState.AGENT1_RUNNING,
        "question_generator": PipelineState.AGENT2_RUNNING,
        "voice_interview": PipelineState.AGENT3_RUNNING,
    }
    return mapping.get(agent_name)


def should_auto_advance(state: PipelineState) -> bool:
    """Is state ke baad automatically next agent chalao?"""
    return state in _AUTO_ADVANCE_STATES


def transition_on_success(state: PipelineState) -> PipelineState:
    """Success ke baad next state kya hoga."""
    return _SUCCESS_TRANSITIONS.get(state, PipelineState.FAILED)


def transition_on_failure(state: PipelineState) -> PipelineState:
    """Any running state fail hone pe FAILED state."""
    return PipelineState.FAILED


# ---------------------------------------------------------------------------
# Agent factory — session_id se correct agent instantiate karo
# ---------------------------------------------------------------------------

def build_agent(agent_name: str, session_id: str) -> Any:
    """
    Agent name se agent instance banao.
    Voice interview agent Phase 4 mein add hoga.
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
    Agent ko synchronously chalao aur AgentResult wapas do.
    Background task mein call hota hai — blocking OK hai.
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
    Is state mein parallel chalane layak agents kaunse hain?
    Currently none — future mein sub-tasks parallel ho sakti hain.
    """
    _parallel_map: dict[PipelineState, list[str]] = {
        # Example: PipelineState.AGENT1_DONE: ["question_generator", "rag_indexer"]
    }
    return _parallel_map.get(state, [])
