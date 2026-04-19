"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import MetricCard from "@/components/MetricCard";
import { HomePageSkeleton } from "@/components/Skeleton";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import type { StatsOverview, SessionInfo } from "@/types";

export default function HomePage() {
  useDocumentTitle("Overview");
  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  async function loadStats() {
    try {
      const r = await fetch("/api/proxy/stats");
      const j = await r.json();
      setStats(j);
    } catch {} finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <HomePageSkeleton />;
  }

  const s = stats || {
    total_campaigns: 0,
    active_campaigns: 0,
    total_prospects: 0,
    total_sent: 0,
    total_replied: 0,
    total_demos: 0,
    response_rate: 0,
    conversion_rate: 0,
    pipeline: {},
    recent_sessions: [],
  };

  const STAGES = ["Sourced", "Researched", "Outreach Sent", "Replied", "Qualified", "Demo Booked"];
  const maxStage = Math.max(...STAGES.map((st) => s.pipeline[st] || 0), 1);

  return (
    <div>
      {/* Header */}
      <header className="border-b border-border bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="text-sm text-stone-500 mt-1.5">Your SalesOS command center</p>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        {/* Metric cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <MetricCard label="Campaigns" value={s.total_campaigns} sub={`${s.active_campaigns} active`} />
          <MetricCard label="Prospects" value={s.total_prospects} accent />
          <MetricCard label="Emails Sent" value={s.total_sent} />
          <MetricCard label="Replied" value={s.total_replied} accent />
          <MetricCard label="Response Rate" value={`${s.response_rate.toFixed(1)}%`} />
          <MetricCard label="Demos Booked" value={s.total_demos} accent />
        </div>

        {/* Pipeline Funnel */}
        <section className="card">
          <h2 className="font-semibold mb-4">Pipeline Funnel</h2>
          <div className="space-y-3">
            {STAGES.map((stage) => {
              const count = s.pipeline[stage] || 0;
              const pct = maxStage > 0 ? (count / maxStage) * 100 : 0;
              return (
                <div key={stage} className="flex items-center gap-3">
                  <div className="w-28 text-sm text-stone-600 text-right shrink-0">{stage}</div>
                  <div className="flex-1 bg-stone-100 rounded-full h-7 overflow-hidden relative">
                    <div
                      className="h-full bg-accent/80 rounded-full transition-all duration-500"
                      style={{ width: `${Math.max(pct, 2)}%` }}
                    />
                    <span className="absolute inset-y-0 left-3 flex items-center text-xs font-semibold">
                      {count}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Campaigns */}
          <section className="card">
            <div className="flex items-baseline justify-between mb-3">
              <h2 className="font-semibold">Recent Campaigns</h2>
              <Link href="/campaigns" className="text-sm text-accent hover:underline">View all</Link>
            </div>
            {s.recent_sessions.length === 0 ? (
              <p className="text-sm text-stone-400">No campaigns yet. Create one to get started.</p>
            ) : (
              <div className="space-y-2">
                {s.recent_sessions.slice(0, 5).map((sess: SessionInfo) => {
                  const prospects = (() => { try { return JSON.parse(sess.prospects_json || "[]").length; } catch { return 0; } })();
                  return (
                    <Link
                      key={sess.session_id}
                      href={`/campaigns/${sess.session_id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-stone-50 transition border border-transparent hover:border-border"
                    >
                      <div>
                        <div className="font-medium text-sm">{sess.name}</div>
                        <div className="text-xs text-stone-500 mt-0.5">
                          {prospects} prospects · {new Date(sess.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <span className={`pill ${
                        sess.phase === "done" ? "pill-accent" :
                        sess.phase === "idle" ? "" :
                        "pill-warn"
                      }`}>
                        {sess.phase}
                      </span>
                    </Link>
                  );
                })}
              </div>
            )}
          </section>

          {/* Quick Actions */}
          <section className="card">
            <h2 className="font-semibold mb-3">Quick Actions</h2>
            <div className="grid grid-cols-1 gap-2">
              <Link href="/campaigns" className="flex items-center gap-3 p-3 rounded-lg hover:bg-stone-50 transition border border-border">
                <span className="w-9 h-9 rounded-lg bg-accent/10 text-accent flex items-center justify-center text-lg">+</span>
                <div>
                  <div className="font-medium text-sm">New Campaign</div>
                  <div className="text-xs text-stone-500">Source prospects and send outreach</div>
                </div>
              </Link>
              <Link href="/crm" className="flex items-center gap-3 p-3 rounded-lg hover:bg-stone-50 transition border border-border">
                <span className="w-9 h-9 rounded-lg bg-accent/10 text-accent flex items-center justify-center text-lg">◫</span>
                <div>
                  <div className="font-medium text-sm">Open CRM</div>
                  <div className="text-xs text-stone-500">Manage all prospects across campaigns</div>
                </div>
              </Link>
              <Link href="/governance" className="flex items-center gap-3 p-3 rounded-lg hover:bg-stone-50 transition border border-border">
                <span className="w-9 h-9 rounded-lg bg-accent/10 text-accent flex items-center justify-center text-lg">◈</span>
                <div>
                  <div className="font-medium text-sm">Company Settings</div>
                  <div className="text-xs text-stone-500">ICPs, sender profiles, and company info</div>
                </div>
              </Link>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
