"""Apify LinkedIn scrape + SQLite cache + Exa fallback.

Apify scrapers are slow (10-30s) and ~20% failure rate. The whole design
is defensive:
  1. Cache check (SQLite) — instant return if hit.
  2. Live Apify call with hard 15s timeout.
  3. On timeout/error: fall through to caller-provided exa_fallback_fn.

Pre-warm cache before demos via prewarm_cache().
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable

import httpx

from ..config import APIFY_API_TOKEN, APIFY_LINKEDIN_ACTOR_ID, DB_PATH

TIMEOUT_S = 15
CACHE_TTL_HOURS = 168  # 7 days — for hackathon demo, cache aggressively


def init_cache() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS apify_cache (
                linkedin_url TEXT PRIMARY KEY,
                scraped_at TEXT,
                data_json TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _cache_get(linkedin_url: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT scraped_at, data_json FROM apify_cache WHERE linkedin_url = ?",
            (linkedin_url,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    try:
        scraped_at = datetime.fromisoformat(row[0])
    except Exception:
        return None
    if datetime.utcnow() - scraped_at > timedelta(hours=CACHE_TTL_HOURS):
        return None
    return {"source": "apify_cache", "scraped_at": row[0], **json.loads(row[1])}


def _cache_put(linkedin_url: str, data: dict) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO apify_cache (linkedin_url, scraped_at, data_json) VALUES (?, ?, ?)",
            (linkedin_url, datetime.utcnow().isoformat(), json.dumps(data)),
        )
        conn.commit()
    finally:
        conn.close()


def _normalize(raw: dict) -> dict:
    """Normalize across Apify actor variants. Different actors use different
    field names: profileUrl/url/linkedinUrl, about/summary/headline, etc."""
    return {
        "headline": raw.get("headline") or raw.get("title") or "",
        "about": raw.get("about") or raw.get("summary") or raw.get("description") or "",
        "experience": raw.get("experience") or raw.get("positions") or [],
        "recent_posts": (
            raw.get("posts")
            or raw.get("recent_posts")
            or raw.get("activity")
            or []
        )[:5],
        "name": (
            raw.get("name")
            or raw.get("fullName")
            or f"{raw.get('firstName', '')} {raw.get('lastName', '')}".strip()
        ),
        "location": raw.get("location") or raw.get("addressWithCountry"),
        "raw_keys": list(raw.keys())[:20],  # for debugging actor schemas
    }


async def scrape_linkedin_profile(
    linkedin_url: str,
    exa_fallback_fn: Callable[[str, str], Awaitable[list[dict]]] | None = None,
) -> dict[str, Any]:
    """Returns LinkedIn profile data.

    Order of operations:
      1. Cache check — instant return if hit.
      2. Live Apify call, 15s hard timeout.
      3. On any failure: exa_fallback_fn(person_name, "") if provided,
         else return {source: 'none', error: ...}.
    """
    if not linkedin_url:
        return {"source": "none", "error": "no linkedin_url"}

    init_cache()
    cached = _cache_get(linkedin_url)
    if cached:
        return cached

    if not APIFY_API_TOKEN:
        return await _fallback(linkedin_url, "no apify token", exa_fallback_fn)

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S + 2) as client:
            # Multiple actor input shapes; try common keys.
            r = await client.post(
                f"https://api.apify.com/v2/acts/{APIFY_LINKEDIN_ACTOR_ID}/run-sync-get-dataset-items",
                params={"token": APIFY_API_TOKEN, "timeout": TIMEOUT_S},
                json={
                    "profileUrls": [linkedin_url],
                    "urls": [linkedin_url],
                    "profileUrl": linkedin_url,
                },
            )
            r.raise_for_status()
            items = r.json()
            if not items:
                raise ValueError("Empty Apify result")
            data = _normalize(items[0])
            data["source"] = "apify_live"
            data["latency_s"] = round(time.time() - start, 2)
            _cache_put(linkedin_url, data)
            return data
    except (httpx.TimeoutException, httpx.HTTPError, ValueError, Exception) as e:
        return await _fallback(linkedin_url, str(e), exa_fallback_fn)


async def _fallback(
    linkedin_url: str,
    reason: str,
    exa_fallback_fn: Callable[[str, str], Awaitable[list[dict]]] | None,
) -> dict:
    if exa_fallback_fn is None:
        return {"source": "none", "error": reason}
    person_name = (
        linkedin_url.rstrip("/").split("/")[-1].replace("-", " ").title()
    )
    try:
        exa_data = await exa_fallback_fn(person_name, "")
    except Exception as e:
        return {"source": "none", "error": f"{reason}; exa also failed: {e}"}
    return {
        "source": "exa_fallback",
        "fallback_reason": reason,
        "name": person_name,
        "recent_posts": [
            {"title": d.get("title"), "snippet": d.get("snippet"), "url": d.get("url")}
            for d in (exa_data or [])
        ],
        "about": "",
        "experience": [],
    }


async def prewarm_cache(linkedin_urls: list[str]) -> dict:
    """Pre-warm cache for demo recipients. Run via scripts/prewarm.py."""
    init_cache()
    sem = asyncio.Semaphore(2)
    results: dict = {"hit": [], "live": [], "failed": []}

    async def _one(url: str):
        async with sem:
            r = await scrape_linkedin_profile(url)
            src = r.get("source", "none")
            if src == "apify_cache":
                results["hit"].append(url)
            elif src == "apify_live":
                results["live"].append(url)
            else:
                results["failed"].append({"url": url, "reason": r.get("error") or r.get("fallback_reason")})

    await asyncio.gather(*(_one(u) for u in linkedin_urls))
    return results


if __name__ == "__main__":
    init_cache()

    async def _smoke():
        url = "https://linkedin.com/in/sundar-pichai"
        print("--- first call ---")
        r1 = await scrape_linkedin_profile(url)
        print({"source": r1.get("source"), "name": r1.get("name"), "latency": r1.get("latency_s")})
        print("--- second call (cache hit expected) ---")
        r2 = await scrape_linkedin_profile(url)
        print({"source": r2.get("source"), "name": r2.get("name")})

    asyncio.run(_smoke())
