"""Governance persistence — SQLite-backed CRUD for company info and ICPs.

Simple key-value store for company info + ICP list.
"""
from __future__ import annotations

import json
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
            CREATE TABLE IF NOT EXISTS governance_company (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL DEFAULT '',
                domain TEXT NOT NULL DEFAULT '',
                industry TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                team_size TEXT NOT NULL DEFAULT '',
                meeting_link TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS governance_icps (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        # Ensure the singleton company row exists
        existing = conn.execute("SELECT id FROM governance_company WHERE id = 1").fetchone()
        if not existing:
            conn.execute("INSERT INTO governance_company (id) VALUES (1)")
        conn.commit()


_ensure_tables()


# ---------- Company ----------


def get_company() -> dict:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM governance_company WHERE id = 1").fetchone()
    if not row:
        return {"name": "", "domain": "", "industry": "", "description": "", "team_size": "", "meeting_link": ""}
    return dict(row)


def save_company(data: dict) -> dict:
    fields = ["name", "domain", "industry", "description", "team_size", "meeting_link"]
    updates = []
    params = []
    for f in fields:
        if f in data:
            updates.append(f"{f} = ?")
            params.append(str(data[f]))
    if not updates:
        return get_company()
    with _conn() as conn:
        conn.execute(f"UPDATE governance_company SET {', '.join(updates)} WHERE id = 1", params)
        conn.commit()
    return get_company()


# ---------- ICPs ----------


def list_icps() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM governance_icps ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def create_icp(name: str, description: str = "") -> dict:
    icp_id = f"icp_{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO governance_icps (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (icp_id, name, description, now),
        )
        conn.commit()
    return {"id": icp_id, "name": name, "description": description, "created_at": now}


def update_icp(icp_id: str, name: Optional[str] = None, description: Optional[str] = None) -> Optional[dict]:
    updates = []
    params = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if not updates:
        return get_icp(icp_id)
    params.append(icp_id)
    with _conn() as conn:
        conn.execute(f"UPDATE governance_icps SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    return get_icp(icp_id)


def get_icp(icp_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM governance_icps WHERE id = ?", (icp_id,)).fetchone()
    return dict(row) if row else None


def delete_icp(icp_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM governance_icps WHERE id = ?", (icp_id,))
        conn.commit()
    return cur.rowcount > 0
