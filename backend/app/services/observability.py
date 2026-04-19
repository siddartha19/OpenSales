"""SQLite-backed observability.

One table: agent_runs. Captures every agent step + tool call with parent linkage,
tokens, cost, duration. The trace UI reads this directly.

LangChain callback handler logs LLM calls and tool calls automatically.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage

from ..config import DB_PATH, LLM_MODEL


# --- pricing (per 1M tokens, USD) ---
# Gemini 2.0 Flash via OpenRouter: $0.10 in / $0.40 out
PRICING_PER_1M = {
    "google/gemini-2.0-flash-001": (0.10, 0.40),
    "google/gemini-flash-1.5": (0.075, 0.30),
    "anthropic/claude-3.5-haiku": (0.80, 4.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
}


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    in_rate, out_rate = PRICING_PER_1M.get(model, (0.10, 0.40))
    return (tokens_in / 1_000_000.0) * in_rate + (tokens_out / 1_000_000.0) * out_rate


# --- schema ---

DDL = """
CREATE TABLE IF NOT EXISTS agent_runs (
  id TEXT PRIMARY KEY,
  run_id TEXT,
  parent_run_id TEXT,
  trace_id TEXT,
  agent_name TEXT,
  tool_name TEXT,
  event_type TEXT,
  input TEXT,
  output TEXT,
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  cost_usd REAL DEFAULT 0,
  duration_ms INTEGER DEFAULT 0,
  status TEXT DEFAULT 'success',
  started_at TEXT,
  ended_at TEXT,
  metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_trace ON agent_runs(trace_id, started_at);
CREATE INDEX IF NOT EXISTS idx_parent ON agent_runs(parent_run_id);
CREATE INDEX IF NOT EXISTS idx_started ON agent_runs(started_at DESC);
"""


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(DDL)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def log_event(
    *,
    trace_id: str,
    parent_run_id: str | None = None,
    agent_name: str | None = None,
    tool_name: str | None = None,
    event_type: str = "tool",  # 'llm', 'tool', 'agent', 'note'
    input: Any = None,
    output: Any = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    duration_ms: int = 0,
    status: str = "success",
    metadata: dict | None = None,
) -> str:
    init_db()
    rid = uuid.uuid4().hex
    now = datetime.utcnow().isoformat()
    started = (datetime.utcnow().timestamp() - duration_ms / 1000.0)
    started_iso = datetime.utcfromtimestamp(started).isoformat()
    with _conn() as c:
        c.execute(
            """INSERT INTO agent_runs
               (id, run_id, parent_run_id, trace_id, agent_name, tool_name, event_type,
                input, output, tokens_in, tokens_out, cost_usd, duration_ms,
                status, started_at, ended_at, metadata)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rid,
                rid,
                parent_run_id,
                trace_id,
                agent_name,
                tool_name,
                event_type,
                _json(input),
                _json(output),
                tokens_in,
                tokens_out,
                cost_usd,
                duration_ms,
                status,
                started_iso,
                now,
                _json(metadata),
            ),
        )
    return rid


def _json(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, default=str)[:8000]
    except Exception:
        return str(v)[:8000]


def fetch_trace(trace_id: str) -> list[dict]:
    init_db()
    with _conn() as c:
        cur = c.execute(
            "SELECT id, parent_run_id, trace_id, agent_name, tool_name, event_type, "
            "input, output, tokens_in, tokens_out, cost_usd, duration_ms, status, "
            "started_at, ended_at, metadata "
            "FROM agent_runs WHERE trace_id = ? ORDER BY started_at, id",
            (trace_id,),
        )
        rows = cur.fetchall()
    cols = [
        "id",
        "parent_run_id",
        "trace_id",
        "agent_name",
        "tool_name",
        "event_type",
        "input",
        "output",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "duration_ms",
        "status",
        "started_at",
        "ended_at",
        "metadata",
    ]
    return [dict(zip(cols, r)) for r in rows]


def trace_summary(trace_id: str) -> dict:
    rows = fetch_trace(trace_id)
    return {
        "trace_id": trace_id,
        "step_count": len(rows),
        "total_tokens_in": sum(r["tokens_in"] for r in rows),
        "total_tokens_out": sum(r["tokens_out"] for r in rows),
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 4),
        "total_duration_ms": sum(r["duration_ms"] for r in rows),
        "by_agent": _group_by(rows, "agent_name"),
        "by_tool": _group_by(rows, "tool_name"),
    }


def _group_by(rows: list[dict], key: str) -> dict:
    out: dict[str, dict] = {}
    for r in rows:
        k = r.get(key) or "unknown"
        if k not in out:
            out[k] = {"count": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
        out[k]["count"] += 1
        out[k]["tokens_in"] += r["tokens_in"]
        out[k]["tokens_out"] += r["tokens_out"]
        out[k]["cost_usd"] += r["cost_usd"]
    for v in out.values():
        v["cost_usd"] = round(v["cost_usd"], 5)
    return out


def list_recent_traces(limit: int = 20) -> list[dict]:
    init_db()
    with _conn() as c:
        cur = c.execute(
            """SELECT trace_id,
                      MIN(started_at) AS started_at,
                      MAX(ended_at)   AS ended_at,
                      COUNT(*)        AS steps,
                      SUM(cost_usd)   AS cost
                 FROM agent_runs
                WHERE trace_id IS NOT NULL
                GROUP BY trace_id
                ORDER BY started_at DESC
                LIMIT ?""",
            (limit,),
        )
        return [
            {
                "trace_id": tid,
                "started_at": s,
                "ended_at": e,
                "steps": steps,
                "cost_usd": round(cost or 0, 5),
            }
            for tid, s, e, steps, cost in cur.fetchall()
        ]


# --- LangChain callback handler ---


class TraceCallback(BaseCallbackHandler):
    """Auto-logs LLM and tool events into agent_runs."""

    def __init__(self, trace_id: str, agent_label: str | None = None):
        self.trace_id = trace_id
        self.agent_label = agent_label
        self._starts: dict[str, float] = {}
        self._inputs: dict[str, str] = {}
        self._tool_names: dict[str, str] = {}
        self._llm_models: dict[str, str] = {}

    # --- LLM events ---
    def on_chat_model_start(
        self,
        serialized: dict,
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        self._starts[rid] = time.time()
        self._inputs[rid] = _summarize_messages(messages)
        model = (
            (serialized.get("kwargs") or {}).get("model")
            or (serialized.get("kwargs") or {}).get("model_name")
            or LLM_MODEL
        )
        self._llm_models[rid] = model

    def on_llm_end(self, response, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> None:
        rid = str(run_id)
        start = self._starts.pop(rid, time.time())
        duration_ms = int((time.time() - start) * 1000)
        usage = {}
        try:
            llm_output = getattr(response, "llm_output", None) or {}
            usage = llm_output.get("token_usage") or llm_output.get("usage") or {}
            if not usage:
                gens = getattr(response, "generations", []) or []
                if gens and gens[0]:
                    msg = getattr(gens[0][0], "message", None)
                    if msg is not None:
                        meta = getattr(msg, "usage_metadata", None) or {}
                        usage = {
                            "prompt_tokens": meta.get("input_tokens", 0),
                            "completion_tokens": meta.get("output_tokens", 0),
                        }
        except Exception:
            pass

        tin = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        tout = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        model = self._llm_models.pop(rid, LLM_MODEL)
        cost = estimate_cost(model, tin, tout)

        out = ""
        try:
            gens = getattr(response, "generations", [])
            if gens and gens[0]:
                txt = getattr(gens[0][0], "text", "") or ""
                out = txt[:2000]
        except Exception:
            pass

        log_event(
            trace_id=self.trace_id,
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            agent_name=self.agent_label or "llm",
            tool_name=model,
            event_type="llm",
            input=self._inputs.pop(rid, ""),
            output=out,
            tokens_in=tin,
            tokens_out=tout,
            cost_usd=cost,
            duration_ms=duration_ms,
        )

    # --- Tool events ---
    def on_tool_start(
        self,
        serialized: dict,
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        self._starts[rid] = time.time()
        self._tool_names[rid] = (serialized or {}).get("name") or "tool"
        self._inputs[rid] = input_str[:2000] if isinstance(input_str, str) else _json_str(input_str)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        start = self._starts.pop(rid, time.time())
        duration_ms = int((time.time() - start) * 1000)
        name = self._tool_names.pop(rid, "tool")
        log_event(
            trace_id=self.trace_id,
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            agent_name=self.agent_label,
            tool_name=name,
            event_type="tool",
            input=self._inputs.pop(rid, ""),
            output=_json_str(output)[:2000],
            duration_ms=duration_ms,
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        start = self._starts.pop(rid, time.time())
        duration_ms = int((time.time() - start) * 1000)
        name = self._tool_names.pop(rid, "tool")
        log_event(
            trace_id=self.trace_id,
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            agent_name=self.agent_label,
            tool_name=name,
            event_type="tool",
            input=self._inputs.pop(rid, ""),
            output=f"ERROR: {error}",
            duration_ms=duration_ms,
            status="error",
        )


def _summarize_messages(messages: list[list[BaseMessage]]) -> str:
    out = []
    for batch in messages:
        for m in batch:
            role = type(m).__name__
            content = getattr(m, "content", "")
            if isinstance(content, list):
                content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
            out.append(f"[{role}] {str(content)[:600]}")
    return "\n".join(out)[:4000]


def _json_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, default=str)
    except Exception:
        return str(v)


if __name__ == "__main__":
    init_db()
    tid = "smoke-trace"
    log_event(
        trace_id=tid,
        agent_name="vp",
        event_type="agent",
        input="parse ICP",
        output="planned campaign",
        tokens_in=180,
        tokens_out=50,
        cost_usd=estimate_cost(LLM_MODEL, 180, 50),
        duration_ms=420,
    )
    print(json.dumps(trace_summary(tid), indent=2))
