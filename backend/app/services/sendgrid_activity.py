"""SendGrid Email Activity API client.

Why this exists: SendGrid's `sg.send()` returns 202 (Accepted) the moment
the API gateway takes the message — that does NOT mean it was delivered.
The Email Logs UI in the SendGrid dashboard only shows messages that
actually reached the SMTP edge; silently-dropped ones are missing from
that view.

The Activity API (https://docs.sendgrid.com/api-reference/e-mail-activity)
is the source of truth: every message has a `status` of
  - delivered           ← actually accepted by recipient MX
  - not_delivered       ← bounced / blocked at SMTP
  - processed           ← still in flight
  - deferred / dropped  ← retry / hard fail

This module wraps that API. Used by /api/diagnostics/sendgrid-activity
and the e2e test script.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable

import httpx

from ..config import SENDGRID_API_KEY

logger = logging.getLogger(__name__)

_BASE = "https://api.sendgrid.com/v3"
_TIMEOUT = 15.0


async def list_recent(limit: int = 25) -> list[dict[str, Any]]:
    """Most recent email activity, newest first.

    Each row: {msg_id, from_email, to_email, subject, status,
               last_event_time, opens_count, clicks_count}
    Returns [] on failure (logs the error).
    """
    if not SENDGRID_API_KEY:
        return []
    url = f"{_BASE}/messages"
    headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url, headers=headers, params={"limit": limit})
            if r.status_code == 401:
                logger.warning("SendGrid Activity API: 401 — API key lacks 'Email Activity' scope")
                return []
            if r.status_code != 200:
                logger.warning(f"SendGrid Activity API: HTTP {r.status_code}: {r.text[:200]}")
                return []
            return r.json().get("messages", [])
    except Exception as e:
        logger.error(f"SendGrid Activity API failed: {e}")
        return []


async def lookup_by_message_ids(message_ids: Iterable[str]) -> dict[str, dict[str, Any]]:
    """Resolve our X-Message-Id values to delivery status.

    SendGrid's Activity API stores the X-Message-Id as a *prefix* of `msg_id`
    (e.g. `Zg7MtQA7RXe_g9EbkoZ-fg.recvd-78d9866fff-...`). So we fetch the
    last ~50 rows and match by prefix.

    Returns: {<our_msg_id>: <activity_row>}.  Missing keys = not found yet
    (likely too soon — try again in a few seconds).
    """
    wanted = {mid for mid in message_ids if mid}
    if not wanted:
        return {}
    rows = await list_recent(limit=50)
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        full = row.get("msg_id", "")
        prefix = full.split(".", 1)[0]
        if prefix in wanted:
            out[prefix] = row
    return out


async def status_summary(limit: int = 25) -> dict[str, Any]:
    """Aggregate status counts across the most recent activity."""
    rows = await list_recent(limit=limit)
    counts: dict[str, int] = {}
    for r in rows:
        s = r.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    return {
        "total": len(rows),
        "counts": counts,
        "rows": rows,
    }


if __name__ == "__main__":
    import asyncio
    import json

    async def _main():
        s = await status_summary(limit=25)
        print(json.dumps(s, indent=2)[:2000])

    asyncio.run(_main())
