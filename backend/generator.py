"""
generator.py
------------
Calls the Groq API (OpenAI-compatible) with a strict grounding system prompt
and the retrieved Amenify chunks as context.

Why Groq?
  • 100% FREE — 14,400 requests/day, 1,000 RPM, no credit card needed
  • Extremely fast inference (GroqChip hardware)
  • OpenAI-compatible SDK — same interface as openai.OpenAI()
  • Get your key at: https://console.groq.com

Model: llama-3.3-70b-versatile
  • 128K context window, excellent instruction following
  • Free on Groq's developer tier

Design:
  • System prompt instructs the model to answer ONLY from the provided context
  • If retrieval returned nothing (empty list), short-circuit to "I don't know"
  • Chat history forwarded for multi-turn conversations
  • Source deduplication before returning
"""

import logging
from typing import List, Dict, Any

from groq import Groq

import config
from models import ChatMessage, ChatResponse, Source

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a friendly and helpful AI customer support assistant for Amenify — \
a real estate technology company that provides lifestyle services (cleaning, chores, handyman, \
dog walking, food delivery, grocery delivery, and more) to multifamily residents across the USA.

STRICT RULES — you MUST follow these:
1. Answer ONLY using the information explicitly stated in the <context> block below.
2. Do NOT use any knowledge from your training data about Amenify or any other topic.
3. If the specific answer is not clearly stated in the context (including prices, timelines,
   or exact details), respond with EXACTLY:
   "I don't know based on the available Amenify information."
   Do NOT infer, estimate, or paraphrase information that isn't clearly written.
4. Do not make up prices, dates, URLs, or any details not in the context.
5. Be concise, friendly, and professional.
6. If multiple context chunks are relevant, combine them into a clear answer.
7. You may format your answer with bullet points if it aids clarity.
8. EXCEPTION — Conversational meta-questions: If the user asks about THIS conversation
   (e.g. 'what was my first question?', 'what did I ask earlier?', 'summarise what we discussed',
   'what have we talked about?'), answer directly from the chat history provided above —
   do NOT say 'I don't know' for these conversational questions.

Remember: accuracy matters more than appearing helpful. Never guess or infer."""


def _build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into a <context> block injected into the user message."""
    if not chunks:
        return ""
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[Source {i}: {chunk['page_title']} — {chunk['source_url']}]\n"
            f"{chunk['text']}"
        )
    return "<context>\n" + "\n\n---\n\n".join(parts) + "\n</context>"


def generate_answer(
    message: str,
    history: List[ChatMessage],
    retrieved_chunks: List[Dict[str, Any]],
) -> ChatResponse:
    """
    Generate a grounded answer from retrieved chunks using Groq's LLM API.

    Parameters
    ----------
    message         : The user's current question
    history         : Previous turns in this session
    retrieved_chunks: Chunks returned by retriever.retrieve()

    Returns
    -------
    ChatResponse with `answer` (str) and `sources` (list of Source)
    """
    # ── Short-circuit: no confident chunks → "I don't know" ──────────────────
    if not retrieved_chunks:
        logger.info("No chunks above threshold — returning 'I don't know'.")
        return ChatResponse(
            answer="I don't know based on the available Amenify information.",
            sources=[],
        )

    # ── Build message list ────────────────────────────────────────────────────
    context_block = _build_context_block(retrieved_chunks)

    user_message_with_context = (
        f"{context_block}\n\n"
        f"User question: {message}"
    )

    # System prompt first
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Prior conversation history
    for turn in history:
        messages.append({"role": turn.role, "content": turn.content})

    # Current user message WITH context injected
    messages.append({"role": "user", "content": user_message_with_context})

    # ── Call Groq (OpenAI-compatible) ─────────────────────────────────────────
    client = Groq(api_key=config.GROQ_API_KEY)

    logger.info("Calling %s via Groq for answer generation …", config.CHAT_MODEL)
    completion = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=messages,
        temperature=0.2,        # Low temperature → more factual, less creative
        max_tokens=512,
    )

    answer_text = completion.choices[0].message.content.strip()

    # ── If the LLM itself decided to say "I don't know", suppress sources ────
    # (Sources alongside "I don't know" is confusing — it implies we found something)
    if "i don't know" in answer_text.lower():
        logger.info("LLM returned 'I don't know' — suppressing sources.")
        return ChatResponse(answer=answer_text, sources=[])

    # ── Deduplicate sources by URL and title ─────────────────────────────────
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    sources: List[Source] = []
    for chunk in retrieved_chunks:
        url = chunk.get("source_url", "")
        title = chunk.get("page_title", "Amenify")
        # Skip if we've already added this URL or an identical title
        if not url or url in seen_urls or title in seen_titles:
            continue
        seen_urls.add(url)
        seen_titles.add(title)
        sources.append(Source(url=url, title=title))

    logger.info("Generated answer (%d chars) with %d sources.", len(answer_text), len(sources))

    return ChatResponse(answer=answer_text, sources=sources)
