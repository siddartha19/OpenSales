"""User persistence — SQLite-backed CRUD for user accounts.

Supports signup, login validation, and listing all users for the admin panel.
Seeds a default admin user (hr@alerahq.com) on first run.
"""
from __future__ import annotations

import hashlib
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import DB_PATH

# All user timestamps are recorded in IST so the admin panel renders the
# right wall-clock time regardless of where the server runs.
_IST = timezone(timedelta(hours=5, minutes=30))


def _now_ist_iso() -> str:
    """Current time as ISO-8601 with explicit +05:30 offset."""
    return datetime.now(_IST).isoformat(timespec="seconds")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str) -> str:
    """Simple SHA-256 hash for password storage."""
    return hashlib.sha256(password.encode()).hexdigest()


def _ensure_table() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                email       TEXT NOT NULL UNIQUE,
                password    TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'user',
                created_at  TEXT NOT NULL
            )
        """)
        conn.commit()

    # Seed the default admin user if no users exist
    _seed_default_admin()


def _seed_default_admin() -> None:
    """Ensure hr@alerahq.com exists as the default admin user."""
    with _conn() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("hr@alerahq.com",)
        ).fetchone()
        if not existing:
            conn.execute(
                """INSERT INTO users (id, name, email, password, role, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    f"usr_{uuid.uuid4().hex[:10]}",
                    "Admin",
                    "hr@alerahq.com",
                    _hash_password("Admin@123"),
                    "admin",
                    _now_ist_iso(),
                ),
            )
            conn.commit()


_ensure_table()


def signup(name: str, email: str, password: str) -> dict | None:
    """Create a new user. Returns user dict or None if email already taken."""
    user_id = f"usr_{uuid.uuid4().hex[:10]}"
    now = _now_ist_iso()
    hashed = _hash_password(password)

    try:
        with _conn() as conn:
            conn.execute(
                """INSERT INTO users (id, name, email, password, role, created_at)
                   VALUES (?, ?, ?, ?, 'user', ?)""",
                (user_id, name, email.lower().strip(), hashed, now),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return None  # email already exists

    return get_user_by_email(email)


def verify_credentials(email: str, password: str) -> dict | None:
    """Check email + password. Returns user dict (without password) or None."""
    hashed = _hash_password(password)
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email.lower().strip(), hashed),
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_user_by_email(email: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
    return _row_to_dict(row) if row else None


def list_users() -> list[dict]:
    """Return all users, newest first (for admin panel)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d.pop("password", None)  # never expose password hash
    return d
