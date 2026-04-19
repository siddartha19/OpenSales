"""QuickEmailVerification service — pattern discovery for prospect emails.

No caching / DB — just the vendor API + pattern logic.
Flow: generate 8 candidate emails for a person, verify each via QEV API,
return the first pattern that passes.  Then apply that pattern to build
the final email address.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from ..config import QUICK_EMAIL_VERIFICATION_API_KEY

logger = logging.getLogger(__name__)

QEV_BASE = "https://api.quickemailverification.com/v1/verify"
_TIMEOUT = 15  # seconds per verification call

# ── 8 standard patterns (order matters — stops on first hit) ──────────

PATTERNS = [
    ("firstname.lastname", lambda f, l, fi: f"{f}.{l}"),
    ("firstname",          lambda f, l, fi: f"{f}"),
    ("firstnamelastname",  lambda f, l, fi: f"{f}{l}"),
    ("f.lastname",         lambda f, l, fi: f"{fi}.{l}"),
    ("flastname",          lambda f, l, fi: f"{fi}{l}"),
    ("firstname-lastname", lambda f, l, fi: f"{f}-{l}"),
    ("firstname_lastname", lambda f, l, fi: f"{f}_{l}"),
    ("lastname.firstname", lambda f, l, fi: f"{l}.{f}"),
]


def _clean(name: str) -> str:
    """Lowercase, strip, keep only alpha chars."""
    return "".join(c for c in name.lower().strip() if c.isalpha())


# ── Single-email verification ────────────────────────────────────────

async def verify_email(email: str) -> dict:
    """Call QEV API for one email. Returns the raw JSON response."""
    if not QUICK_EMAIL_VERIFICATION_API_KEY:
        logger.warning("QUICK_EMAIL_VERIFICATION_API_KEY not set — skipping verification")
        return {}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                QEV_BASE,
                params={"email": email, "apikey": QUICK_EMAIL_VERIFICATION_API_KEY},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"QEV verify failed for {email}: {e}")
        return {}


def _is_acceptable(result: dict) -> bool:
    """A pattern wins if result == 'valid' OR safe_to_send is truthy."""
    if result.get("result") == "valid":
        return True
    # safe_to_send comes back as string "true"/"false" or bool
    sts = result.get("safe_to_send")
    if sts is True or (isinstance(sts, str) and sts.lower() == "true"):
        return True
    return False


# ── Pattern discovery ─────────────────────────────────────────────────

async def discover_email_pattern(
    first_name: str,
    last_name: str,
    domain: str,
) -> Optional[str]:
    """Try 8 email patterns via QEV API, return the first valid pattern name.

    Returns None if no pattern passes.
    """
    first = _clean(first_name)
    last = _clean(last_name)
    first_initial = first[0] if first else ""

    if not first or not last or not domain:
        logger.warning(f"Incomplete data for pattern discovery: first={first_name}, last={last_name}, domain={domain}")
        return None

    for pattern_name, builder in PATTERNS:
        local_part = builder(first, last, first_initial)
        email = f"{local_part}@{domain}"
        logger.info(f"QEV trying pattern {pattern_name} -> {email}")

        result = await verify_email(email)
        if _is_acceptable(result):
            logger.info(f"QEV pattern hit: {pattern_name} for {domain}")
            return pattern_name

    logger.warning(f"QEV: no valid pattern found for {first_name} {last_name} @ {domain}")
    return None


# ── Apply a known pattern ─────────────────────────────────────────────

def generate_email_from_pattern(
    first_name: str,
    last_name: str,
    domain: str,
    pattern: str,
) -> Optional[str]:
    """Given a pattern name, reconstruct the email for any person at that domain."""
    first = _clean(first_name)
    last = _clean(last_name)
    first_initial = first[0] if first else ""

    mapping = {name: builder for name, builder in PATTERNS}
    builder = mapping.get(pattern)
    if not builder:
        return None
    return f"{builder(first, last, first_initial)}@{domain}"


# ── High-level helper (the one agent.py will call) ────────────────────

async def find_verified_email(
    first_name: str,
    last_name: str,
    domain: str,
) -> Optional[str]:
    """Discover the pattern and return the constructed email, or None."""
    pattern = await discover_email_pattern(first_name, last_name, domain)
    if not pattern:
        return None
    return generate_email_from_pattern(first_name, last_name, domain, pattern)
