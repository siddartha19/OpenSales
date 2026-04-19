"""End-to-end smoke test for the SalesOS pipeline.

Drives a real backend (defaults to http://127.0.0.1:8000) through every
phase a user goes through in the UI:

  1. /api/health                    — backend reachable + integrations configured
  2. /api/sessions (POST)           — create a fresh campaign session
  3. /api/campaign/start            — VP routes to SDR, returns prospects
  4. /api/campaign/draft (SSE)      — AE drafts personalized emails
  5. /api/campaign/send             — SendGrid relays emails (returns 202)
  6. /api/diagnostics/sendgrid/lookup
                                    — confirms ACTUAL delivery status for
                                      every X-Message-Id, with retries
                                      (SendGrid Activity API is eventually
                                       consistent — 5-30s lag)

Each step prints PASS / FAIL with timing + a one-line reason. Exits non-zero
if any required step fails — safe to wire into CI later.

USAGE:
    cd backend
    ../.venv/bin/python scripts/e2e_test.py
    ../.venv/bin/python scripts/e2e_test.py --icp "..." --count 4
    ../.venv/bin/python scripts/e2e_test.py --no-send  # dry run, skip phase 5+6
    ../.venv/bin/python scripts/e2e_test.py --backend http://127.0.0.1:8000

Why this exists: the dashboard "Sent (N)" pill counts SendGrid 202s, which
reflect API acceptance, not delivery. This test resolves every X-Message-Id
back to its real `delivered` / `not_delivered` status, so a green run means
emails ACTUALLY landed (or you know exactly which made-up addresses bounced).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_BACKEND = "http://127.0.0.1:8000"
DEFAULT_ICP = (
    "SF AI startup founders, Series A or earlier, building AI SaaS, "
    "raised in 2024 or 2025."
)


# ── ANSI helpers (no extra deps) ──────────────────────────────────

def _c(code: str, s: str) -> str:
    return f"\x1b[{code}m{s}\x1b[0m"


GREEN = lambda s: _c("32", s)
RED = lambda s: _c("31", s)
YEL = lambda s: _c("33", s)
DIM = lambda s: _c("2", s)
BOLD = lambda s: _c("1", s)


@dataclass
class StepResult:
    name: str
    ok: bool
    duration_ms: int
    detail: str = ""
    data: Any = None


@dataclass
class Report:
    steps: list[StepResult] = field(default_factory=list)

    def add(self, step: StepResult) -> None:
        self.steps.append(step)
        tag = GREEN("PASS") if step.ok else RED("FAIL")
        ms = f"{step.duration_ms}ms".rjust(7)
        print(f"  {tag} {ms}  {step.name}  {DIM(step.detail)}")

    @property
    def all_ok(self) -> bool:
        return all(s.ok for s in self.steps)


# ── Helpers ───────────────────────────────────────────────────────


async def _timed(name: str, coro, report: Report, fail_fast: bool = False) -> StepResult:
    t0 = time.time()
    try:
        ok, detail, data = await coro
    except Exception as e:
        ok, detail, data = False, f"exception: {e}", None
    sr = StepResult(
        name=name,
        ok=ok,
        duration_ms=int((time.time() - t0) * 1000),
        detail=detail,
        data=data,
    )
    report.add(sr)
    if fail_fast and not ok:
        print(RED(f"\nABORTING — required step failed: {name}\n"))
        _print_summary(report)
        sys.exit(2)
    return sr


# ── Steps ─────────────────────────────────────────────────────────


async def step_health(client: httpx.AsyncClient, backend: str):
    r = await client.get(f"{backend}/api/health")
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}", None
    j = r.json()
    missing = [
        k for k, v in j.items()
        if k in ("sendgrid", "openrouter", "exa", "crustdata") and v is False
    ]
    detail = f"sendgrid={j.get('sendgrid')} openrouter={j.get('openrouter')} exa={j.get('exa')} model={j.get('model')}"
    if missing:
        detail += f"  ⚠ missing: {','.join(missing)}"
    return True, detail, j


async def step_create_session(client: httpx.AsyncClient, backend: str, name: str):
    r = await client.post(f"{backend}/api/sessions", json={"name": name})
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:120]}", None
    sess = r.json().get("session") or {}
    sid = sess.get("session_id")
    if not sid:
        return False, "no session_id in response", None
    return True, f"session_id={sid}", sess


async def step_source(client: httpx.AsyncClient, backend: str, icp: str, count: int, session_id: str):
    r = await client.post(
        f"{backend}/api/campaign/start",
        json={"icp": icp, "target_count": count, "session_id": session_id},
        timeout=180.0,  # SDR + LLM can be slow
    )
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:120]}", None
    j = r.json()
    prospects = j.get("prospects") or []
    if not prospects:
        return False, f"SDR returned 0 prospects ({j.get('error') or 'no error'})", j
    return True, f"got {len(prospects)} prospects, run_id={j.get('run_id')}", j


async def step_draft(client: httpx.AsyncClient, backend: str, run_id: str, prospects: list, session_id: str):
    """POST /api/campaign/draft is SSE — read the stream until 'all_done'."""
    drafts: list[dict] = []
    errors: list[str] = []

    async with client.stream(
        "POST",
        f"{backend}/api/campaign/draft",
        json={"run_id": run_id, "prospects": prospects, "session_id": session_id},
        timeout=300.0,
    ) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            return False, f"HTTP {resp.status_code}: {body[:120]!r}", None

        buffer = ""
        async for chunk in resp.aiter_text():
            buffer += chunk
            while "\n\n" in buffer:
                event, buffer = buffer.split("\n\n", 1)
                for line in event.splitlines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if not data_str:
                        continue
                    try:
                        evt = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    step = evt.get("step")
                    if step == "draft_complete" and evt.get("draft"):
                        drafts.append(evt["draft"])
                    elif step == "draft_error":
                        errors.append(f"{evt.get('prospect')}: {evt.get('error')}")
                    elif step == "all_done":
                        # Server's authoritative final list (preferred over
                        # the streamed-in-pieces accumulator).
                        if evt.get("drafts"):
                            drafts = evt["drafts"]

    if not drafts:
        return False, f"AE produced 0 drafts; errors={errors[:3]}", None
    sample = drafts[0]
    detail = f"got {len(drafts)} drafts (sample → {sample.get('to_email')})"
    if errors:
        detail += f"  ⚠ {len(errors)} errors"
    return True, detail, drafts


async def step_send(client: httpx.AsyncClient, backend: str, run_id: str, drafts: list, session_id: str):
    r = await client.post(
        f"{backend}/api/campaign/send",
        json={"run_id": run_id, "drafts": drafts, "session_id": session_id},
        timeout=120.0,
    )
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:120]}", None
    j = r.json()
    sent = j.get("sent") or []
    if not sent:
        return False, "no send results returned", j
    successes = sum(1 for s in sent if s.get("success"))
    msg_ids = [s.get("message_id") for s in sent if s.get("message_id")]
    return (
        successes == len(sent),
        f"SendGrid 2xx: {successes}/{len(sent)}; message_ids={len(msg_ids)}",
        {"sent": sent, "message_ids": msg_ids},
    )


async def step_verify_delivery(
    client: httpx.AsyncClient,
    backend: str,
    message_ids: list[str],
    max_wait_s: int = 60,
):
    """Poll the diagnostics endpoint until every message has a real status.

    SendGrid Activity API is eventually consistent — usually 5-30 seconds
    after the 202. We retry up to max_wait_s and report the verdict.
    """
    if not message_ids:
        return False, "no message_ids to verify", None

    deadline = time.time() + max_wait_s
    last_results: dict[str, dict] = {}
    while time.time() < deadline:
        r = await client.post(
            f"{backend}/api/diagnostics/sendgrid/lookup",
            json={"message_ids": message_ids},
            timeout=20.0,
        )
        if r.status_code != 200:
            return False, f"diagnostics HTTP {r.status_code}", None
        j = r.json()
        last_results = j.get("results", {})
        if len(last_results) == len(message_ids):
            break
        await asyncio.sleep(3)

    delivered = sum(1 for v in last_results.values() if v.get("status") == "delivered")
    not_delivered = sum(1 for v in last_results.values() if v.get("status") == "not_delivered")
    pending = len(message_ids) - len(last_results)

    detail_lines = []
    for mid in message_ids:
        row = last_results.get(mid)
        if row is None:
            detail_lines.append(f"  {YEL('PENDING')}  {mid}  (Activity API hasn't seen it yet)")
        else:
            status = row.get("status", "?")
            tag = GREEN(status) if status == "delivered" else RED(status)
            detail_lines.append(f"  {tag}  {row.get('to_email','?')}  ({mid})")

    print("\n  " + DIM("delivery breakdown:"))
    for line in detail_lines:
        print("  " + line)

    detail = f"delivered={delivered}, not_delivered={not_delivered}, pending={pending}"
    # PASS only if at least one delivered AND none in hard-fail.
    ok = delivered > 0 and not_delivered == 0 and pending == 0
    return ok, detail, last_results


# ── Output ────────────────────────────────────────────────────────


def _print_summary(report: Report) -> None:
    print()
    print(BOLD("━" * 60))
    passed = sum(1 for s in report.steps if s.ok)
    total = len(report.steps)
    label = GREEN(f"{passed}/{total} PASS") if report.all_ok else RED(f"{passed}/{total} PASS")
    print(f"  E2E summary: {label}")
    print(BOLD("━" * 60))


# ── Main ─────────────────────────────────────────────────────────


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", default=DEFAULT_BACKEND, help="Backend URL")
    ap.add_argument("--icp", default=DEFAULT_ICP, help="ICP query for SDR")
    ap.add_argument("--count", type=int, default=4, help="Target prospect count (also: how many to draft)")
    ap.add_argument("--no-send", action="store_true", help="Skip phase 5+6 (don't actually email)")
    ap.add_argument("--max-drafts", type=int, default=2, help="Cap drafts for the send step (saves credits)")
    ap.add_argument(
        "--verify-wait",
        type=int,
        default=60,
        help="Max seconds to poll SendGrid Activity for delivery confirmation",
    )
    args = ap.parse_args()

    print(BOLD(f"\nSalesOS E2E test → {args.backend}"))
    print(DIM(f"ICP: {args.icp}"))
    print(DIM(f"target_count={args.count}  no-send={args.no_send}  max_drafts={args.max_drafts}\n"))

    report = Report()
    async with httpx.AsyncClient() as client:
        # 1. Health
        await _timed("health", step_health(client, args.backend), report, fail_fast=True)

        # 2. Session
        sess_step = await _timed(
            "create session",
            step_create_session(
                client, args.backend, name=f"e2e-{int(time.time())}"
            ),
            report,
            fail_fast=True,
        )
        sess = sess_step.data
        sid = sess["session_id"]

        # 3. Sourcing
        src_step = await _timed(
            "source prospects",
            step_source(client, args.backend, args.icp, args.count, sid),
            report,
            fail_fast=True,
        )
        run_id = src_step.data["run_id"]
        prospects = src_step.data["prospects"]

        # 4. Drafting (cap to max_drafts so send step doesn't burn credits)
        prospects_to_draft = prospects[: args.max_drafts]
        draft_step = await _timed(
            f"draft {len(prospects_to_draft)} email(s) (SSE)",
            step_draft(client, args.backend, run_id, prospects_to_draft, sid),
            report,
            fail_fast=True,
        )
        drafts = draft_step.data

        if args.no_send:
            print(YEL("\n  --no-send specified, skipping phase 5+6.\n"))
            _print_summary(report)
            sys.exit(0 if report.all_ok else 1)

        # 5. Sending
        send_step = await _timed(
            f"send {len(drafts)} via SendGrid",
            step_send(client, args.backend, run_id, drafts, sid),
            report,
        )
        if not send_step.ok or not send_step.data:
            _print_summary(report)
            sys.exit(1)

        msg_ids = send_step.data["message_ids"]

        # 6. Verify actual delivery via Activity API
        await _timed(
            f"verify delivery (poll up to {args.verify_wait}s)",
            step_verify_delivery(client, args.backend, msg_ids, args.verify_wait),
            report,
        )

    _print_summary(report)
    sys.exit(0 if report.all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
