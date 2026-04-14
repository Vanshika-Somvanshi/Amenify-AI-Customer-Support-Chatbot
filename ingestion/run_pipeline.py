"""
run_pipeline.py
---------------
Orchestrates the full offline ingestion pipeline in one command:

    python ingestion/run_pipeline.py

Steps:
  1. Scrape Amenify pages  → ingestion/raw_pages.json
  2. Chunk the text        → ingestion/chunks.json
  3. Embed + build index   → backend/data/faiss.index
                           → backend/data/chunks.json

Run this ONCE locally before deploying.  Commit backend/data/ to git so
Render doesn't need an OpenAI key at deploy time (just at runtime).
"""

import logging
import sys
from pathlib import Path

# Make sure local module imports work regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

from scraper  import run_scraper
from chunker  import chunk_pages
from embedder import build_index

import json

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)

RAW_PATH    = Path(__file__).parent / "raw_pages.json"
CHUNKS_PATH = Path(__file__).parent / "chunks.json"


def main() -> None:
    logger.info("=" * 60)
    logger.info("STEP 1/3 — Scraping Amenify pages")
    logger.info("=" * 60)
    pages = run_scraper()
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    logger.info("Scraped %d pages.\n", len(pages))

    logger.info("=" * 60)
    logger.info("STEP 2/3 — Chunking text")
    logger.info("=" * 60)
    chunks = chunk_pages(pages)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    logger.info("Created %d chunks.\n", len(chunks))

    logger.info("=" * 60)
    logger.info("STEP 3/3 — Embedding + building FAISS index")
    logger.info("=" * 60)
    build_index(chunks)

    logger.info("=" * 60)
    logger.info("Pipeline complete!")
    logger.info(
        "Next steps:\n"
        "  1. Commit backend/data/faiss.index and backend/data/chunks.json to git\n"
        "  2. Deploy backend/ to Render\n"
        "  3. Deploy frontend/ to Vercel\n"
    )


if __name__ == "__main__":
    main()
