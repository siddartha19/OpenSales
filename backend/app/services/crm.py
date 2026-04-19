"""CRM persistence — SQLite-backed notes and manual stage overrides.

Two tables:
  1. crm_notes     — timestamped comments on a prospect (keyed by session_id + dm_name)
  2. crm_stages    — manual stage overrides (latest wins, keyed by session_id + dm_name)

The composite key (session_id, dm_name) uniquely identifies a prospect since
prospect IDs are ephemeral (generated at query time).  This is stable because
dm_name is unique within a session.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from ..config import DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crm_notes (
                id          TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL,
                dm_name     TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_crm_notes_lookup
            ON crm_notes(session_id, dm_name, created_at DESC)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crm_stages (
                session_id  TEXT NOT NULL,
                dm_name     TEXT NOT NULL,
                stage       TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                PRIMARY KEY (session_id, dm_name)
            )
        """)
        conn.commit()


_ensure_tables()


# ---------- Notes ----------


def list_notes(session_id: str, dm_name: str) -> list[dict]:
    """Return all notes for a prospect, newest first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, content, created_at FROM crm_notes "
            "WHERE session_id = ? AND dm_name = ? ORDER BY created_at DESC",
            (session_id, dm_name),
        ).fetchall()
    return [dict(r) for r in rows]


def add_note(session_id: str, dm_name: str, content: str) -> dict:
    """Add a note to a prospect. Returns the created note."""
    note_id = f"note_{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO crm_notes (id, session_id, dm_name, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (note_id, session_id, dm_name, content, now),
        )
        conn.commit()
    return {"id": note_id, "content": content, "created_at": now}


def delete_note(note_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM crm_notes WHERE id = ?", (note_id,))
        conn.commit()
    return cur.rowcount > 0


def bulk_notes(session_id: str) -> dict[str, list[dict]]:
    """Return all notes for every prospect in a session, keyed by dm_name."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, dm_name, content, created_at FROM crm_notes "
            "WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
    out: dict[str, list[dict]] = {}
    for r in rows:
        d = dict(r)
        name = d.pop("dm_name")
        out.setdefault(name, []).append(d)
    return out


def all_notes() -> dict[str, dict[str, list[dict]]]:
    """Return all notes keyed by session_id -> dm_name -> [notes].
    Used by the CRM list endpoint to batch-load everything."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, session_id, dm_name, content, created_at "
            "FROM crm_notes ORDER BY created_at DESC"
        ).fetchall()
    out: dict[str, dict[str, list[dict]]] = {}
    for r in rows:
        d = dict(r)
        sid = d.pop("session_id")
        name = d.pop("dm_name")
        out.setdefault(sid, {}).setdefault(name, []).append(d)
    return out


# ---------- Stage overrides ----------


def set_stage(session_id: str, dm_name: str, stage: str) -> dict:
    """Set a manual stage override for a prospect."""
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO crm_stages (session_id, dm_name, stage, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(session_id, dm_name) DO UPDATE SET stage = ?, updated_at = ?",
            (session_id, dm_name, stage, now, stage, now),
        )
        conn.commit()
    return {"session_id": session_id, "dm_name": dm_name, "stage": stage, "updated_at": now}


def get_stage(session_id: str, dm_name: str) -> Optional[str]:
    """Return the manual stage override, or None if not set."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT stage FROM crm_stages WHERE session_id = ? AND dm_name = ?",
            (session_id, dm_name),
        ).fetchone()
    return row["stage"] if row else None


def all_stage_overrides() -> dict[str, dict[str, str]]:
    """Return all overrides keyed by session_id -> dm_name -> stage."""
    with _conn() as conn:
        rows = conn.execute("SELECT session_id, dm_name, stage FROM crm_stages").fetchall()
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        out.setdefault(r["session_id"], {})[r["dm_name"]] = r["stage"]
    return out
