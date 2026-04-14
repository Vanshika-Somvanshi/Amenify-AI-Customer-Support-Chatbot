"""
chunker.py
----------
Splits raw page text into overlapping chunks of ~300 tokens.

Why chunking?
  • Language models have context limits  
  • Smaller chunks → more precise retrieval (each chunk is a focused topic)
  • Overlapping windows (50 tokens) prevent losing context at chunk boundaries

Output format per chunk:
    {
        "chunk_id":   "amenify.com/cleaningservices1_0",
        "source_url": "https://amenify.com/cleaningservices1",
        "page_title": "Cleaning Services | Amenify",
        "text":       "..."
    }
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

INPUT_PATH  = Path(__file__).parent / "raw_pages.json"
OUTPUT_PATH = Path(__file__).parent / "chunks.json"

# Approximate token counts (1 token ≈ 4 characters for English)
CHUNK_SIZE    = 300   # tokens per chunk
CHUNK_OVERLAP = 50    # tokens of overlap between consecutive chunks
CHARS_PER_TOKEN = 4   # rough approximation


def _token_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text into overlapping chunks by approximate token count.
    We use character count as a proxy (1 token ≈ 4 chars).

    This is simpler than using tiktoken and avoids an extra dependency
    in the ingestion step — good enough for this use case.
    """
    char_size    = chunk_size * CHARS_PER_TOKEN
    char_overlap = overlap    * CHARS_PER_TOKEN
    step         = char_size - char_overlap

    chunks = []
    start  = 0
    while start < len(text):
        end   = start + char_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


def chunk_pages(pages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Take a list of { url, title, text } page dicts and produce
    a flat list of chunk dicts.
    """
    all_chunks: List[Dict[str, Any]] = []

    for page in pages:
        url   = page.get("url", "")
        title = page.get("title", "Amenify")
        text  = page.get("text", "")

        if not text.strip():
            logger.warning("Empty text for %s — skipping.", url)
            continue

        # Create a short slug for the chunk_id from the URL path
        slug = re.sub(r"[^a-z0-9]", "_", url.lower().split("amenify.com")[-1])[:40]
        slug = slug.strip("_") or "home"

        text_chunks = _token_split(text, CHUNK_SIZE, CHUNK_OVERLAP)

        for idx, chunk_text in enumerate(text_chunks):
            all_chunks.append(
                {
                    "chunk_id":   f"{slug}_{idx}",
                    "source_url": url,
                    "page_title": title,
                    "text":       chunk_text,
                }
            )

        logger.info("  %s → %d chunks", url, len(text_chunks))

    logger.info("Total chunks produced: %d", len(all_chunks))
    return all_chunks


if __name__ == "__main__":
    if not INPUT_PATH.exists():
        logger.error("raw_pages.json not found. Run scraper.py first.")
        raise SystemExit(1)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        pages = json.load(f)

    chunks = chunk_pages(pages)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    logger.info("Saved %d chunks to %s", len(chunks), OUTPUT_PATH)
