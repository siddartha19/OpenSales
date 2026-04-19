"""Centralized config. All env reading goes through here.

Loaded once at import. Fail loud if a required key is missing — better than
debugging a 30-second silent timeout three layers down.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root (one level up from backend/)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")


def _strip(s: str | None) -> str:
    if s is None:
        return ""
    return s.strip().strip("'").strip('"')


# ---------- LLM ----------
OPENROUTER_API_KEY = _strip(os.getenv("OPENROUTER_API_KEY"))
LLM_MODEL = _strip(os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001"))

# ---------- Email ----------
SENDGRID_API_KEY = _strip(os.getenv("SENDGRID_API_KEY"))
SENDGRID_FROM_EMAIL = _strip(os.getenv("SENDGRID_FROM_EMAIL", "demo@opencode.com"))
SENDGRID_FROM_NAME = _strip(os.getenv("SENDGRID_FROM_NAME", "SalesOS Demo"))
EMAIL_FALLBACK_RECIPIENT = _strip(os.getenv("EMAIL_FALLBACK_RECIPIENT", "demo@salesos.opensource"))

# ---------- Search / enrichment ----------
EXA_API_KEY = _strip(os.getenv("EXA_API_KEY"))
CRUSTDATA_API_KEY = _strip(os.getenv("CRUSTDATA_API_KEY"))
APIFY_API_TOKEN = _strip(os.getenv("APIFY_API_TOKEN"))
APIFY_LINKEDIN_ACTOR_ID = _strip(
    os.getenv("APIFY_LINKEDIN_ACTOR_ID", "dev_fusion~linkedin-profile-scraper")
)
QUICK_EMAIL_VERIFICATION_API_KEY = _strip(os.getenv("QUICK_EMAIL_VERIFICATION_API_KEY"))

# ---------- Web Scraping (Firecrawl) ----------
FIRECRAWL_API_KEY = _strip(os.getenv("FIRECRAWL_API_KEY"))

# ---------- Sheets ----------
GOOGLE_SHEET_ID = _strip(os.getenv("GOOGLE_SHEET_ID"))

# ---------- Auth ----------
AUTH_EMAIL = _strip(os.getenv("AUTH_EMAIL", "hr@alerahq.com"))
AUTH_PASSWORD = _strip(os.getenv("AUTH_PASSWORD", "Admin@123"))
AUTH_SECRET = _strip(os.getenv("AUTH_SECRET", "change-me"))

# ---------- CORS ----------
ALLOWED_ORIGINS = _strip(os.getenv("ALLOWED_ORIGINS", "*"))

# ---------- DB ----------
DB_PATH = str(REPO_ROOT / "agent_runs.db")


def health_summary() -> dict:
    """Returns a config-presence summary for /api/health (no values, just boolean)."""
    return {
        "openrouter": bool(OPENROUTER_API_KEY),
        "sendgrid": bool(SENDGRID_API_KEY),
        "exa": bool(EXA_API_KEY),
        "crustdata": bool(CRUSTDATA_API_KEY),
        "apify": bool(APIFY_API_TOKEN),
        "google_sheet_id": bool(GOOGLE_SHEET_ID),
        "quick_email_verification": bool(QUICK_EMAIL_VERIFICATION_API_KEY),
        "firecrawl": bool(FIRECRAWL_API_KEY),
        "model": LLM_MODEL,
    }
