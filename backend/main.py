"""
main.py
-------
FastAPI application entry point.

Endpoints:
  GET  /health   — Render health check
  POST /chat     — Main chatbot endpoint

Startup:
  • Validates GROQ_API_KEY is set
  • Loads the TF-IDF index and chunks into memory (done once)

CORS:
  • Configured via ALLOWED_ORIGINS env var
  • Defaults to localhost:5173 (Vite dev server)
"""

import logging
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import config
import retriever
from generator import generate_answer
from models import ChatRequest, ChatResponse

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Amenify Support Chatbot API",
    description="Grounded AI customer support bot powered by RAG over amenify.com content.",
    version="1.0.0",
    docs_url="/docs",   # Swagger UI available at /docs
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow the frontend origin (Vercel URL set via env var, plus localhost for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup event — load resources once ──────────────────────────────────────
@app.on_event("startup")
async def startup_event() -> None:
    """
    Called once when the server starts.
    Validates config and pre-loads the TF-IDF index so the first request
    doesn't experience a cold-load delay.
    """
    if not config.GROQ_API_KEY:
        logger.error(
            "GROQ_API_KEY is not set. "
            "Add it to your .env file or Render environment variables."
        )
        # Don't crash on startup — just log; the /chat endpoint will 500
    try:
        retriever.initialise()
    except FileNotFoundError as exc:
        logger.error("Failed to load retrieval resources: %s", exc)
        # Still let the server start so /health can respond


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
async def health_check() -> dict:
    """Simple ping used by Render to verify the service is alive."""
    return {"status": "ok", "service": "amenify-chatbot-api"}


# ── Chat endpoint ─────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chatbot endpoint.

    Flow:
      1. Validate API key is configured
      2. Retrieve the top-k most relevant Amenify chunks via TF-IDF
      3. Pass chunks + history to the generator for a grounded answer
      4. Return the answer and source metadata to the frontend
    """
    if not config.GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: GROQ_API_KEY is missing.",
        )

    logger.info("Received query: %r (history length: %d)", request.message[:80], len(request.history))

    # ── Query augmentation for contextual follow-ups ──────────────────────────
    # TF-IDF can't understand vague queries like "tell me more about the first one"
    # without knowing what topic we're on. Fix: if the query is short/vague AND
    # we have history, prepend the last assistant turn to the retrieval query.
    # This gives TF-IDF the topic keywords it needs to find the right chunks.
    retrieval_query = request.message
    if request.history and len(request.message.split()) <= 10:
        last_assistant = next(
            (turn.content for turn in reversed(request.history) if turn.role == "assistant"),
            None,
        )
        if last_assistant:
            # Use first 300 chars of previous answer as retrieval context
            retrieval_query = f"{last_assistant[:300]} {request.message}"
            logger.info("Augmented retrieval query with last assistant context.")

    # Step 1 — Retrieve relevant chunks (using augmented query)
    chunks = retriever.retrieve(retrieval_query, top_k=config.TOP_K)

    # Step 2 — Generate grounded answer (or "I don't know" if no chunks pass threshold)
    response = generate_answer(
        message=request.message,
        history=request.history,
        retrieved_chunks=chunks,
    )

    return response
