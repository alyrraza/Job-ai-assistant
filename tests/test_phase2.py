"""Phase 2 tests — CV Analyzer Agent + RAG Pipeline (vector store + retriever)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_cv_analyzer_agent_instantiates():
    """CVAnalyzerAgent instantiates with correct name and no LLM call."""
    from backend.agents.cv_analyzer.agent import CVAnalyzerAgent
    agent = CVAnalyzerAgent()
    assert agent.name == "cv_analyzer"


def test_cv_validate_rejects_empty_output():
    """validate_cv_analysis returns (False, ...) for empty dict."""
    from backend.agents.cv_analyzer.validator import validate_cv_analysis
    ok, err, result = validate_cv_analysis({})
    assert ok is False
    assert result is None
    assert err is not None


def test_cv_validate_accepts_correct_schema():
    """validate_cv_analysis returns (True, ...) for a fully valid dict."""
    from backend.agents.cv_analyzer.validator import validate_cv_analysis
    valid_data = {
        "match_score": 80,
        "strengths": ["Python", "FastAPI", "Machine Learning"],
        "gaps": ["Kubernetes", "Docker"],
        "required_skills": ["Python", "FastAPI", "Kubernetes", "Docker"],
        "candidate_skills": ["Python", "FastAPI", "Machine Learning"],
        "summary": "Strong backend candidate with excellent Python skills but missing containerization experience.",
        "experience_match": True,
        "education_match": True,
        "top_missing_skill": "Kubernetes",
    }
    ok, err, result = validate_cv_analysis(valid_data)
    assert ok is True, f"Validation should pass but got: {err}"
    assert result is not None
    assert result.match_score == 80
    assert result.top_missing_skill == "Kubernetes"


def test_rag_vector_store_creates_collections():
    """VectorStore singleton exposes both required ChromaDB collections."""
    from backend.rag.vector_store import VectorStore
    store = VectorStore.get_instance()
    stats = store.get_collection_stats()
    assert isinstance(stats, dict)
    assert "cv_patterns" in stats
    assert "interview_questions" in stats


def test_retriever_returns_list():
    """retrieve_similar_cv_patterns returns a list (empty DB → empty list)."""
    from backend.rag.retriever import retrieve_similar_cv_patterns
    results = retrieve_similar_cv_patterns("Python machine learning engineer", n=3)
    assert isinstance(results, list)
