"""Session persistence — SQLite-backed CRUD for campaign sessions.

Each session maps to one Google Sheet worksheet tab.
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from ..config import DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id     TEXT PRIMARY KEY,
                name           TEXT NOT NULL,
                worksheet_name TEXT NOT NULL,
                created_at     TEXT NOT NULL,
                phase          TEXT NOT NULL DEFAULT 'idle',
                run_ids_json   TEXT NOT NULL DEFAULT '[]',
                prospects_json TEXT NOT NULL DEFAULT '[]',
                drafts_json    TEXT NOT NULL DEFAULT '[]',
                activity_json  TEXT NOT NULL DEFAULT '[]'
            )
        """)
        conn.commit()
        # Migration: add activity_json if missing (existing DBs)
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN activity_json TEXT NOT NULL DEFAULT '[]'")
            conn.commit()
        except Exception:
            pass  # column already exists


_ensure_table()


def _sanitize_worksheet_name(name: str) -> str:
    """Google Sheets worksheet names: max 100 chars, no [ ] * / \\ ? :"""
    clean = re.sub(r'[\[\]*/?:\\]', '', name).strip()
    if not clean:
        clean = "Session"
    return clean[:100]


def create_session(name: str) -> dict:
    """Create a new session. Returns the session dict."""
    session_id = f"ses_{uuid.uuid4().hex[:10]}"
    worksheet_name = _sanitize_worksheet_name(name)

    # Dedupe worksheet name if it already exists
    existing = [s["worksheet_name"] for s in list_sessions()]
    if worksheet_name in existing:
        worksheet_name = f"{worksheet_name} ({session_id[-6:]})"

    now = datetime.utcnow().isoformat()

    with _conn() as conn:
        conn.execute(
            """INSERT INTO sessions (session_id, name, worksheet_name, created_at, phase, run_ids_json, prospects_json, drafts_json)
               VALUES (?, ?, ?, ?, 'idle', '[]', '[]', '[]')""",
            (session_id, name, worksheet_name, now),
        )
        conn.commit()

    return _get_session(session_id)


def list_sessions() -> list[dict]:
    """Return all sessions, newest first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_session(session_id: str) -> Optional[dict]:
    return _get_session(session_id)


def _get_session(session_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def update_session(
    session_id: str,
    *,
    name: Optional[str] = None,
    phase: Optional[str] = None,
    run_ids: Optional[list[str]] = None,
    prospects_json: Optional[str] = None,
    drafts_json: Optional[str] = None,
    activity_json: Optional[str] = None,
) -> Optional[dict]:
    """Update fields on a session. Only non-None args are written."""
    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if phase is not None:
        updates.append("phase = ?")
        params.append(phase)
    if run_ids is not None:
        updates.append("run_ids_json = ?")
        params.append(json.dumps(run_ids))
    if prospects_json is not None:
        updates.append("prospects_json = ?")
        params.append(prospects_json)
    if drafts_json is not None:
        updates.append("drafts_json = ?")
        params.append(drafts_json)
    if activity_json is not None:
        updates.append("activity_json = ?")
        params.append(activity_json)

    if not updates:
        return _get_session(session_id)

    params.append(session_id)
    with _conn() as conn:
        conn.execute(
            f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?",
            params,
        )
        conn.commit()

    return _get_session(session_id)


def add_run_id(session_id: str, run_id: str) -> None:
    """Append a run_id to the session's run list."""
    sess = _get_session(session_id)
    if not sess:
        return
    ids = json.loads(sess.get("run_ids_json", "[]"))
    if run_id not in ids:
        ids.append(run_id)
        update_session(session_id, run_ids=ids)


def delete_session(session_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM sessions WHERE session_id = ?", (session_id,)
        )
        conn.commit()
    return cur.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # Parse JSON fields for the API response
    d["run_ids"] = json.loads(d.pop("run_ids_json", "[]"))
    return d
