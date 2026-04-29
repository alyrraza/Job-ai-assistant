# Yeh file documents ko vector store mein ingest karti hai.
# PDF aur plain text dono support hain — LlamaIndex document loader use kiya.
# Embedding generate karo aur ChromaDB mein store karo — retriever baad mein use karega.

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Union

from llama_index.core import SimpleDirectoryReader, Document
from llama_index.core.node_parser import SentenceSplitter
from sentence_transformers import SentenceTransformer

from backend.rag.vector_store import VectorStore, COLLECTION_CV_PATTERNS, get_vector_store
from backend.utils.logger import logger

# Local embedding model — Groq sirf LLM ke liye, embeddings local hain
_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
_embed_model: SentenceTransformer | None = None


def _get_embed_model() -> SentenceTransformer:
    """Lazy load karo — pehli baar hi download hoga."""
    global _embed_model
    if _embed_model is None:
        logger.info(f"Loading embedding model: {_EMBED_MODEL_NAME}")
        _embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
        logger.success(f"Embedding model loaded: {_EMBED_MODEL_NAME}")
    return _embed_model


def embed_text(text: str) -> list[float]:
    """Text ko embedding vector mein convert karo."""
    model = _get_embed_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def _stable_doc_id(text: str, prefix: str = "") -> str:
    """Same text ka same ID banao — duplicate inserts se bacho."""
    hash_val = hashlib.md5(text.encode()).hexdigest()[:12]
    return f"{prefix}_{hash_val}" if prefix else hash_val


# ---------------------------------------------------------------------------
# PDF ingestion
# ---------------------------------------------------------------------------

def ingest_pdf(file_path: Union[str, Path], metadata: dict | None = None) -> int:
    """
    PDF file lo, chunk karo, embed karo, ChromaDB mein store karo.

    Returns:
        Number of chunks ingested.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    logger.info(f"Ingesting PDF: {file_path.name}")
    reader = SimpleDirectoryReader(input_files=[str(file_path)])
    documents: list[Document] = reader.load_data()

    return _ingest_documents(documents, metadata or {"source": file_path.name, "type": "pdf"})


# ---------------------------------------------------------------------------
# Plain text ingestion
# ---------------------------------------------------------------------------

def ingest_text(
    text: str,
    doc_id: str | None = None,
    metadata: dict | None = None,
) -> int:
    """
    Raw text string lo, chunk karo, embed karo, ChromaDB mein store karo.

    Returns:
        Number of chunks ingested.
    """
    if not text.strip():
        logger.warning("ingest_text called with empty text — skipping")
        return 0

    document = Document(text=text, id_=doc_id or str(uuid.uuid4()))
    return _ingest_documents([document], metadata or {"source": "raw_text", "type": "text"})


# ---------------------------------------------------------------------------
# Core ingestion pipeline
# ---------------------------------------------------------------------------

def _ingest_documents(documents: list[Document], base_metadata: dict) -> int:
    """
    LlamaIndex documents lo → chunk karo → embed karo → ChromaDB mein add karo.
    """
    splitter = SentenceSplitter(chunk_size=512, chunk_overlap=64)
    nodes = splitter.get_nodes_from_documents(documents)

    if not nodes:
        logger.warning("No nodes after splitting — nothing ingested")
        return 0

    store: VectorStore = get_vector_store()
    ingested = 0

    for node in nodes:
        chunk_text = node.get_content().strip()
        if not chunk_text:
            continue

        doc_id = _stable_doc_id(chunk_text, prefix="cv")
        embedding = embed_text(chunk_text)
        chunk_meta = {**base_metadata, "chunk_index": ingested, "char_count": len(chunk_text)}

        try:
            store.add_cv_pattern(
                doc_id=doc_id,
                text=chunk_text,
                embedding=embedding,
                metadata=chunk_meta,
            )
            ingested += 1
        except Exception as exc:
            # Duplicate ID error — silently skip
            if "already exists" in str(exc).lower() or "duplicate" in str(exc).lower():
                logger.debug(f"Chunk already in store, skipping: {doc_id}")
            else:
                logger.error(f"Failed to ingest chunk {doc_id}: {exc}")

    logger.success(f"Ingestion complete — {ingested}/{len(nodes)} chunks stored")
    return ingested


# ---------------------------------------------------------------------------
# Convenience: ingest a CV-JD pair as a matched pattern
# ---------------------------------------------------------------------------

def ingest_cv_jd_match(
    cv_text: str,
    jd_text: str,
    match_score: int,
    session_id: str,
) -> int:
    """
    Successful CV-JD match ko vector store mein save karo.
    Future retrieval mein similar CVs ke liye example ban jaayega.
    """
    combined = f"CV:\n{cv_text[:1500]}\n\nJD:\n{jd_text[:1500]}"
    metadata = {
        "type": "cv_jd_match",
        "match_score": str(match_score),
        "session_id": session_id,
        "source": "cv_jd_pair",
    }
    return ingest_text(combined, metadata=metadata)
