"""Company profile + ICP persistence — SQLite-backed.

Stores:
  1. Company profile (singleton) — the owner's company info, scraped once.
  2. ICP definitions (max 3) — saved ideal customer profiles the owner can
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
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS icp_definitions (
                id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


_ensure_tables()


# ---------- Company Profile (singleton) ----------


def save_company_profile(data: dict) -> dict:
    """Upsert the company profile. Only one row with id='default'."""
    now = datetime.utcnow().isoformat()
    data_json = json.dumps(data, default=str)

    with _conn() as conn:
        existing = conn.execute(
            "SELECT id FROM company_profile WHERE id = 'default'"
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE company_profile SET data_json = ?, updated_at = ? WHERE id = 'default'",
                (data_json, now),
            )
        else:
            conn.execute(
                "INSERT INTO company_profile (id, data_json, created_at, updated_at) VALUES ('default', ?, ?, ?)",
                (data_json, now, now),
            )
        conn.commit()

    return get_company_profile()


def get_company_profile() -> Optional[dict]:
    """Return the company profile, or None if not set up yet."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT data_json, created_at, updated_at FROM company_profile WHERE id = 'default'"
        ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row["data_json"])
        data["created_at"] = row["created_at"]
        data["updated_at"] = row["updated_at"]
        return data
    except Exception:
        return None


def delete_company_profile() -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM company_profile WHERE id = 'default'")
        conn.commit()
    return cur.rowcount > 0


# ---------- ICP Definitions (max 3) ----------


def list_icps() -> list[dict]:
    """Return all ICPs, newest first."""
    with _conn() as conn:
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


def create_icp(data: dict) -> Optional[dict]:
    """Create a new ICP definition. Returns None if max 3 already exist."""
    existing = list_icps()
    if len(existing) >= MAX_ICPS:
        return None  # caller should return 400

    icp_id = f"icp_{uuid.uuid4().hex[:10]}"
    now = datetime.utcnow().isoformat()
    data_json = json.dumps(data, default=str)

    with _conn() as conn:
        conn.execute(
            "INSERT INTO icp_definitions (id, data_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (icp_id, data_json, now, now),
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
