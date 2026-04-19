"use client";

import { useEffect, useState } from "react";
import MetricCard from "@/components/MetricCard";
import type { AnalyticsData } from "@/types";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch("/api/proxy/analytics");
        const j = await r.json();
        setData(j);
      } catch {} finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-screen text-stone-400">Loading analytics...</div>;
  }

  const o = data?.overview || {
    total_campaigns: 0, active_campaigns: 0, total_prospects: 0,
    total_sent: 0, total_replied: 0, total_demos: 0,
    response_rate: 0, conversion_rate: 0, pipeline: {}, recent_sessions: [],
  };

  const funnel = data?.stage_funnel || [];
  const campaigns = data?.campaign_breakdown || [];
  const maxFunnel = Math.max(...funnel.map((f) => f.count), 1);

  return (
    <div>
      <header className="border-b border-border bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <h1 className="text-xl font-semibold">Analytics</h1>
          <p className="text-sm text-stone-500 mt-0.5">Campaign performance and outreach metrics</p>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        {/* Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Total Campaigns" value={o.total_campaigns} />
          <MetricCard label="Total Prospects" value={o.total_prospects} accent />
          <MetricCard label="Emails Sent" value={o.total_sent} />
          <MetricCard label="Response Rate" value={`${o.response_rate.toFixed(1)}%`} accent />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Stage funnel */}
          <section className="card">
            <h2 className="font-semibold mb-4">Pipeline Funnel (All Campaigns)</h2>
            {funnel.length === 0 ? (
              <p className="text-sm text-stone-400">No pipeline data yet.</p>
            ) : (
              <div className="space-y-2.5">
                {funnel.map((f) => (
                  <div key={f.stage}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-stone-600">{f.stage}</span>
                      <span className="font-semibold">{f.count} <span className="text-stone-400 font-normal">({f.pct.toFixed(0)}%)</span></span>
                    </div>
                    <div className="w-full bg-stone-100 rounded-full h-5 overflow-hidden">
                      <div
                        className="h-full bg-accent/70 rounded-full transition-all duration-500"
                        style={{ width: `${Math.max((f.count / maxFunnel) * 100, 3)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Key ratios */}
          <section className="card">
            <h2 className="font-semibold mb-4">Key Ratios</h2>
            <div className="space-y-4">
              <RatioBar label="Sourced → Sent" value={o.total_sent} total={o.total_prospects} />
              <RatioBar label="Sent → Replied" value={o.total_replied} total={o.total_sent} />
              <RatioBar label="Replied → Demo" value={o.total_demos} total={o.total_replied} />
              <RatioBar label="Overall Conversion" value={o.total_demos} total={o.total_prospects} />
            </div>
          </section>
        </div>

        {/* Campaign breakdown table */}
        <section className="card">
          <h2 className="font-semibold mb-4">Campaign Breakdown</h2>
          {campaigns.length === 0 ? (
            <p className="text-sm text-stone-400">No campaigns yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 pr-4 text-xs uppercase text-stone-500 font-semibold">Campaign</th>
                    <th className="text-left py-2 pr-4 text-xs uppercase text-stone-500 font-semibold">Phase</th>
                    <th className="text-right py-2 pr-4 text-xs uppercase text-stone-500 font-semibold">Prospects</th>
                    <th className="text-right py-2 pr-4 text-xs uppercase text-stone-500 font-semibold">Sent</th>
                    <th className="text-right py-2 pr-4 text-xs uppercase text-stone-500 font-semibold">Replied</th>
                    <th className="text-right py-2 pr-4 text-xs uppercase text-stone-500 font-semibold">Demos</th>
                    <th className="text-right py-2 text-xs uppercase text-stone-500 font-semibold">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {campaigns.map((c) => (
                    <tr key={c.session_id} className="border-b border-stone-100 hover:bg-stone-50">
                      <td className="py-2.5 pr-4 font-medium">{c.name}</td>
                      <td className="py-2.5 pr-4">
                        <span className={`pill text-[10px] ${
                          c.phase === "done" ? "pill-accent" :
                          c.phase === "idle" ? "" : "pill-warn"
                        }`}>{c.phase}</span>
                      </td>
                      <td className="py-2.5 pr-4 text-right">{c.prospects}</td>
                      <td className="py-2.5 pr-4 text-right">{c.sent}</td>
                      <td className="py-2.5 pr-4 text-right">{c.replied}</td>
                      <td className="py-2.5 pr-4 text-right">{c.demos}</td>
                      <td className="py-2.5 text-right text-stone-500">{new Date(c.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function RatioBar({ label, value, total }: { label: string; value: number; total: number }) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="text-stone-600">{label}</span>
        <span className="font-semibold">
          {value}/{total} <span className="text-stone-400 font-normal">({pct.toFixed(1)}%)</span>
        </span>
      </div>
      <div className="w-full bg-stone-100 rounded-full h-3 overflow-hidden">
        <div
          className="h-full bg-accent/60 rounded-full transition-all duration-500"
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
    </div>
  );
}
