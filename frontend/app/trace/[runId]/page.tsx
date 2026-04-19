"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Row = {
  id: string;
  parent_run_id: string | null;
  agent_name: string | null;
  tool_name: string | null;
  event_type: string;
  input: string | null;
  output: string | null;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  duration_ms: number;
  status: string;
  started_at: string;
  ended_at: string;
  metadata: string | null;
};

type Summary = {
  trace_id: string;
  step_count: number;
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost_usd: number;
  total_duration_ms: number;
  by_agent: Record<string, any>;
  by_tool: Record<string, any>;
};

const AGENT_COLORS: Record<string, string> = {
  vp: "bg-amber-100 text-amber-900 border-amber-300",
  sdr: "bg-sky-100 text-sky-900 border-sky-300",
  ae: "bg-emerald-100 text-emerald-900 border-emerald-300",
  llm: "bg-stone-100 text-stone-900 border-stone-300",
  unknown: "bg-stone-100 text-stone-900 border-stone-300",
};

export default function TracePage({ params }: { params: { runId: string } }) {
  const [data, setData] = useState<{ summary: Summary; rows: Row[] } | null>(null);
  const [filter, setFilter] = useState<string>("");
  const [openRows, setOpenRows] = useState<Set<string>>(new Set());
  const [autoRefresh, setAutoRefresh] = useState(true);

  async function load() {
    try {
      const r = await fetch(`/api/proxy/trace/${params.runId}`);
      const j = await r.json();
      setData(j);
    } catch {}
  }
  useEffect(() => {
    load();
    if (!autoRefresh) return;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [params.runId, autoRefresh]);

  if (!data) return <Loading />;

  const rows = data.rows.filter(
    (r) =>
      !filter ||
      (r.agent_name || "").toLowerCase().includes(filter.toLowerCase()) ||
      (r.tool_name || "").toLowerCase().includes(filter.toLowerCase())
  );

  function toggle(id: string) {
    const next = new Set(openRows);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setOpenRows(next);
  }

  return (
    <main className="min-h-screen bg-bg">
      <header className="border-b border-border bg-white">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/campaigns" className="btn btn-ghost text-stone-500">← Campaigns</Link>
            <div>
              <div className="font-semibold">Trace</div>
              <div className="text-xs mono text-stone-500">{params.runId}</div>
            </div>
          </div>
          <label className="text-xs flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (1.5s)
          </label>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        <section className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Stat label="Steps" value={data.summary.step_count} />
          <Stat
            label="Tokens"
            value={`${data.summary.total_tokens_in} → ${data.summary.total_tokens_out}`}
          />
          <Stat label="Cost" value={`$${data.summary.total_cost_usd.toFixed(4)}`} />
          <Stat label="Duration" value={`${(data.summary.total_duration_ms / 1000).toFixed(2)}s`} />
          <Stat label="Agents" value={Object.keys(data.summary.by_agent).join(" · ") || "—"} />
        </section>

        <section className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="card">
            <h3 className="font-semibold mb-2">By agent</h3>
            <table className="w-full text-sm">
              <thead className="text-xs text-stone-500 uppercase">
                <tr>
                  <th className="text-left py-1">Agent</th>
                  <th className="text-right">Steps</th>
                  <th className="text-right">Tokens (in→out)</th>
                  <th className="text-right">$</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.summary.by_agent).map(([k, v]: any) => (
                  <tr key={k} className="border-t border-border">
                    <td className="py-1">
                      <span className={`pill border ${AGENT_COLORS[k] || AGENT_COLORS.unknown}`}>{k}</span>
                    </td>
                    <td className="text-right">{v.count}</td>
                    <td className="text-right mono">{v.tokens_in} → {v.tokens_out}</td>
                    <td className="text-right mono">${v.cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card">
            <h3 className="font-semibold mb-2">By tool</h3>
            <table className="w-full text-sm">
              <thead className="text-xs text-stone-500 uppercase">
                <tr>
                  <th className="text-left py-1">Tool / Model</th>
                  <th className="text-right">Calls</th>
                  <th className="text-right">$</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.summary.by_tool).map(([k, v]: any) => (
                  <tr key={k} className="border-t border-border">
                    <td className="py-1 mono text-xs">{k}</td>
                    <td className="text-right">{v.count}</td>
                    <td className="text-right mono">${v.cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card">
          <div className="flex items-baseline justify-between mb-3 gap-3">
            <h3 className="font-semibold">Steps ({rows.length})</h3>
            <input
              className="input max-w-xs"
              placeholder="Filter by agent or tool…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            {rows.length === 0 && <div className="text-sm text-stone-500">No steps yet.</div>}
            {rows.map((r) => {
              const open = openRows.has(r.id);
              const agent = r.agent_name || "unknown";
              const colorClass = AGENT_COLORS[agent] || AGENT_COLORS.unknown;
              return (
                <div key={r.id} className="border border-border rounded-md">
                  <button
                    onClick={() => toggle(r.id)}
                    className="w-full text-left px-3 py-2 flex items-center gap-3 hover:bg-stone-50"
                  >
                    <span className={`pill border ${colorClass}`}>{agent}</span>
                    <span className="text-xs pill">{r.event_type}</span>
                    <span className="font-mono text-xs text-stone-700 flex-1 truncate">
                      {r.tool_name || "—"}
                    </span>
                    <span className="text-xs text-stone-500 mono">
                      {(r.duration_ms / 1000).toFixed(2)}s
                    </span>
                    <span className="text-xs text-stone-500 mono">
                      {r.tokens_in}→{r.tokens_out}
                    </span>
                    <span className="text-xs text-stone-500 mono">
                      ${r.cost_usd.toFixed(5)}
                    </span>
                    {r.status === "error" && (
                      <span className="pill pill-danger">err</span>
                    )}
                    <span className="text-xs text-stone-400">{open ? "▾" : "▸"}</span>
                  </button>
                  {open && (
                    <div className="px-3 pb-3 space-y-2 bg-stone-50">
                      <Block label="Input" text={r.input || ""} />
                      <Block label="Output" text={r.output || ""} />
                      <div className="text-xs text-stone-500">
                        {r.started_at} → {r.ended_at}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className="text-lg font-semibold mt-1">{value}</div>
    </div>
  );
}

function Block({ label, text }: { label: string; text: string }) {
  if (!text) return null;
  return (
    <div>
      <div className="label">{label}</div>
      <pre className="bg-white border border-border rounded-md p-2 mono text-xs whitespace-pre-wrap mt-1 max-h-64 overflow-auto">
        {text}
      </pre>
    </div>
  );
}

function Loading() {
  return (
    <main className="min-h-screen bg-bg flex items-center justify-center text-stone-500">
      Loading trace…
    </main>
  );
}
