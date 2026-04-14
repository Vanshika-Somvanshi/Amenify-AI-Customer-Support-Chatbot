"""
embedder.py  (now a TF-IDF vectorizer — no neural embeddings, no API key)
--------------------------------------------------------------------------
Builds a TF-IDF index over all Amenify chunks using scikit-learn.

Why TF-IDF instead of neural embeddings?
  • 100% pure Python — zero C/Rust compilation needed
  • scikit-learn ships pre-built wheels for every Python version including 3.13
  • For 96 keyword-rich support chunks, TF-IDF retrieval quality is excellent
  • Instant indexing (milliseconds vs. seconds for neural models)

Output files (written to backend/data/):
  • vectorizer.pkl      — fitted TfidfVectorizer (serialised with pickle)
  • tfidf_matrix.npy   — dense TF-IDF matrix, shape (n_chunks, vocab)
  • chunks.json         — chunk metadata (same row order as the matrix)
"""

import json
import pickle
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

INPUT_PATH = Path(__file__).parent / "chunks.json"

BACKEND_DATA_DIR = Path(__file__).parent.parent / "backend" / "data"
VECTORIZER_PATH  = BACKEND_DATA_DIR / "vectorizer.pkl"
MATRIX_PATH      = BACKEND_DATA_DIR / "tfidf_matrix.npy"
CHUNKS_OUT_PATH  = BACKEND_DATA_DIR / "chunks.json"


def build_index(chunks: List[Dict[str, Any]]) -> None:
    """
    Fit a TF-IDF vectorizer on all chunk texts and save the matrix + vectorizer.
    """
    BACKEND_DATA_DIR.mkdir(parents=True, exist_ok=True)

    texts = [c["text"] for c in chunks]
    n = len(texts)
    logger.info("Building TF-IDF index over %d chunks …", n)

    # TfidfVectorizer settings:
    #   ngram_range=(1,2)  — captures both single words and bigrams for better matching
    #   max_features=8000  — caps vocabulary size to keep matrix small
    #   sublinear_tf=True  — apply log(1+tf) to reduce impact of very frequent terms
    #   stop_words='english' — remove common words like "the", "and", etc.
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=8000,
        sublinear_tf=True,
        stop_words="english",
    )

    # Fit and transform — result is a sparse matrix of shape (n_chunks, vocab_size)
    sparse_matrix = vectorizer.fit_transform(texts)
    logger.info(
        "TF-IDF matrix shape: %s, vocabulary size: %d",
        sparse_matrix.shape,
        len(vectorizer.vocabulary_),
    )

    # Convert to dense numpy array for simple dot-product retrieval
    # (~96 chunks × ~8000 features = tiny, well under 1MB)
    dense_matrix = sparse_matrix.toarray().astype(np.float32)

    # L2-normalise each row so dot product == cosine similarity at query time
    norms = np.linalg.norm(dense_matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    dense_matrix = dense_matrix / norms

    # Save matrix
    np.save(str(MATRIX_PATH), dense_matrix)
    logger.info("✓ TF-IDF matrix saved to %s", MATRIX_PATH)

    # Save fitted vectorizer (needed to transform query at runtime)
    with open(VECTORIZER_PATH, "wb") as f:
        pickle.dump(vectorizer, f)
    logger.info("✓ Vectorizer saved to %s", VECTORIZER_PATH)

    # Save chunk metadata
    with open(CHUNKS_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    logger.info("✓ Chunks metadata saved to %s", CHUNKS_OUT_PATH)


if __name__ == "__main__":
    if not INPUT_PATH.exists():
        logger.error("chunks.json not found at %s. Run chunker.py first.", INPUT_PATH)
        sys.exit(1)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    logger.info("Loaded %d chunks from %s", len(chunks), INPUT_PATH)
    build_index(chunks)
    logger.info("Ingestion pipeline complete.")
