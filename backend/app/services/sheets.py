"""Google Sheets pipeline writer.

Adapts the existing top-level google_sheets.py to write sales-pipeline rows.
Stages: Sourced -> Researched -> Outreach Sent -> Replied -> Qualified -> Demo Booked -> Lost
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

# Reuse the OAuth flow already wired in repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Force absolute paths so the OAuth file resolves regardless of cwd
_client_env = os.environ.get("GOOGLE_OAUTH_CLIENT_JSON", "./client_secret.json")
_token_env = os.environ.get("GOOGLE_OAUTH_TOKEN_JSON", "./google_token.json")
if not Path(_client_env).is_absolute():
    os.environ["GOOGLE_OAUTH_CLIENT_JSON"] = str((REPO_ROOT / _client_env).resolve())
if not Path(_token_env).is_absolute():
    os.environ["GOOGLE_OAUTH_TOKEN_JSON"] = str((REPO_ROOT / _token_env).resolve())

try:
    from google_sheets import append_rows, open_sheet, read_all, write_header  # type: ignore
except Exception as _e:  # pragma: no cover
    append_rows = None  # type: ignore
    open_sheet = None  # type: ignore
    read_all = None  # type: ignore
    write_header = None  # type: ignore
    _IMPORT_ERROR = _e
else:
    _IMPORT_ERROR = None


PIPELINE_HEADERS = [
    "Run ID",
    "Company",
    "Decision Maker",
    "Title",
    "LinkedIn URL",
    "Email",
    "Stage",
    "Subject Sent",
    "Sent At",
    "Replied?",
    "Reply Snippet",
    "Next Action",
    "Fit Score",
    "Why",
]
DEFAULT_WORKSHEET = "SalesOS"


def _ensure_header(worksheet: str = DEFAULT_WORKSHEET) -> None:
    if write_header is None:
        return
    try:
        write_header(PIPELINE_HEADERS, worksheet=worksheet)
    except Exception:
        pass


def log_prospect(
    *,
    run_id: str,
    company: str,
    dm_name: str,
    title: str,
    linkedin_url: str | None,
    email: str | None,
    stage: str = "Sourced",
    subject: str | None = None,
    fit_score: float = 0.7,
    why: str = "",
    worksheet: str | None = None,
) -> dict:
    """Append a pipeline row. Returns {success, row_index, error?}."""
    ws_name = worksheet or DEFAULT_WORKSHEET
    if append_rows is None:
        return {"success": False, "error": f"sheets unavailable: {_IMPORT_ERROR}"}

    _ensure_header(ws_name)
    sent_at = datetime.utcnow().isoformat() if stage == "Outreach Sent" else ""
    row = [
        run_id,
        company,
        dm_name,
        title or "",
        linkedin_url or "",
        email or "",
        stage,
        subject or "",
        sent_at,
        "",  # Replied?
        "",  # Reply Snippet
        "",  # Next Action
        f"{fit_score:.2f}",
        why,
    ]
    try:
        append_rows([row], worksheet=ws_name)
        rows = read_all(worksheet=ws_name)  # type: ignore
        return {"success": True, "row_index": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_stage(row_index: int, new_stage: str, worksheet: str | None = None) -> dict:
    ws_name = worksheet or DEFAULT_WORKSHEET
    if open_sheet is None:
        return {"success": False, "error": "sheets unavailable"}
    try:
        ws = open_sheet(ws_name)  # type: ignore
        # Stage is column G (7)
        ws.update_cell(row_index, 7, new_stage)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_pipeline_summary(worksheet: str | None = None) -> dict[str, int]:
    """Counts per stage. Used by the dashboard header."""
    ws_name = worksheet or DEFAULT_WORKSHEET
    if read_all is None:
        return {}
    try:
        rows = read_all(worksheet=ws_name)  # type: ignore
    except Exception:
        return {}
    if not rows or len(rows) < 2:
        return {}
    counts: dict[str, int] = {}
    for row in rows[1:]:
        stage = row[6] if len(row) > 6 else ""
        if stage:
            counts[stage] = counts.get(stage, 0) + 1
    return counts


def init_session_worksheet(worksheet: str) -> dict:
    """Create the worksheet tab and write the header row. Called once when a session is created."""
    if write_header is None:
        return {"success": False, "error": f"sheets unavailable: {_IMPORT_ERROR}"}
    try:
        write_header(PIPELINE_HEADERS, worksheet=worksheet)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def sheet_url() -> str | None:
    from ..config import GOOGLE_SHEET_ID

    raw = GOOGLE_SHEET_ID
    if not raw:
        return None
    if "spreadsheets/d/" in raw:
        return raw
    return f"https://docs.google.com/spreadsheets/d/{raw}/edit"


if __name__ == "__main__":
    _ensure_header()
    res = log_prospect(
        run_id="smoke-test",
        company="Velocity AI",
        dm_name="Riya M.",
        title="CEO",
        linkedin_url="https://linkedin.com/in/riya-m",
        email="riya@velocity.ai",
        stage="Sourced",
        fit_score=0.85,
        why="Series A AI startup, recent eval pipeline post",
    )
    print(res)
    print("Pipeline summary:", get_pipeline_summary())
