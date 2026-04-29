# Yeh file ChromaDB vector store setup karti hai — do collections hain.
# "cv_patterns": successful CV-JD matches store hote hain future reference ke liye.
# "interview_questions": past questions store hote hain taake agent similar sawaal generate kare.

from __future__ import annotations

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.utils.config import get_settings
from backend.utils.logger import logger

settings = get_settings()

# Collection names — yahan define karo taake typos na ho
COLLECTION_CV_PATTERNS = "cv_patterns"
COLLECTION_INTERVIEW_QUESTIONS = "interview_questions"


class VectorStore:
    """
    ChromaDB wrapper — singleton pattern.
    Do collections manage karta hai: CV patterns aur interview questions.
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
        """Singleton — ek baar banao, baar baar use karo."""
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
        """Ek CV-JD pattern store karo future retrieval ke liye."""
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
        """Similar CV patterns search karo embedding se."""
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
        """Ek interview question store karo."""
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
        """Similar interview questions retrieve karo."""
        kwargs: dict = {"query_embeddings": [embedding], "n_results": n_results}
        if where:
            kwargs["where"] = where
        return self._interview_questions.query(**kwargs)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_collection_stats(self) -> dict[str, int]:
        """Dono collections ka document count wapas lo."""
        return {
            COLLECTION_CV_PATTERNS: self._cv_patterns.count(),
            COLLECTION_INTERVIEW_QUESTIONS: self._interview_questions.count(),
        }

    def reset_collection(self, collection_name: str) -> None:
        """Testing ke liye — ek collection saaf karo."""
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
    """FastAPI dependency injection ke liye shortcut."""
    return VectorStore.get_instance()
