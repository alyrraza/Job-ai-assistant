# Sets up the ChromaDB vector store — there are two collections.
# "cv_patterns": stores successful CV-JD matches for future reference.
# "interview_questions": stores past questions so the agent can generate similar ones.

from __future__ import annotations

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.utils.config import get_settings
from backend.utils.logger import logger

settings = get_settings()

# Collection names — defined here to avoid typos
COLLECTION_CV_PATTERNS = "cv_patterns"
COLLECTION_INTERVIEW_QUESTIONS = "interview_questions"


class VectorStore:
    """
    ChromaDB wrapper — singleton pattern.
    Manages two collections: CV patterns and interview questions.
    """

    _instance: Optional["VectorStore"] = None

    def __init__(self) -> None:
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB initialized at: {persist_dir}")

        # Collections — get_or_create so restarts don't wipe data
        self._cv_patterns = self._client.get_or_create_collection(
            name=COLLECTION_CV_PATTERNS,
            metadata={"hnsw:space": "cosine"},
        )
        self._interview_questions = self._client.get_or_create_collection(
            name=COLLECTION_INTERVIEW_QUESTIONS,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"Collections ready — cv_patterns: {self._cv_patterns.count()} docs, "
            f"interview_questions: {self._interview_questions.count()} docs"
        )

    @classmethod
    def get_instance(cls) -> "VectorStore":
        """Singleton — create once, reuse every time."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # CV Patterns collection
    # ------------------------------------------------------------------

    def add_cv_pattern(
        self,
        doc_id: str,
        text: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Store a CV-JD pattern for future retrieval."""
        self._cv_patterns.add(
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        logger.debug(f"CV pattern added: id={doc_id}")

    def query_cv_patterns(
        self,
        embedding: list[float],
        n_results: int = 3,
        where: Optional[dict] = None,
    ) -> dict:
        """Search for similar CV patterns by embedding."""
        kwargs: dict = {"query_embeddings": [embedding], "n_results": n_results}
        if where:
            kwargs["where"] = where
        return self._cv_patterns.query(**kwargs)

    # ------------------------------------------------------------------
    # Interview Questions collection
    # ------------------------------------------------------------------

    def add_interview_question(
        self,
        doc_id: str,
        question_text: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Store an interview question."""
        self._interview_questions.add(
            ids=[doc_id],
            documents=[question_text],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        logger.debug(f"Interview question added: id={doc_id}")

    def query_interview_questions(
        self,
        embedding: list[float],
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        """Retrieve similar interview questions."""
        kwargs: dict = {"query_embeddings": [embedding], "n_results": n_results}
        if where:
            kwargs["where"] = where
        return self._interview_questions.query(**kwargs)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_collection_stats(self) -> dict[str, int]:
        """Return the document count of both collections."""
        return {
            COLLECTION_CV_PATTERNS: self._cv_patterns.count(),
            COLLECTION_INTERVIEW_QUESTIONS: self._interview_questions.count(),
        }

    def reset_collection(self, collection_name: str) -> None:
        """For testing — clear a collection."""
        self._client.delete_collection(collection_name)
        if collection_name == COLLECTION_CV_PATTERNS:
            self._cv_patterns = self._client.get_or_create_collection(
                name=COLLECTION_CV_PATTERNS,
                metadata={"hnsw:space": "cosine"},
            )
        elif collection_name == COLLECTION_INTERVIEW_QUESTIONS:
            self._interview_questions = self._client.get_or_create_collection(
                name=COLLECTION_INTERVIEW_QUESTIONS,
                metadata={"hnsw:space": "cosine"},
            )
        logger.warning(f"Collection reset: {collection_name}")


def get_vector_store() -> VectorStore:
    """Shortcut for FastAPI dependency injection."""
    return VectorStore.get_instance()
