"""Phase 1 foundation tests — config, ChromaDB, SQLite, MLflow, logger, BaseAgent."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


def test_env_groq_api_key_present():
    """GROQ_API_KEY loaded from .env via pydantic-settings."""
    from backend.utils.config import get_settings
    settings = get_settings()
    assert settings.groq_api_key, "GROQ_API_KEY missing — add it to .env"


def test_chromadb_connects_and_creates_collections():
    """ChromaDB PersistentClient opens and both collections are created."""
    from backend.rag.vector_store import VectorStore
    store = VectorStore.get_instance()
    assert store is not None
    stats = store.get_collection_stats()
    assert "cv_patterns" in stats, "cv_patterns collection missing"
    assert "interview_questions" in stats, "interview_questions collection missing"


def test_sqlite_db_initializes():
    """SQLite database initializes (creates all ORM tables) without error."""
    from backend.database.models import init_db
    init_db()  # idempotent — safe to call multiple times


def test_mlflow_tracking_uri_set():
    """MLflow tracking URI is configured via settings."""
    from backend.utils.config import get_settings
    settings = get_settings()
    assert settings.mlflow_tracking_uri
    assert len(settings.mlflow_tracking_uri) > 0


def test_logger_works_without_error():
    """Loguru logger emits a log entry without raising."""
    from backend.utils.logger import logger
    logger.info("test_phase1: logger smoke test")


def test_base_agent_cannot_be_instantiated_directly():
    """BaseAgent is abstract — direct instantiation must raise TypeError."""
    from backend.agents.base_agent import BaseAgent
    with pytest.raises(TypeError):
        BaseAgent()  # type: ignore[abstract]
