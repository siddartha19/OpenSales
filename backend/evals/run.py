"""Eval runner — 10 cold-email quality cases.

For each case:
  1. Build a synthetic ProspectDossier + LinkedIn data.
  2. Call the AE drafting flow (LLM with structured output).
  3. Use Gemini-as-judge to check must-includes and anti-patterns.

Output: backend/evals/last_run.json (also surfaced via /api/evals).

Run: cd backend && ../.venv/bin/python evals/run.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.agent import _DraftSchema, AE_DRAFT_SYSTEM, make_llm  # noqa: E402
from app.config import SENDGRID_FROM_NAME  # noqa: E402
from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

EVAL_PATH = Path(__file__).parent / "cold_email_quality.json"
OUT_PATH = Path(__file__).parent / "last_run.json"


JUDGE_SYSTEM = """You are a strict judge of cold email quality.

You will receive a draft email + a list of must-includes + a list of anti-patterns.
Return JSON: {pass: bool, must_include_results: [bool...], anti_patterns_found: [str...], notes: str}

PASS = ALL must-includes satisfied AND ZERO anti-patterns triggered.
"""


class _JudgeSchema:
    pass  # placeholder; we'll use dict structured output via Pydantic below


from pydantic import BaseModel, Field


class JudgeResult(BaseModel):
    passed: bool = Field(..., description="True only if ALL must_include satisfied AND ZERO anti_patterns triggered.")
    must_include_results: list[bool]
    anti_patterns_found: list[str]
    notes: str = ""


async def draft_for_case(case: dict, from_name: str) -> dict:
    """Run the AE drafting flow on a synthetic case, no network for Apify/Exa."""
    p = case["prospect"]
    brief = json.dumps(
        {
            "prospect_name": p["name"],
            "title": p["title"],
            "company": p["company"],
            "why_target": case.get("icp", ""),
            "linkedin_about": p.get("linkedin_about", ""),
            "linkedin_recent_posts": p.get("recent_posts", []),
            "web_recent_activity": p.get("web_recent_activity", []),
            "linkedin_source": "synthetic_eval",
        }
    )
    llm = make_llm(temperature=0.5, max_tokens=600).with_structured_output(_DraftSchema)
    out = await llm.ainvoke(
        [
            SystemMessage(content=AE_DRAFT_SYSTEM.format(from_name=from_name)),
            HumanMessage(content=f"Write the cold email. Brief:\n{brief}\n\nReturn: subject, body, personalization_hooks."),
        ]
    )
    return {
        "subject": out.subject,
        "body": out.body,
        "personalization_hooks": list(out.personalization_hooks or []),
    }


async def judge_case(case: dict, draft: dict) -> JudgeResult:
    judge = make_llm(temperature=0.0, max_tokens=600).with_structured_output(JudgeResult)
    payload = json.dumps(
        {
            "subject": draft["subject"],
            "body": draft["body"],
            "must_include": case.get("must_include", []),
            "anti_patterns": case.get("anti_patterns", []),
        }
    )
    res = await judge.ainvoke(
        [
            SystemMessage(content=JUDGE_SYSTEM),
            HumanMessage(content=payload),
        ]
    )
    return res


async def main():
    cases = json.loads(EVAL_PATH.read_text())["cases"]
    from_name = SENDGRID_FROM_NAME or "Alera Founder"

    started = time.time()
    results = []
    for case in cases:
        t0 = time.time()
        try:
            draft = await draft_for_case(case, from_name)
        except Exception as e:
            results.append(
                {
                    "id": case["id"],
                    "ok": False,
                    "error": f"draft error: {e}",
                    "duration_ms": int((time.time() - t0) * 1000),
                }
            )
            continue

        try:
            judge = await judge_case(case, draft)
        except Exception as e:
            results.append(
                {
                    "id": case["id"],
                    "ok": False,
                    "draft": draft,
                    "error": f"judge error: {e}",
                    "duration_ms": int((time.time() - t0) * 1000),
                }
            )
            continue

        results.append(
            {
                "id": case["id"],
                "ok": True,
                "passed": judge.passed,
                "draft": draft,
                "must_include_results": judge.must_include_results,
                "anti_patterns_found": judge.anti_patterns_found,
                "notes": judge.notes,
                "duration_ms": int((time.time() - t0) * 1000),
            }
        )
        status = "PASS" if judge.passed else "FAIL"
        print(f"[{status}] {case['id']:50s} {results[-1]['duration_ms']}ms")

    passed = sum(1 for r in results if r.get("passed"))
    out = {
        "eval_set": "cold_email_quality_v1",
        "model": make_llm().model_name,
        "total": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "pass_rate": round(passed / max(len(cases), 1), 3),
        "duration_s": round(time.time() - started, 2),
        "results": results,
        "timestamp": time.time(),
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n=== {passed}/{len(cases)} pass — {out['pass_rate']*100:.0f}% ===")
    print(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
