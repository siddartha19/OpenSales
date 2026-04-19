"""Crustdata — decision-maker discovery + contact enrichment.

Two surfaces:
  1. find_decision_makers(company, titles)  -> name + linkedin (no credit burn)
  2. enrich_contact(linkedin_url)           -> email + verified info (CREDITS!)

Crustdata's API is filter-based. We use the people/search endpoint with
title + company filters. enrich_contact is the credit burner; only call after
VP review and user opt-in.
"""
from __future__ import annotations

from typing import Any

import httpx

from ..config import CRUSTDATA_API_KEY

BASE_URL = "https://api.crustdata.com"
TIMEOUT = 25.0


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Token {CRUSTDATA_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


async def find_decision_makers(
    company_name: str,
    target_titles: list[str] | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Find decision-makers at a known company by title patterns.

    Returns list of {name, title, company, linkedin_url} (no email yet).
    """
    if not CRUSTDATA_API_KEY:
        return []

    titles = target_titles or ["CEO", "Founder", "Co-Founder", "CTO", "Head of"]

    # Crustdata person search: filter by current_company name + current_title
    filters = [
        {
            "filter_type": "CURRENT_COMPANY",
            "type": "in",
            "value": [company_name],
        },
        {
            "filter_type": "CURRENT_TITLE",
            "type": "in",
            "value": titles,
        },
    ]
    payload = {"filters": filters, "page": 1, "limit": limit}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(
                f"{BASE_URL}/screener/person/search",
                headers=_headers(),
                json=payload,
            )
            if r.status_code >= 400:
                # fallback: title-only search if company filter rejected
                payload2 = {"filters": [filters[1]], "page": 1, "limit": limit}
                r2 = await client.post(
                    f"{BASE_URL}/screener/person/search",
                    headers=_headers(),
                    json=payload2,
                )
                r2.raise_for_status()
                data = r2.json()
            else:
                data = r.json()
        except httpx.HTTPError as e:
            return [{"_error": f"crustdata error: {e}"}]

    profiles = data.get("profiles") or data.get("results") or []
    out = []
    for p in profiles[:limit]:
        out.append(
            {
                "name": p.get("name")
                or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
                or "Unknown",
                "title": p.get("title") or p.get("current_title") or "",
                "company": company_name,
                "linkedin_url": p.get("linkedin_profile_url") or p.get("linkedin_url"),
            }
        )
    return out


async def enrich_contact(linkedin_url: str) -> dict[str, Any]:
    """Get verified email + extra context for a single person.

    BURNS CREDITS (1-7 per call). Only call after user confirms intent.
    """
    if not CRUSTDATA_API_KEY:
        return {"error": "crustdata key missing"}
    if not linkedin_url:
        return {"error": "no linkedin_url"}

    payload = {
        "linkedin_profile_url": linkedin_url,
        "enrich_email": True,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(
                f"{BASE_URL}/screener/person/enrich",
                headers=_headers(),
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as e:
            return {"error": f"crustdata enrich error: {e}"}

    # Crustdata can return a list or a dict depending on endpoint version
    if isinstance(data, list) and data:
        data = data[0]

    profile = data.get("profile") or data
    email = (
        profile.get("email")
        or (profile.get("emails") or [None])[0]
        or (data.get("business_emails") or [None])[0]
        or (data.get("personal_emails") or [None])[0]
    )

    return {
        "name": profile.get("name")
        or f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip(),
        "email": email,
        "title": profile.get("title") or profile.get("current_title"),
        "company": profile.get("company") or profile.get("current_company"),
        "raw": data,
    }


if __name__ == "__main__":
    import asyncio
    import json

    async def _smoke():
        print("--- find_decision_makers ---")
        dms = await find_decision_makers("Stripe", ["CEO", "Founder"], 3)
        print(json.dumps(dms, indent=2)[:1500])

    asyncio.run(_smoke())
