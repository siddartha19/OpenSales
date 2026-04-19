"""Exa neural search.

Two purposes:
  1. SDR: discover_companies — find target companies matching an ICP.
  2. AE:  find_recent_activity — fetch recent posts/talks for personalization.

Uses Exa's REST API directly via httpx — keeps deps light.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from ..config import EXA_API_KEY

EXA_URL = "https://api.exa.ai"
TIMEOUT = 20.0


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).netloc
        return host.lstrip("www.") if host else None
    except Exception:
        return None


def _company_name_from_title(title: str) -> str:
    """Best-effort: 'Velocity AI raises $4M seed - TechCrunch' -> 'Velocity AI'."""
    if not title:
        return "Unknown"
    # split on common separators
    parts = re.split(r"\s[-—|:·]\s", title)
    name = parts[0].strip()
    # cut off at first " raises" / " announces" / etc.
    name = re.split(
        r"\s+(raises|announces|launches|secures|closes|appoints|founder|CEO)",
        name,
        flags=re.I,
    )[0].strip()
    return name or title[:40]


async def discover_companies(
    icp_query: str,
    num_results: int = 10,
) -> list[dict[str, Any]]:
    """Find target companies matching the ICP.

    Returns a list of dicts: {name, url, domain, snippet, published_date}.
    """
    if not EXA_API_KEY:
        return []

    payload = {
        "query": icp_query,
        "type": "auto",
        "numResults": num_results,
        "useAutoprompt": True,
        "contents": {
            "text": {"maxCharacters": 600},
            "summary": True,
        },
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{EXA_URL}/search",
            headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

    out = []
    for item in data.get("results", []):
        title = item.get("title") or ""
        url = item.get("url") or ""
        snippet = (
            item.get("summary")
            or (item.get("text") or "")[:300]
            or (item.get("highlights") or [""])[0]
        )
        out.append(
            {
                "name": _company_name_from_title(title),
                "title": title,
                "url": url,
                "domain": _domain(url),
                "snippet": snippet.strip(),
                "published_date": item.get("publishedDate"),
            }
        )
    return out


async def find_recent_activity(
    person_name: str,
    company: str = "",
    num_results: int = 5,
) -> list[dict[str, Any]]:
    """Personalization signal: recent posts/talks/articles by this person.

    Used by the AE in cold email drafting.
    """
    if not EXA_API_KEY:
        return []

    query_parts = [person_name]
    if company:
        query_parts.append(company)
    query_parts.append("recent post OR talk OR interview OR blog")
    query = " ".join(query_parts)

    payload = {
        "query": query,
        "type": "auto",
        "numResults": num_results,
        "useAutoprompt": True,
        "contents": {"text": {"maxCharacters": 500}, "summary": True},
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{EXA_URL}/search",
            headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

    out = []
    for item in data.get("results", []):
        out.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "snippet": (item.get("summary") or item.get("text") or "")[:400].strip(),
                "published_date": item.get("publishedDate"),
            }
        )
    return out


if __name__ == "__main__":
    import asyncio
    import json

    async def _smoke():
        print("--- discover_companies ---")
        companies = await discover_companies(
            "Indian AI startup Series A funded 2024 2025 founder OR CEO", 5
        )
        print(json.dumps(companies, indent=2)[:1500])
        print(f"\nFound {len(companies)} companies")
        if companies:
            print("\n--- find_recent_activity ---")
            acts = await find_recent_activity("Sundar Pichai", "Google", 3)
            print(json.dumps(acts, indent=2)[:1000])

    asyncio.run(_smoke())
