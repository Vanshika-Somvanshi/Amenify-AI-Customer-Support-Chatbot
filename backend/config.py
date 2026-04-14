"""
config.py
---------
Centralised configuration loaded from environment variables.
All settings live here — nothing is hardcoded elsewhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file when running locally (has no effect in production)
load_dotenv()

# ── Groq ──────────────────────────────────────────────────────────────────
# Free: 14,400 requests/day, 1,000 RPM. Get key at https://console.groq.com
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# llama-3.3-70b is fast, accurate, and completely free on Groq
CHAT_MODEL: str = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")

# ── Retrieval ────────────────────────────────────────────────────────────────
# How many chunks to retrieve from FAISS for each query
TOP_K: int = int(os.getenv("TOP_K", "4"))

# Cosine-similarity threshold (0–1).  Below this → "I don't know".
# TF-IDF on a small domain corpus produces scores in the 0.005–0.08 range.
# Set low enough to pass relevant chunks, high enough to block zero-overlap queries.
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.005"))

# ── Data paths ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CHUNKS_PATH      = DATA_DIR / "chunks.json"
VECTORIZER_PATH  = DATA_DIR / "vectorizer.pkl"
TFIDF_MATRIX_PATH = DATA_DIR / "tfidf_matrix.npy"

# Legacy alias kept for compatibility
FAISS_INDEX_PATH = DATA_DIR / "faiss.index"

# ── CORS ─────────────────────────────────────────────────────────────────────
# Comma-separated list of allowed origins.  Add your Vercel URL here.
ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    ).split(",")
    if o.strip()
]
