"""Phase 3 tests — Question Generator Agent + Supervisor MCP Server + Router."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_question_generator_agent_instantiates():
    """QuestionGeneratorAgent instantiates with correct name."""
    from backend.agents.question_generator.agent import QuestionGeneratorAgent
    agent = QuestionGeneratorAgent()
    assert agent.name == "question_generator"


def test_question_validator_rejects_insufficient_questions():
    """validate_question_output returns False when counts are below minimums.

    Minimums: behavioral >= 3, technical >= 4, role_specific >= 2.
    This test provides only 1 of each — all three checks should fail.
    """
    from backend.agents.question_generator.validator import validate_question_output

    def _q(text: str, cat: str, diff: str) -> dict:
        return {"text": text, "difficulty": diff, "category": cat,
                "skill_tag": "", "follow_up": ""}

    raw = {
        "behavioral": [_q("Tell me about a challenge you overcame at work.", "behavioral", "medium")],
        "technical": [_q("Explain the difference between REST and GraphQL APIs.", "technical", "hard")],
        "role_specific": [_q("Why are you interested in this specific role today?", "role_specific", "medium")],
    }
    ok, err, result = validate_question_output(raw)
    assert ok is False, "Should reject: behavioral<3, technical<4, role_specific<2"
    assert result is None


def test_supervisor_health_returns_200():
    """Supervisor /health endpoint responds 200 OK."""
    from fastapi.testclient import TestClient
    from backend.supervisor.mcp_server import mcp_app
    client = TestClient(mcp_app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_supervisor_dispatch_accepts_payload():
    """Supervisor /dispatch accepts a valid CV+JD payload and returns 200/202.

    raise_server_exceptions=False: background task failures (e.g. Groq timeout)
    do not abort the assertion — we only test the HTTP acceptance layer.
    """
    from fastapi.testclient import TestClient
    from backend.supervisor.mcp_server import mcp_app

    client = TestClient(mcp_app, raise_server_exceptions=False)
    payload = {
        "session_id": "phase3-test-dispatch-001",
        "cv_text": "Experienced Python developer with 5 years of FastAPI and machine learning expertise.",
        "jd_text": "Seeking a Python ML engineer with strong FastAPI, Docker, and cloud deployment skills.",
    }
    resp = client.post("/dispatch", json=payload)
    assert resp.status_code in (200, 202), (
        f"Expected 200/202 but got {resp.status_code}: {resp.text}"
    )


def test_router_build_agent_returns_correct_types():
    """build_agent() factory returns the correct class for cv_analyzer and question_generator."""
    from backend.supervisor.router import build_agent
    from backend.agents.cv_analyzer.agent import CVAnalyzerAgent
    from backend.agents.question_generator.agent import QuestionGeneratorAgent

    cv_agent = build_agent("cv_analyzer", "router-test-cv")
    assert isinstance(cv_agent, CVAnalyzerAgent)

    qg_agent = build_agent("question_generator", "router-test-qg")
    assert isinstance(qg_agent, QuestionGeneratorAgent)
