"""LangChain @tool wrappers around services.

These are what the SDR and AE agents actually call. Keeping them as thin
adapters: services do the work, tools handle the LLM-facing schema.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.tools import tool

from .services import apify as apify_svc
from .services import crustdata as cd_svc
from .services import mailer as email_svc
from .services import exa as exa_svc
from .services import sheets as sheets_svc


# ---------- SDR tools ----------


@tool
async def discover_companies(icp_query: str, num_results: int = 10) -> str:
    """Discover target companies matching an ICP via Exa neural search.

    Args:
      icp_query: A focused query string. INCLUDE geography, stage, vertical, signals.
        Good: 'Indian AI startup Series A funded 2024 2025 founder OR CEO'
        Bad: 'AI companies'
      num_results: How many companies to return (default 10).

    Returns: JSON list of {name, url, domain, snippet, published_date}.
    """
    results = await exa_svc.discover_companies(icp_query, num_results)
    return json.dumps(results)[:6000]


@tool
async def find_decision_makers(
    company_name: str,
    target_titles: list[str] | None = None,
    limit: int = 2,
) -> str:
    """Find decision-makers at a known company via Crustdata.

    Args:
      company_name: Exact company name.
      target_titles: e.g. ['CEO', 'Founder', 'Co-Founder', 'CTO'].
      limit: max people to return (default 2).

    Returns: JSON list of {name, title, company, linkedin_url}.
    """
    titles = target_titles or ["CEO", "Founder", "Co-Founder", "CTO", "Head of"]
    results = await cd_svc.find_decision_makers(company_name, titles, limit)
    return json.dumps(results)[:4000]


# ---------- AE tools ----------


@tool
async def enrich_contact(linkedin_url: str) -> str:
    """Get verified email + extra context for a prospect.

    BURNS CRUSTDATA CREDITS. Only call after VP/user has approved the prospect.
    """
    result = await cd_svc.enrich_contact(linkedin_url)
    return json.dumps(result)[:4000]


@tool
async def scrape_linkedin_profile(linkedin_url: str) -> str:
    """Scrape LinkedIn profile (about, experience, recent posts) via Apify.
    Falls back to Exa if Apify fails or times out (15s).
    Cached aggressively.
    """
    result = await apify_svc.scrape_linkedin_profile(
        linkedin_url, exa_fallback_fn=exa_svc.find_recent_activity
    )
    # Trim experience array for prompt size
    if "experience" in result and isinstance(result["experience"], list):
        result["experience"] = result["experience"][:3]
    return json.dumps(result)[:4000]


@tool
async def find_recent_activity(person_name: str, company: str = "") -> str:
    """Web-wide recent activity (talks, blog, GitHub, Twitter) via Exa.
    Used for cold email personalization."""
    results = await exa_svc.find_recent_activity(person_name, company, num_results=4)
    return json.dumps(results)[:3000]


@tool
def send_outreach_email(
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
) -> str:
    """Send a cold email via SendGrid.

    Returns JSON with success, message_id.
    """
    res = email_svc.send_email(to_email, to_name, subject, body)
    return json.dumps(res)


@tool
def log_prospect_to_sheet(
    run_id: str,
    company: str,
    dm_name: str,
    title: str,
    linkedin_url: str = "",
    email: str = "",
    stage: str = "Sourced",
    subject: str = "",
    fit_score: float = 0.7,
    why: str = "",
) -> str:
    """Append a prospect/outreach row to the Google Sheets pipeline.

    stage: one of Sourced / Researched / Outreach Sent / Replied / Qualified.
    """
    res = sheets_svc.log_prospect(
        run_id=run_id,
        company=company,
        dm_name=dm_name,
        title=title,
        linkedin_url=linkedin_url,
        email=email,
        stage=stage,
        subject=subject,
        fit_score=fit_score,
        why=why,
    )
    return json.dumps(res)


@tool
def update_pipeline_stage(row_index: int, new_stage: str) -> str:
    """Update the stage of a row in the pipeline sheet."""
    res = sheets_svc.update_stage(row_index, new_stage)
    return json.dumps(res)


SDR_TOOLS = [discover_companies, find_decision_makers]
AE_TOOLS = [
    enrich_contact,
    scrape_linkedin_profile,
    find_recent_activity,
    send_outreach_email,
    log_prospect_to_sheet,
    update_pipeline_stage,
]
