"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import type { SessionInfo } from "@/types";

export default function CampaignsListPage() {
  useDocumentTitle("Campaigns");
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [sortBy, setSortBy] = useState<"date" | "name" | "phase">("date");
  const [filterPhase, setFilterPhase] = useState<string>("all");
  const router = useRouter();

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {
    try {
      const r = await fetch("/api/proxy/sessions");
      const j = await r.json();
      setSessions(j.sessions || []);
    } catch {} finally {
      setLoading(false);
    }
  }

  async function createSession() {
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    try {
      const r = await fetch("/api/proxy/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const j = await r.json();
      if (j.session) {
        router.push(`/campaigns/${j.session.session_id}`);
      }
    } catch {} finally {
      setCreating(false);
      setNewName("");
    }
  }

  async function deleteSession(id: string) {
    try {
      await fetch(`/api/proxy/sessions/${id}`, { method: "DELETE" });
      setSessions((prev) => prev.filter((s) => s.session_id !== id));
    } catch {}
  }

  const phases = ["all", ...new Set(sessions.map((s) => s.phase))];

  const filtered = sessions
    .filter((s) => filterPhase === "all" || s.phase === filterPhase)
    .sort((a, b) => {
      if (sortBy === "name") return a.name.localeCompare(b.name);
      if (sortBy === "phase") return a.phase.localeCompare(b.phase);
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen text-stone-400">Loading campaigns…</div>
    );
  }

  return (
    <div>
      <header className="border-b border-border bg-white">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Campaigns</h1>
            <p className="text-sm text-stone-500 mt-1.5">{sessions.length} total campaigns</p>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-6 space-y-4">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-1">
            {phases.map((p) => (
              <button
                key={p}
                onClick={() => setFilterPhase(p)}
                className={`pill cursor-pointer transition ${filterPhase === p ? "pill-accent" : ""}`}
              >
                {p}
              </button>
            ))}
          </div>
          <div className="ml-auto flex gap-2">
            <select
              className="select w-auto text-sm"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
            >
              <option value="date">Sort by date</option>
              <option value="name">Sort by name</option>
              <option value="phase">Sort by phase</option>
            </select>
          </div>
        </div>

        {/* Campaign list */}
        <div className="space-y-2">
          {filtered.map((s) => {
            const prospects = (() => { try { return JSON.parse(s.prospects_json || "[]").length; } catch { return 0; } })();
            const drafts = (() => { try { return JSON.parse(s.drafts_json || "[]").length; } catch { return 0; } })();
            return (
              <Link
                key={s.session_id}
                href={`/campaigns/${s.session_id}`}
                className="card flex items-center justify-between hover:border-accent/30 transition group"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm group-hover:text-accent transition">{s.name}</span>
                    <span className={`pill text-[10px] ${
                      s.phase === "done" ? "pill-accent" :
                      s.phase === "idle" ? "" :
                      "pill-warn"
                    }`}>
                      {s.phase}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-stone-500">
                    <span>{prospects} prospects</span>
                    <span>{drafts} drafts</span>
                    <span>{new Date(s.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      deleteSession(s.session_id);
                    }}
                    className="text-stone-400 hover:text-danger text-xs px-2 py-1 opacity-0 group-hover:opacity-100 transition"
                  >
                    Delete
                  </button>
                  <span className="text-stone-400 text-sm">→</span>
                </div>
              </Link>
            );
          })}
        </div>

        {/* New campaign */}
        <div className="card border-dashed">
          <div className="flex gap-2">
            <input
              className="input flex-1"
              placeholder="New campaign name…"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createSession()}
            />
            <button
              onClick={createSession}
              disabled={creating || !newName.trim()}
              className="btn btn-primary"
            >
              {creating ? "Creating…" : "+ New Campaign"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
