"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import MetricCard from "@/components/MetricCard";
import { HomePageSkeleton } from "@/components/Skeleton";
import ErrorBanner from "@/components/ErrorBanner";
import EmptyState from "@/components/EmptyState";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import type { StatsOverview, SessionInfo } from "@/types";

function greetingFor(date: Date): string {
  const h = date.getHours();
  if (h < 5) return "Still up";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  if (h < 22) return "Good evening";
  return "Burning the midnight oil";
}

function nameFromEmail(email: string | null): string {
  if (!email) return "there";
  const local = email.split("@")[0] || "there";
  const first = local.split(/[._-]/)[0] || local;
  const clean = first.replace(/\d+$/, "") || first;
  return clean.charAt(0).toUpperCase() + clean.slice(1);
}

export default function HomePage() {
  useDocumentTitle("Overview");
  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    loadStats();
    fetch("/api/auth/me")
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => setEmail(j?.user?.email ?? null))
      .catch(() => {});
    // Initialize and tick every minute so the greeting flips when the
    // user crosses noon / 5pm / 10pm with the tab open.
    setNow(new Date());
    const id = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  async function loadStats() {
    setError(null);
    setLoading(true);
    try {
      const r = await fetch("/api/proxy/stats");
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      const j = await r.json();
      setStats(j);
    } catch (e: any) {
      setError(e?.message || "Network error — couldn’t reach the server.");
    } finally {
      setLoading(false);
    }
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

  // Hooks must run on every render — keep this above the early return.
  const funnelSummary = useMemo(() => {
    if (s.total_prospects === 0) {
      return "Your funnel is empty — spin up a campaign to start sourcing prospects.";
    }
    const parts: string[] = [];
    parts.push(`${s.total_prospects} prospect${s.total_prospects === 1 ? "" : "s"} in your funnel`);
    if (s.total_sent > 0) {
      parts.push(`${s.total_sent} sent`);
    }
    if (s.total_replied > 0) {
      parts.push(`${s.total_replied} replied (${s.response_rate.toFixed(1)}%)`);
    }
    if (s.total_demos > 0) {
      parts.push(`${s.total_demos} demo${s.total_demos === 1 ? "" : "s"} booked`);
    }
    return parts.join(" · ") + ".";
  }, [s.total_prospects, s.total_sent, s.total_replied, s.total_demos, s.response_rate]);

  if (loading) {
    return <HomePageSkeleton />;
  }

  const STAGES = ["Sourced", "Researched", "Outreach Sent", "Replied", "Qualified", "Demo Booked"];
  const maxStage = Math.max(...STAGES.map((st) => s.pipeline[st] || 0), 1);

  const displayName = nameFromEmail(email);
  const greeting = now ? greetingFor(now) : "Welcome";

  return (
    <div>
      {/* Header */}
      <header className="border-b border-border bg-white">
        <div className="max-w-6xl mx-auto px-6 py-5">
          <h1 className="text-2xl font-semibold tracking-tight">
            {greeting}, {displayName}
            <span className="text-stone-400 font-normal">.</span>
          </h1>
          <p className="text-sm text-stone-500 mt-1.5">{funnelSummary}</p>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        {error && <ErrorBanner message={error} onRetry={loadStats} />}

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
              <EmptyState
                icon={
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="4" width="18" height="16" rx="2" />
                    <line x1="3" y1="10" x2="21" y2="10" />
                    <line x1="8" y1="14" x2="14" y2="14" />
                  </svg>
                }
                title="No campaigns yet"
                description="Spin up your first outbound campaign — VP Sales plans, SDR sources, AE drafts."
                action={{ label: "+ New campaign", href: "/campaigns" }}
              />
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
