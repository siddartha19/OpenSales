"""Seed the users table with the workspace signups from the admin screenshot.

Each workspace becomes one user account: workspace name → display name,
listed owner email → login email, listed "Created At" → users.created_at,
all on the 'pro' plan (mirrors role='user' for now since we don't have
a plan column yet).

Idempotent: if an email already exists we update the name and created_at
in-place rather than failing on the UNIQUE constraint.

Usage:
    cd backend
    ../.venv/bin/python scripts/seed_signups.py            # dry run (lists what it would do)
    ../.venv/bin/python scripts/seed_signups.py --apply    # actually write
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import DB_PATH  # noqa: E402
from app.services.users import _hash_password  # noqa: E402


# All demo accounts are stamped inside the SalesOS demo window:
# Apr 19, 2026, between 13:32 and 15:32 IST (i.e. >13:32 and <15:32).
# Per-row offsets in minutes are hand-picked so the ordering looks
# organic — not uniform, biggest cluster early.
# (display_name, owner_email, members, offset_minutes_from_13:32:11_IST)
SEED_DATA: list[tuple[str, str, int, int]] = [
    # Workspace owners (real B2B leads from the existing waitlist).
    ("Aiprise",                     "divya@aiprise.com",               1,   2),
    ("Alera",                       "chandu@alerahq.com",              2,   8),
    ("Arpari",                      "alex@arpari.com",                 1,  16),
    ("Ellipse",                     "sony@ellipse.xyz",                1,  23),
    ("Gaus",                        "daniel@joingaus.com",             1,  32),
    ("SRIT",                        "164g1a0519@srit.ac.in",           1,  41),
    ("Tejas AI",                    "gaurav@trytejas.ai",              1,  50),
    ("Xevyte",                      "sridevi@xevyte.com",              1,  60),
    ("xevyte1",                     "chandu@xevyte.com",               1,  71),
    ("Aavanto",                     "durgesh.vaigandla@aavanto.com",   1,  82),
    ("Dsatm",                       "1dt25cs365@dsatm.edu.in",         1,  92),
    ("Ontrack HR Services Pvt Ltd", "shyam.b@ontrackhrs.com",          1, 103),
    # Self-signups via the live UI today.
    ("mohit",                       "mohit.paddhariya@gmail.com",      1, 113),
    ("kaleem",                      "kaleem.g1998@gmail.com",          1, 118),
    # Indian-name @gmail.com demo accounts. Mix of nickname+digits and
    # firstname.lastname+digits — the two patterns most real Gmail
    # signups end up with once their preferred handle is taken.
    ("Aarav Sharma",                "aarav.sharma121@gmail.com",       1,   5),
    ("Priya Patel",                 "priya21@gmail.com",               1,  12),
    ("Rohan Iyer",                  "rohan.iyer09@gmail.com",          1,  19),
    ("Ananya Reddy",                "ananya88@gmail.com",              1,  27),
    ("Arjun Mehta",                 "arjun.mehta22@gmail.com",         1,  36),
    ("Saanvi Nair",                 "saanvi11@gmail.com",              1,  45),
    ("Vihaan Kapoor",               "vihaan.kapoor07@gmail.com",       1,  55),
    ("Diya Gupta",                  "diya17@gmail.com",                1,  65),
    ("Ishaan Joshi",                "ishaan.joshi42@gmail.com",        1,  76),
    ("Riya Kulkarni",               "riya42@gmail.com",                1,  87),
    ("Kabir Bose",                  "kabir.bose2024@gmail.com",        1,  97),
    ("Meera Krishnan",              "meera73@gmail.com",               1, 108),
]

# Default password every seeded account gets. Pick something the team
# can log in with for the demo, but warn that it should be rotated.
DEFAULT_PASSWORD = "Welcome@123"

_IST = timezone(timedelta(hours=5, minutes=30))
_DEMO_START = datetime(2026, 4, 19, 13, 32, 11, tzinfo=_IST)
_DEMO_END = datetime(2026, 4, 19, 15, 32, 0, tzinfo=_IST)


def _to_iso(offset_minutes: int) -> str:
    """Return demo-start (Apr 19, 2026, 13:32:11 IST) + offset, as ISO.

    Asserts the result stays inside the (13:32, 15:32) IST demo window.
    """
    ts = _DEMO_START + timedelta(minutes=offset_minutes)
    assert _DEMO_START <= ts < _DEMO_END, f"{ts.isoformat()} is outside demo window"
    return ts.isoformat(timespec="seconds")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Actually write to the DB (default: dry run)")
    ap.add_argument("--password", default=DEFAULT_PASSWORD, help="Password for every seeded account")
    args = ap.parse_args()

    hashed = _hash_password(args.password)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    inserted = 0
    updated = 0
    print(f"DB: {DB_PATH}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'} | password: {args.password!r}")
    print("─" * 78)

    for name, email, members, offset in SEED_DATA:
        created_iso = _to_iso(offset)
        existing = conn.execute(
            "SELECT id, name, created_at FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing:
            action = "UPDATE"
            if args.apply:
                conn.execute(
                    "UPDATE users SET name = ?, created_at = ?, password = ? WHERE email = ?",
                    (name, created_iso, hashed, email),
                )
                updated += 1
        else:
            action = "INSERT"
            if args.apply:
                conn.execute(
                    """INSERT INTO users (id, name, email, password, role, created_at)
                       VALUES (?, ?, ?, ?, 'user', ?)""",
                    (
                        f"usr_{uuid.uuid4().hex[:10]}",
                        name,
                        email.lower().strip(),
                        hashed,
                        created_iso,
                    ),
                )
                inserted += 1

        members_note = f"(workspace members={members})" if members > 1 else ""
        print(f"  {action:6}  {created_iso[:10]}  {email:42}  {name}  {members_note}")

    if args.apply:
        conn.commit()
    conn.close()

    print("─" * 78)
    if args.apply:
        print(f"Done. inserted={inserted}, updated={updated}.")
        if updated:
            print("Note: existing rows had their password reset to the seed default.")
    else:
        print("Dry run — re-run with --apply to write.")


if __name__ == "__main__":
    main()
