"""
scraper.py
----------
Crawls a curated list of Amenify pages and extracts clean body text.

Why a curated list instead of a full crawl?
  • Amenify uses Squarespace (some pages render client-side JS)
  • A curated list gives us the highest-signal pages (service pages, FAQ, about)
  • Avoids scraping irrelevant pages like blog archives or city-specific duplicates

Output:
  raw_pages.json — list of { url, title, text } objects saved next to this script
"""

import json
import time
import logging
from pathlib import Path
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

# ── Target pages ──────────────────────────────────────────────────────────────
# We select the highest-signal pages from amenify.com's navigation.
TARGET_URLS: List[str] = [
    "https://amenify.com",
    "https://amenify.com/about-us",
    "https://amenify.com/resident-services",
    "https://amenify.com/cleaningservices1",
    "https://amenify.com/choreservices1",
    "https://amenify.com/handymanservices1",
    "https://amenify.com/groceryservices1",
    "https://amenify.com/dog-walking-services",
    "https://amenify.com/professional-moving-services",
    "https://amenify.com/movingoutservices1",
    "https://amenify.com/resident-protection-plan",
    "https://amenify.com/property-managers-2",
    "https://amenify.com/providers-1",
    "https://amenify.com/amenify-platform",
    "https://amenify.com/amenify-technology",
    "https://amenify.com/acommerce",
    "https://amenify.com/mission-and-values",
]

# HTML tags to remove before extracting text (navigation noise)
TAGS_TO_REMOVE = ["nav", "header", "footer", "script", "style", "noscript", "iframe"]

# Politeness delay between requests (seconds)
REQUEST_DELAY = 1.5

OUTPUT_PATH = Path(__file__).parent / "raw_pages.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AmenifyChatbotScraper/1.0; "
        "+https://amenify.com)"
    )
}


def scrape_page(url: str) -> Dict[str, str] | None:
    """
    Fetch a single URL and extract clean text.

    Returns:
        { "url": str, "title": str, "text": str }
        or None if the request fails.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove noisy elements
    for tag in TAGS_TO_REMOVE:
        for el in soup.find_all(tag):
            el.decompose()

    # Extract page title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Amenify"

    # Get all visible text
    text = soup.get_text(separator=" ", strip=True)

    # Basic cleanup: collapse multiple spaces/newlines
    import re
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) < 100:
        logger.warning("Very short content for %s — may be JS-rendered, skipping.", url)
        return None

    logger.info("✓ Scraped %s (%d chars)", url, len(text))
    return {"url": url, "title": title, "text": text}


def run_scraper() -> List[Dict[str, str]]:
    """Scrape all TARGET_URLS and return the list of page dicts."""
    pages = []
    for url in TARGET_URLS:
        page = scrape_page(url)
        if page:
            pages.append(page)
        time.sleep(REQUEST_DELAY)

    logger.info("Scraped %d/%d pages successfully.", len(pages), len(TARGET_URLS))
    return pages


if __name__ == "__main__":
    pages = run_scraper()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    logger.info("Saved raw pages to %s", OUTPUT_PATH)
