"""Governance persistence — SQLite-backed CRUD for company info and ICPs.

Scoped per-user via user_email. Each user has their own company info and ICPs.
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
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                domain TEXT NOT NULL DEFAULT '',
                industry TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                team_size TEXT NOT NULL DEFAULT '',
                meeting_link TEXT NOT NULL DEFAULT '',
                user_email TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS governance_icps (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                user_email TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.commit()
        # Migration: add user_email if missing + handle old schema
        for table in ("governance_company", "governance_icps"):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN user_email TEXT NOT NULL DEFAULT ''")
                conn.commit()
            except Exception:
                pass
        # Migrate old singleton row (id=1) — change its id to the user_email key
        # but keep it accessible as fallback


_ensure_tables()


def _company_id(user_email: str) -> str:
    """Generate a stable company row ID per user."""
    return f"gov_{user_email}" if user_email else "gov_default"


# ---------- Company ----------


def get_company(user_email: str = "") -> dict:
    cid = _company_id(user_email)
    with _conn() as conn:
        row = conn.execute("SELECT * FROM governance_company WHERE id = ?", (cid,)).fetchone()
    if not row:
        # Fallback: try old singleton (id=1) for backward compat
        if user_email:
            with _conn() as conn:
                row = conn.execute("SELECT * FROM governance_company WHERE id = '1'").fetchone()
        if not row:
            return {"name": "", "domain": "", "industry": "", "description": "", "team_size": "", "meeting_link": ""}
    d = dict(row)
    d.pop("id", None)
    d.pop("user_email", None)
    return d


def save_company(data: dict, user_email: str = "") -> dict:
    cid = _company_id(user_email)
    fields = ["name", "domain", "industry", "description", "team_size", "meeting_link"]

    with _conn() as conn:
        existing = conn.execute("SELECT id FROM governance_company WHERE id = ?", (cid,)).fetchone()
        if existing:
            updates = []
            params = []
            for f in fields:
                if f in data:
                    updates.append(f"{f} = ?")
                    params.append(str(data[f]))
            if updates:
                params.append(cid)
                conn.execute(f"UPDATE governance_company SET {', '.join(updates)} WHERE id = ?", params)
        else:
            conn.execute(
                "INSERT INTO governance_company (id, name, domain, industry, description, team_size, meeting_link, user_email) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    cid,
                    str(data.get("name", "")),
                    str(data.get("domain", "")),
                    str(data.get("industry", "")),
                    str(data.get("description", "")),
                    str(data.get("team_size", "")),
                    str(data.get("meeting_link", "")),
                    user_email,
                ),
            )
        conn.commit()
    return get_company(user_email=user_email)


# ---------- ICPs ----------


def list_icps(user_email: str = "") -> list[dict]:
    with _conn() as conn:
        if user_email:
            rows = conn.execute(
                "SELECT * FROM governance_icps WHERE user_email = ? ORDER BY created_at DESC",
                (user_email,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM governance_icps ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def create_icp(name: str, description: str = "", user_email: str = "") -> dict:
    icp_id = f"icp_{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO governance_icps (id, name, description, created_at, user_email) VALUES (?, ?, ?, ?, ?)",
            (icp_id, name, description, now, user_email),
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
