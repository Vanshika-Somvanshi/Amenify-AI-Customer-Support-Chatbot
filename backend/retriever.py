"""
retriever.py
------------
Loads the TF-IDF vectorizer + matrix at startup and exposes retrieve().

How retrieval works:
  1. Transform the user query with the same fitted TfidfVectorizer from ingestion
  2. L2-normalise the query vector
  3. Compute cosine similarity = dot product with pre-normalised chunk matrix
  4. Return top-k chunks that exceed the confidence threshold
"""

import json
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

import config

logger = logging.getLogger(__name__)

# ── Module-level singletons (loaded once at startup) ─────────────────────────
_vectorizer: TfidfVectorizer | None = None
_matrix: np.ndarray | None = None          # shape: (n_chunks, vocab)
_chunks: List[Dict[str, Any]] = []

# Paths for serialised TF-IDF data
VECTORIZER_PATH = config.DATA_DIR / "vectorizer.pkl"
MATRIX_PATH     = config.DATA_DIR / "tfidf_matrix.npy"


def _load_resources() -> None:
    """Load vectorizer, matrix, and chunk metadata into module-level singletons."""
    global _vectorizer, _matrix, _chunks

    if not VECTORIZER_PATH.exists():
        raise FileNotFoundError(
            f"Vectorizer not found at {VECTORIZER_PATH}. "
            "Run the ingestion pipeline first: python ingestion/run_pipeline.py"
        )
    if not MATRIX_PATH.exists():
        raise FileNotFoundError(
            f"TF-IDF matrix not found at {MATRIX_PATH}. "
            "Run the ingestion pipeline first."
        )
    if not config.CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"Chunks file not found at {config.CHUNKS_PATH}. "
            "Run the ingestion pipeline first."
        )

    logger.info("Loading TF-IDF vectorizer from %s …", VECTORIZER_PATH)
    with open(VECTORIZER_PATH, "rb") as f:
        _vectorizer = pickle.load(f)

    logger.info("Loading TF-IDF matrix from %s …", MATRIX_PATH)
    _matrix = np.load(str(MATRIX_PATH))  # shape: (n_chunks, vocab)

    logger.info("Loading chunks from %s …", config.CHUNKS_PATH)
    with open(config.CHUNKS_PATH, "r", encoding="utf-8") as f:
        _chunks = json.load(f)

    logger.info(
        "Retriever ready — %d chunks, matrix shape %s.",
        len(_chunks), _matrix.shape,
    )


def initialise() -> None:
    """Call this once at FastAPI startup to pre-load everything."""
    _load_resources()


def _embed_query(query: str) -> np.ndarray:
    """
    Transform a query string into a normalised TF-IDF vector.
    Returns shape (vocab,) float32 array.
    """
    if _vectorizer is None:
        raise RuntimeError("Vectorizer not initialised. Call initialise() first.")

    # transform() returns a sparse (1, vocab) matrix; convert to dense 1-D array
    vec = _vectorizer.transform([query]).toarray()[0].astype(np.float32)

    # L2-normalise so dot product with pre-normalised rows == cosine similarity
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec


def retrieve(query: str, top_k: int = config.TOP_K) -> List[Dict[str, Any]]:
    """
    Retrieve the top-k most relevant Amenify chunks for `query`.

    Returns list of dicts:
        { text, source_url, page_title, score }

    Returns empty list if no chunk exceeds CONFIDENCE_THRESHOLD.
    """
    if _matrix is None:
        _load_resources()

    query_vec = _embed_query(query)  # shape: (vocab,)

    # Zero-vector guard: if the query has NO vocabulary overlap with the corpus
    # (e.g. completely unrelated words like "bitcoin") all scores will be 0.
    # Short-circuit immediately — saves an API call and correctly returns "I don't know".
    if np.linalg.norm(query_vec) == 0:
        logger.info("Zero-vector query (no vocab overlap) — returning empty results.")
        return []

    # Cosine similarities: dot product with each normalised row of the matrix
    scores = _matrix.dot(query_vec)  # shape: (n_chunks,)

    # Get top-k indices sorted by descending score
    top_indices = np.argsort(scores)[::-1][:top_k]

    # Log the top score so it's easy to tune the threshold
    top_score = float(scores[top_indices[0]]) if len(top_indices) > 0 else 0.0
    logger.info("Top retrieval score: %.4f  (threshold: %.4f)", top_score, config.CONFIDENCE_THRESHOLD)

    results = []
    for idx in top_indices:
        score = float(scores[idx])
        if score < config.CONFIDENCE_THRESHOLD:
            logger.debug("Chunk %d score %.4f below threshold — skipped.", idx, score)
            continue

        chunk = _chunks[idx]
        results.append(
            {
                "text":       chunk["text"],
                "source_url": chunk.get("source_url", ""),
                "page_title": chunk.get("page_title", "Amenify"),
                "score":      score,
            }
        )

    logger.info(
        "Retrieved %d/%d chunks above threshold %.4f for query: %r",
        len(results), top_k, config.CONFIDENCE_THRESHOLD, query[:60],
    )
    return results
