#!/usr/bin/env python3
"""
FINAL INTEGRATION TEST — CV Interview Coach
20 tests covering all 4 phases.

Run directly:
    python tests/FINAL_INTEGRATION_TEST.py

Generates TEST_RESULTS.md in the project root.
Exit code 0 = all pass, 1 = any failures.
"""
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Registry ──────────────────────────────────────────────────────────────────

_TESTS: list[tuple[str, Callable]] = []


def _t(display_name: str) -> Callable:
    """Decorator: register a test with a display name."""
    def decorator(fn: Callable) -> Callable:
        _TESTS.append((display_name, fn))
        return fn
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Foundation (T01–T06)
# ═══════════════════════════════════════════════════════════════════════════════

@_t("T01 — Config loads Settings object")
def t01_config_loads():
    """Settings object is returned from get_settings()."""
    from backend.utils.config import get_settings
    s = get_settings()
    assert s is not None


@_t("T02 — GROQ_API_KEY present in .env")
def t02_groq_api_key():
    """GROQ_API_KEY is non-empty after loading from .env."""
    from backend.utils.config import get_settings
    assert get_settings().groq_api_key, "GROQ_API_KEY missing — add it to .env"


@_t("T03 — ChromaDB connects and creates collections")
def t03_chromadb():
    """VectorStore singleton opens ChromaDB and both collections exist."""
    from backend.rag.vector_store import VectorStore
    store = VectorStore.get_instance()
    stats = store.get_collection_stats()
    assert "cv_patterns" in stats
    assert "interview_questions" in stats


@_t("T04 — SQLite database initializes")
def t04_sqlite():
    """init_db() creates ORM tables without raising."""
    from backend.database.models import init_db
    init_db()


@_t("T05 — MLflow tracking URI configured")
def t05_mlflow():
    """mlflow_tracking_uri setting is non-empty."""
    from backend.utils.config import get_settings
    uri = get_settings().mlflow_tracking_uri
    assert uri and len(uri) > 0


@_t("T06 — BaseAgent is abstract (cannot instantiate directly)")
def t06_base_agent_abstract():
    """Direct instantiation of BaseAgent raises TypeError."""
    from backend.agents.base_agent import BaseAgent
    try:
        BaseAgent()  # type: ignore[abstract]
        raise AssertionError("Expected TypeError — BaseAgent should be abstract")
    except TypeError:
        pass  # expected


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — CV Analyzer + RAG (T07–T11)
# ═══════════════════════════════════════════════════════════════════════════════

@_t("T07 — CVAnalyzerAgent instantiates")
def t07_cv_agent_init():
    """CVAnalyzerAgent() creates an instance with name='cv_analyzer'."""
    from backend.agents.cv_analyzer.agent import CVAnalyzerAgent
    agent = CVAnalyzerAgent()
    assert agent.name == "cv_analyzer"


@_t("T08 — CV validator rejects empty output")
def t08_cv_validator_rejects_empty():
    """validate_cv_analysis({}) returns (False, err, None)."""
    from backend.agents.cv_analyzer.validator import validate_cv_analysis
    ok, err, result = validate_cv_analysis({})
    assert ok is False
    assert result is None


@_t("T09 — CV validator accepts valid schema")
def t09_cv_validator_accepts_valid():
    """validate_cv_analysis returns (True, ...) for a correctly structured dict."""
    from backend.agents.cv_analyzer.validator import validate_cv_analysis
    data = {
        "match_score": 78,
        "strengths": ["Python", "FastAPI", "Machine Learning"],
        "gaps": ["Kubernetes", "Docker"],
        "required_skills": ["Python", "FastAPI", "Kubernetes", "Docker"],
        "candidate_skills": ["Python", "FastAPI", "Machine Learning"],
        "summary": "Strong backend candidate with solid Python skills but missing containerization experience.",
        "experience_match": True,
        "education_match": True,
        "top_missing_skill": "Kubernetes",
    }
    ok, err, result = validate_cv_analysis(data)
    assert ok is True, f"Validation should pass, got: {err}"
    assert result.match_score == 78
    assert result.top_missing_skill == "Kubernetes"


@_t("T10 — RAG VectorStore creates both collections")
def t10_rag_vector_store():
    """get_collection_stats() returns dict with cv_patterns and interview_questions."""
    from backend.rag.vector_store import VectorStore
    stats = VectorStore.get_instance().get_collection_stats()
    assert isinstance(stats, dict)
    assert "cv_patterns" in stats
    assert "interview_questions" in stats


@_t("T11 — Retriever returns list type (empty DB ok)")
def t11_retriever_list():
    """retrieve_similar_cv_patterns returns a list regardless of DB content."""
    from backend.rag.retriever import retrieve_similar_cv_patterns
    result = retrieve_similar_cv_patterns("Python machine learning engineer", n=3)
    assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Question Generator + Supervisor MCP (T12–T16)
# ═══════════════════════════════════════════════════════════════════════════════

@_t("T12 — QuestionGeneratorAgent instantiates")
def t12_qg_agent_init():
    """QuestionGeneratorAgent() creates an instance with name='question_generator'."""
    from backend.agents.question_generator.agent import QuestionGeneratorAgent
    agent = QuestionGeneratorAgent()
    assert agent.name == "question_generator"


@_t("T13 — Question validator rejects < 9 questions")
def t13_question_validator_rejects_insufficient():
    """validate_question_output returns False when list counts are below minimums."""
    from backend.agents.question_generator.validator import validate_question_output

    def _q(text: str, cat: str, diff: str) -> dict:
        return {"text": text, "difficulty": diff, "category": cat,
                "skill_tag": "", "follow_up": ""}

    # 1 behavioral (need 3), 1 technical (need 4), 1 role_specific (need 2)
    raw = {
        "behavioral": [_q("Tell me about a challenge you overcame at work.", "behavioral", "medium")],
        "technical": [_q("Explain the difference between REST and GraphQL APIs.", "technical", "hard")],
        "role_specific": [_q("Why are you interested in this specific role today?", "role_specific", "medium")],
    }
    ok, err, result = validate_question_output(raw)
    assert ok is False, "Should reject underpopulated question lists"
    assert result is None


@_t("T14 — Question validator accepts valid 3+4+2 output")
def t14_question_validator_accepts_valid():
    """validate_question_output returns True for 3 behavioral + 4 technical + 2 role_specific."""
    from backend.agents.question_generator.validator import validate_question_output

    def _q(text: str, cat: str, diff: str) -> dict:
        return {"text": text, "difficulty": diff, "category": cat,
                "skill_tag": "Python", "follow_up": "Can you elaborate on that point?"}

    raw = {
        "behavioral": [_q(f"Behavioral interview question number {i + 1}.", "behavioral", "medium")
                       for i in range(3)],
        "technical": [_q(f"Technical coding question number {i + 1}.", "technical", "hard")
                      for i in range(4)],
        "role_specific": [_q(f"Role-specific scenario question number {i + 1}.", "role_specific", "medium")
                          for i in range(2)],
    }
    ok, err, result = validate_question_output(raw)
    assert ok is True, f"Should accept 3+4+2 questions, got: {err}"
    assert result.total_count == 9


@_t("T15 — Supervisor /health endpoint returns 200")
def t15_supervisor_health():
    """mcp_app /health responds 200 OK."""
    from fastapi.testclient import TestClient
    from backend.supervisor.mcp_server import mcp_app
    resp = TestClient(mcp_app).get("/health")
    assert resp.status_code == 200


@_t("T16 — Supervisor /dispatch accepts CV+JD payload")
def t16_supervisor_dispatch():
    """POST /dispatch returns 200/202 for a well-formed payload.

    raise_server_exceptions=False so background task failures (e.g. no Groq key)
    do not abort the HTTP-layer assertion.
    """
    from fastapi.testclient import TestClient
    from backend.supervisor.mcp_server import mcp_app
    client = TestClient(mcp_app, raise_server_exceptions=False)
    payload = {
        "session_id": "integration-final-dispatch-001",
        "cv_text": "Experienced Python developer with 5 years of FastAPI and machine learning expertise.",
        "jd_text": "Seeking a Python ML engineer with FastAPI, Docker, and cloud deployment skills.",
    }
    resp = client.post("/dispatch", json=payload)
    assert resp.status_code in (200, 202), f"Got {resp.status_code}: {resp.text}"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Voice Interview Agent (T17–T20)
# ═══════════════════════════════════════════════════════════════════════════════

@_t("T17 — VoiceInterviewAgent instantiates")
def t17_voice_agent_init():
    """VoiceInterviewAgent() creates an instance with name='voice_interview'."""
    from backend.agents.voice_interview.agent import VoiceInterviewAgent
    agent = VoiceInterviewAgent()
    assert agent.name == "voice_interview"


@_t("T18 — AnswerEval validator rejects empty input")
def t18_answer_eval_rejects_empty():
    """validate_answer_eval({}) returns (False, err, None)."""
    from backend.agents.voice_interview.validator import validate_answer_eval
    ok, err, result = validate_answer_eval({})
    assert ok is False
    assert result is None


@_t("T19 — SessionReport avg_score auto-computed by model_validator")
def t19_session_report_avg_score():
    """model_validator computes avg_score = mean(answers.score) — not trusted from LLM."""
    from backend.agents.voice_interview.validator import validate_session_report

    def _ans(idx: int, score: int, q_text: str) -> dict:
        return {
            "score": score,
            "feedback": "Adequate response with relevant examples provided during the answer.",
            "strong_points": ["clarity"],
            "weak_points": [],
            "follow_up": "",
            "question_index": idx,
            "question_text": q_text,
            "answer_text": "I have experience working on various Python projects.",
            "category": "behavioral",
            "skill_tag": "communication",
            "difficulty": "medium",
        }

    raw = {
        "answers": [
            _ans(0, 8, "Tell me about yourself and your background."),
            _ans(1, 6, "Describe a difficult technical problem you solved."),
        ],
        "overall_feedback": "Candidate demonstrates solid Python skills with room to improve technical depth.",
        "weak_areas": ["technical depth"],
        "strong_areas": ["communication", "Python knowledge"],
        "top_improvement_tips": ["Practice STAR method", "Prepare specific ML project examples"],
        "recommendation": "consider",
    }
    ok, err, result = validate_session_report(raw)
    assert ok is True, f"Should accept valid SessionReport, got: {err}"
    assert result.avg_score == 7.0, f"Expected avg 7.0 for scores [8,6], got {result.avg_score}"
    assert result.total_questions == 2


@_t("T20 — Router build_agent returns correct types for all three agents")
def t20_router_all_agents():
    """build_agent() factory resolves cv_analyzer, question_generator, voice_interview."""
    from backend.supervisor.router import build_agent
    from backend.agents.cv_analyzer.agent import CVAnalyzerAgent
    from backend.agents.question_generator.agent import QuestionGeneratorAgent
    from backend.agents.voice_interview.agent import VoiceInterviewAgent

    assert isinstance(build_agent("cv_analyzer", "final-cv"), CVAnalyzerAgent)
    assert isinstance(build_agent("question_generator", "final-qg"), QuestionGeneratorAgent)
    assert isinstance(build_agent("voice_interview", "final-vi"), VoiceInterviewAgent)


# ═══════════════════════════════════════════════════════════════════════════════
# Runner + TEST_RESULTS.md writer
# ═══════════════════════════════════════════════════════════════════════════════

def _run_all() -> list[tuple[str, str, str]]:
    """Run every registered test. Returns list of (display_name, status, error)."""
    records: list[tuple[str, str, str]] = []
    for name, fn in _TESTS:
        try:
            fn()
            records.append((name, "PASS", ""))
            print(f"  ✓  {name}")
        except Exception as exc:  # noqa: BLE001
            short_err = str(exc).split("\n")[0][:120]
            records.append((name, "FAIL", short_err))
            print(f"  ✗  {name}")
            print(f"     └─ {short_err}")
    return records


def _write_results_md(records: list[tuple[str, str, str]]) -> Path:
    """Write TEST_RESULTS.md to project root and return its path."""
    passed = sum(1 for _, s, _ in records if s == "PASS")
    total = len(records)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    verdict = "✅ READY FOR DEMO" if passed > 16 else "❌ NEEDS FIXES"

    lines = [
        "# Test Results — CV Interview Coach",
        "",
        f"**Timestamp:** {timestamp}",
        f"**Python:** {sys.version.split()[0]}",
        "",
        "---",
        "",
        "## Results",
        "",
        "| # | Test | Status | Error |",
        "|---|------|--------|-------|",
    ]

    for i, (name, status, error) in enumerate(records, 1):
        icon = "✅" if status == "PASS" else "❌"
        err_col = (error[:90] + "…") if len(error) > 90 else error
        lines.append(f"| {i:02d} | {name} | {icon} {status} | {err_col} |")

    lines += [
        "",
        "---",
        "",
        "## Summary",
        "",
        f"- **Passed:** {passed} / {total}",
        f"- **Failed:** {total - passed} / {total}",
        f"- **Pass rate:** {passed / total * 100:.0f}%",
        "",
        "---",
        "",
        "## Verdict",
        "",
        verdict,
    ]

    out_path = ROOT / "TEST_RESULTS.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    print("\n" + "=" * 58)
    print("  CV Interview Coach — Final Integration Tests (20)")
    print("=" * 58 + "\n")

    records = _run_all()
    passed = sum(1 for _, s, _ in records if s == "PASS")
    total = len(records)

    print(f"\n{'=' * 58}")
    print(f"  Passed: {passed}/{total}  |  Failed: {total - passed}/{total}")

    out_path = _write_results_md(records)
    print(f"  Results → {out_path}")
    verdict = "READY FOR DEMO" if passed > 16 else "NEEDS FIXES"
    print(f"  Verdict: {verdict}")
    print("=" * 58 + "\n")

    sys.exit(0 if passed == total else 1)
