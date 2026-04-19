"""Firecrawl web scraping service.

Two use cases:
  1. Owner onboarding: scrape YOUR company website to build a company profile.
  2. Prospect research: scrape the PROSPECT's company website before drafting
     the cold email, so the AE can write a personalized one-liner about their
     business.

Uses the Firecrawl Python SDK (firecrawl-py) for clean markdown extraction.
Results are cached in SQLite to avoid redundant scrapes.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from ..config import DB_PATH, FIRECRAWL_API_KEY

# Cache TTL: 7 days for company website scrapes
CACHE_TTL_HOURS = 168


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_cache() -> None:
    """Create the firecrawl cache table if it doesn't exist."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS firecrawl_cache (
                url TEXT PRIMARY KEY,
                scraped_at TEXT NOT NULL,
                data_json TEXT NOT NULL
            )
        """)
        conn.commit()


init_cache()


def _get_cached(url: str) -> Optional[dict]:
    """Return cached scrape if fresh enough, else None."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT scraped_at, data_json FROM firecrawl_cache WHERE url = ?",
            (url,),
        ).fetchone()
    if not row:
        return None
    scraped_at = datetime.fromisoformat(row["scraped_at"])
    if datetime.utcnow() - scraped_at > timedelta(hours=CACHE_TTL_HOURS):
        return None
    try:
        return json.loads(row["data_json"])
    except Exception:
        return None


def _set_cached(url: str, data: dict) -> None:
    """Upsert scrape result into cache."""
    with _conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO firecrawl_cache (url, scraped_at, data_json)
               VALUES (?, ?, ?)""",
            (url, datetime.utcnow().isoformat(), json.dumps(data, default=str)),
        )
        conn.commit()


async def scrape_company_website(url: str) -> dict[str, Any]:
    """Scrape a company website and return structured intel.

    Returns: {
        url: str,
        markdown: str (first 3000 chars),
        title: str,
        description: str,
        source: "firecrawl_cache" | "firecrawl_live" | "error",
        scraped_at: str,
    }
    """
    if not url:
        return {"url": "", "source": "error", "error": "No URL provided"}

    # Normalize URL
    if not url.startswith("http"):
        url = f"https://{url}"

    # Check cache first
    cached = _get_cached(url)
    if cached:
        cached["source"] = "firecrawl_cache"
        return cached

    if not FIRECRAWL_API_KEY:
        return {"url": url, "source": "error", "error": "FIRECRAWL_API_KEY not set"}

    try:
        from firecrawl import AsyncFirecrawl

        fc = AsyncFirecrawl(api_key=FIRECRAWL_API_KEY)
        result = await fc.scrape(url, formats=["markdown"])

        # Extract useful fields
        markdown = ""
        title = ""
        description = ""

        if hasattr(result, "markdown"):
            markdown = (result.markdown or "")[:3000]
        elif isinstance(result, dict):
            markdown = (result.get("markdown") or "")[:3000]

        if hasattr(result, "metadata"):
            meta = result.metadata
            if hasattr(meta, "title"):
                title = meta.title or ""
            elif isinstance(meta, dict):
                title = meta.get("title", "")
            if hasattr(meta, "description"):
                description = meta.description or ""
            elif isinstance(meta, dict):
                description = meta.get("description", "")
        elif isinstance(result, dict) and "metadata" in result:
            meta = result["metadata"]
            title = meta.get("title", "")
            description = meta.get("description", "")

        data = {
            "url": url,
            "markdown": markdown,
            "title": title,
            "description": description,
            "source": "firecrawl_live",
            "scraped_at": datetime.utcnow().isoformat(),
        }

        # Cache it
        _set_cached(url, data)
        return data

    except Exception as e:
        return {
            "url": url,
            "source": "error",
            "error": str(e)[:500],
        }


async def scrape_and_summarize(url: str) -> dict[str, Any]:
    """Scrape a website and return a condensed summary for LLM consumption.

    Used for both owner company onboarding and prospect company research.
    Returns a dict with: summary, products, key_facts, industry.
    """
    raw = await scrape_company_website(url)

    if raw.get("source") == "error":
        return {
            "url": url,
            "summary": "",
            "products": "",
            "key_facts": [],
            "industry": "",
            "raw_markdown": "",
            "error": raw.get("error", "Scrape failed"),
        }

    return {
        "url": url,
        "summary": raw.get("description") or raw.get("title") or "",
        "raw_markdown": raw.get("markdown", "")[:2000],
        "title": raw.get("title", ""),
        "source": raw.get("source", ""),
    }
