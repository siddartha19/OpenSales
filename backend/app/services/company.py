"""Company profile + ICP persistence — SQLite-backed.

Stores:
  1. Company profile — keyed by user_email (each user has their own).
  2. ICP definitions (max 3 per user) — saved ideal customer profiles the owner can
     select from when launching a campaign.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from ..config import DB_PATH

MAX_ICPS = 3


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS company_profile (
                id TEXT PRIMARY KEY DEFAULT 'default',
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                user_email TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS icp_definitions (
                id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                user_email TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.commit()
        # Migration: add user_email if missing
        for table in ("company_profile", "icp_definitions"):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN user_email TEXT NOT NULL DEFAULT ''")
                conn.commit()
            except Exception:
                pass


_ensure_tables()


# ---------- Company Profile (per-user) ----------


def save_company_profile(data: dict, user_email: str = "") -> dict:
    """Upsert the company profile for the given user."""
    profile_id = f"cp_{user_email}" if user_email else "default"
    now = datetime.utcnow().isoformat()
    data_json = json.dumps(data, default=str)

    with _conn() as conn:
        existing = conn.execute(
            "SELECT id FROM company_profile WHERE id = ?", (profile_id,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE company_profile SET data_json = ?, updated_at = ? WHERE id = ?",
                (data_json, now, profile_id),
            )
        else:
            conn.execute(
                "INSERT INTO company_profile (id, data_json, created_at, updated_at, user_email) VALUES (?, ?, ?, ?, ?)",
                (profile_id, data_json, now, now, user_email),
            )
        conn.commit()

    return get_company_profile(user_email=user_email)


def get_company_profile(user_email: str = "") -> Optional[dict]:
    """Return the company profile for the given user, or None if not set up yet."""
    profile_id = f"cp_{user_email}" if user_email else "default"
    with _conn() as conn:
        row = conn.execute(
            "SELECT data_json, created_at, updated_at FROM company_profile WHERE id = ?",
            (profile_id,),
        ).fetchone()
    if not row:
        # Fallback: try the old 'default' profile for backward compat
        if user_email:
            return get_company_profile(user_email="")
        return None
    try:
        data = json.loads(row["data_json"])
        data["created_at"] = row["created_at"]
        data["updated_at"] = row["updated_at"]
        return data
    except Exception:
        return None


def delete_company_profile(user_email: str = "") -> bool:
    profile_id = f"cp_{user_email}" if user_email else "default"
    with _conn() as conn:
        cur = conn.execute("DELETE FROM company_profile WHERE id = ?", (profile_id,))
        conn.commit()
    return cur.rowcount > 0


# ---------- ICP Definitions (max 3 per user) ----------


def list_icps(user_email: str = "") -> list[dict]:
    """Return all ICPs for the given user, newest first."""
    with _conn() as conn:
        if user_email:
            rows = conn.execute(
                "SELECT id, data_json, created_at, updated_at FROM icp_definitions WHERE user_email = ? ORDER BY created_at DESC",
                (user_email,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, data_json, created_at, updated_at FROM icp_definitions ORDER BY created_at DESC"
            ).fetchall()
    result = []
    for row in rows:
        try:
            data = json.loads(row["data_json"])
            data["id"] = row["id"]
            data["created_at"] = row["created_at"]
            data["updated_at"] = row["updated_at"]
            result.append(data)
        except Exception:
            continue
    return result


def get_icp(icp_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, data_json, created_at, updated_at FROM icp_definitions WHERE id = ?",
            (icp_id,),
        ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row["data_json"])
        data["id"] = row["id"]
        data["created_at"] = row["created_at"]
        data["updated_at"] = row["updated_at"]
        return data
    except Exception:
        return None


def create_icp(data: dict, user_email: str = "") -> Optional[dict]:
    """Create a new ICP definition. Returns None if max 3 already exist for this user."""
    existing = list_icps(user_email=user_email)
    if len(existing) >= MAX_ICPS:
        return None  # caller should return 400

    icp_id = f"icp_{uuid.uuid4().hex[:10]}"
    now = datetime.utcnow().isoformat()
    data_json = json.dumps(data, default=str)

    with _conn() as conn:
        conn.execute(
            "INSERT INTO icp_definitions (id, data_json, created_at, updated_at, user_email) VALUES (?, ?, ?, ?, ?)",
            (icp_id, data_json, now, now, user_email),
        )
        conn.commit()

    return get_icp(icp_id)


def update_icp(icp_id: str, data: dict) -> Optional[dict]:
    """Update an existing ICP definition."""
    now = datetime.utcnow().isoformat()
    data_json = json.dumps(data, default=str)

    with _conn() as conn:
        cur = conn.execute(
            "UPDATE icp_definitions SET data_json = ?, updated_at = ? WHERE id = ?",
            (data_json, now, icp_id),
        )
        conn.commit()

    if cur.rowcount == 0:
        return None
    return get_icp(icp_id)


def delete_icp(icp_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM icp_definitions WHERE id = ?", (icp_id,)
        )
        conn.commit()
    return cur.rowcount > 0
