# Yeh file ChromaDB se similar documents retrieve karti hai.
# Query text do → embedding banao → top-3 similar CV patterns wapas lo.
# CV Analyzer agent yeh use karega context improve karne ke liye.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.rag.ingestion import embed_text
from backend.rag.vector_store import VectorStore, get_vector_store
from backend.utils.logger import logger


@dataclass
class RetrievedChunk:
    """Ek retrieved document chunk — text aur metadata ke saath."""

    doc_id: str
    text: str
    score: float
    metadata: dict


def retrieve_similar_cv_patterns(
    query_text: str,
    n: int = 3,
    min_score: float = 0.0,
    where: Optional[dict] = None,
) -> list[RetrievedChunk]:
    """
    Query text se similar CV patterns retrieve karo ChromaDB se.

    Args:
        query_text:  Search query — usually a skill or JD snippet.
        n:           Kitne results chahiye (default 3).
        min_score:   Minimum cosine similarity threshold (0.0 = no filter).
        where:       Optional ChromaDB metadata filter dict.

    Returns:
        List of RetrievedChunk sorted by similarity (highest first).
    """
    if not query_text.strip():
        logger.warning("retrieve_similar_cv_patterns called with empty query")
        return []

    store: VectorStore = get_vector_store()

    # Check if collection has any documents
    stats = store.get_collection_stats()
    if stats.get("cv_patterns", 0) == 0:
        logger.debug("cv_patterns collection is empty — returning no results")
        return []

    # Embed the query
    query_embedding = embed_text(query_text)

    # Query ChromaDB — cap n_results to what's actually in the collection
    safe_n = min(n, stats["cv_patterns"])
    raw_results = store.query_cv_patterns(
        embedding=query_embedding,
        n_results=safe_n,
        where=where,
    )

    chunks = _parse_chroma_results(raw_results, min_score=min_score)
    logger.debug(f"Retrieved {len(chunks)} CV pattern chunks for query: '{query_text[:60]}...'")
    return chunks


def retrieve_similar_questions(
    query_text: str,
    n_results: int = 5,
    category: Optional[str] = None,
) -> list[RetrievedChunk]:
    """
    Similar interview questions retrieve karo.

    Args:
        query_text: Skill ya topic jo question mein hona chahiye.
        n_results:  Kitne questions chahiye (default 5).
        category:   Optional filter — "behavioral", "technical", "role_specific".
    """
    if not query_text.strip():
        return []

    store: VectorStore = get_vector_store()

    stats = store.get_collection_stats()
    if stats.get("interview_questions", 0) == 0:
        logger.debug("interview_questions collection is empty — returning no results")
        return []

    query_embedding = embed_text(query_text)
    where = {"category": category} if category else None
    safe_n = min(n_results, stats["interview_questions"])

    raw_results = store.query_interview_questions(
        embedding=query_embedding,
        n_results=safe_n,
        where=where,
    )

    chunks = _parse_chroma_results(raw_results)
    logger.debug(f"Retrieved {len(chunks)} question chunks for query: '{query_text[:60]}'")
    return chunks


def format_chunks_for_prompt(chunks: list[RetrievedChunk], max_chars: int = 2000) -> str:
    """
    Retrieved chunks ko LLM prompt mein inject karne ke liye format karo.
    Token budget se zyada nahi jaana chahiye.
    """
    if not chunks:
        return ""

    parts = []
    total = 0
    for i, chunk in enumerate(chunks, 1):
        snippet = f"[Example {i} | score={chunk.score:.2f}]\n{chunk.text}"
        if total + len(snippet) > max_chars:
            break
        parts.append(snippet)
        total += len(snippet)

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_chroma_results(
    raw: dict,
    min_score: float = 0.0,
) -> list[RetrievedChunk]:
    """ChromaDB query result dict ko clean list mein convert karo."""
    ids = raw.get("ids", [[]])[0]
    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    chunks: list[RetrievedChunk] = []
    for doc_id, text, meta, dist in zip(ids, documents, metadatas, distances):
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity score: 1 - (dist / 2)
        similarity = max(0.0, 1.0 - (dist / 2.0))
        if similarity < min_score:
            continue
        chunks.append(
            RetrievedChunk(
                doc_id=doc_id,
                text=text or "",
                score=round(similarity, 4),
                metadata=meta or {},
            )
        )

    return sorted(chunks, key=lambda c: c.score, reverse=True)
