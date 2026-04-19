"use client";

import { useEffect, useMemo, useState } from "react";
import type { CRMProspect, CRMNote, SessionInfo } from "@/types";

type ViewMode = "table" | "board" | "list";

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
    </svg>
  );
}

function EmailIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="4" width="20" height="16" rx="2"/>
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
    </svg>
  );
}

const STAGES = ["Sourced", "Researched", "Outreach Sent", "Replied", "Qualified", "Demo Booked", "Lost"];

const STAGE_COLORS: Record<string, string> = {
  "Sourced": "",
  "Researched": "pill-accent",
  "Outreach Sent": "pill-warn",
  "Replied": "pill-accent",
  "Qualified": "pill-accent",
  "Demo Booked": "pill-accent",
  "Lost": "pill-danger",
};

export default function CRMPage() {
  const [prospects, setProspects] = useState<CRMProspect[]>([]);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>("table");

  // Detail panel
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);
  const [stageUpdating, setStageUpdating] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [filterSession, setFilterSession] = useState<string>("all");
  const [filterStage, setFilterStage] = useState<string>("all");
  const [filterFitMin, setFilterFitMin] = useState(0);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [pr, sr] = await Promise.all([
        fetch("/api/proxy/crm/prospects"),
        fetch("/api/proxy/sessions"),
      ]);
      const pj = await pr.json();
      const sj = await sr.json();
      setProspects(pj.prospects || []);
      setSessions(sj.sessions || []);
    } catch {} finally {
      setLoading(false);
    }
  }

  const selectedProspect = prospects.find((p) => p.id === selectedId) || null;

  // --- Stage change ---
  async function changeStage(prospect: CRMProspect, newStage: string) {
    setStageUpdating(true);
    try {
      await fetch("/api/proxy/crm/stage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: prospect.session_id,
          dm_name: prospect.dm_name,
          stage: newStage,
        }),
      });
      // Update local state
      setProspects((prev) =>
        prev.map((p) =>
          p.id === prospect.id ? { ...p, stage: newStage } : p
        )
      );
    } catch {} finally {
      setStageUpdating(false);
    }
  }

  // --- Notes ---
  async function addNote(prospect: CRMProspect) {
    const content = noteText.trim();
    if (!content) return;
    setAddingNote(true);
    try {
      const r = await fetch("/api/proxy/crm/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: prospect.session_id,
          dm_name: prospect.dm_name,
          content,
        }),
      });
      const j = await r.json();
      if (j.note) {
        setProspects((prev) =>
          prev.map((p) =>
            p.id === prospect.id
              ? { ...p, notes: [j.note, ...p.notes] }
              : p
          )
        );
        setNoteText("");
      }
    } catch {} finally {
      setAddingNote(false);
    }
  }

  async function deleteNote(prospect: CRMProspect, noteId: string) {
    try {
      await fetch(`/api/proxy/crm/notes/${noteId}`, { method: "DELETE" });
      setProspects((prev) =>
        prev.map((p) =>
          p.id === prospect.id
            ? { ...p, notes: p.notes.filter((n) => n.id !== noteId) }
            : p
        )
      );
    } catch {}
  }

  // --- Filtering ---
  const filtered = useMemo(() => {
    return prospects.filter((p) => {
      if (filterSession !== "all" && p.session_id !== filterSession) return false;
      if (filterStage !== "all" && p.stage !== filterStage) return false;
      if ((p.fit_score || 0) < filterFitMin / 100) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const match = [p.dm_name, p.company, p.dm_title, p.email, p.stage]
          .filter(Boolean)
          .some((f) => f!.toLowerCase().includes(q));
        if (!match) return false;
      }
      return true;
    });
  }, [prospects, filterSession, filterStage, filterFitMin, searchQuery]);

  const stageGroups = useMemo(() => {
    const groups: Record<string, CRMProspect[]> = {};
    STAGES.forEach((s) => (groups[s] = []));
    filtered.forEach((p) => {
      if (!groups[p.stage]) groups[p.stage] = [];
      groups[p.stage].push(p);
    });
    return groups;
  }, [filtered]);

  const companyGroups = useMemo(() => {
    const groups: Record<string, CRMProspect[]> = {};
    filtered.forEach((p) => {
      if (!groups[p.company]) groups[p.company] = [];
      groups[p.company].push(p);
    });
    return groups;
  }, [filtered]);

  if (loading) {
    return <div className="flex items-center justify-center h-screen text-stone-400">Loading CRM…</div>;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Main area */}
      <div className={`flex-1 min-w-0 flex flex-col overflow-hidden ${selectedProspect ? "" : ""}`}>
        <header className="border-b border-border bg-white shrink-0">
          <div className="px-6 py-4 flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold">CRM</h1>
              <p className="text-sm text-stone-500 mt-1.5">{prospects.length} prospects across {sessions.length} campaigns</p>
            </div>
            <div className="flex gap-1">
              {(["table", "board", "list"] as ViewMode[]).map((v) => (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={`btn text-sm capitalize ${view === v ? "btn-primary" : ""}`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-auto">
          <div className="px-6 py-4">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <input
                className="input max-w-xs"
                placeholder="Search name, company, email…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <select
                className="select w-auto text-sm"
                value={filterSession}
                onChange={(e) => setFilterSession(e.target.value)}
              >
                <option value="all">All campaigns</option>
                {sessions.map((s) => (
                  <option key={s.session_id} value={s.session_id}>{s.name}</option>
                ))}
              </select>
              <select
                className="select w-auto text-sm"
                value={filterStage}
                onChange={(e) => setFilterStage(e.target.value)}
              >
                <option value="all">All stages</option>
                {STAGES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-stone-500">Fit ≥</span>
                <input
                  type="range" min={0} max={100} step={5}
                  value={filterFitMin}
                  onChange={(e) => setFilterFitMin(Number(e.target.value))}
                  className="w-24"
                />
                <span className="text-xs font-medium">{filterFitMin}%</span>
              </div>
              <div className="ml-auto text-sm text-stone-500">{filtered.length} results</div>
            </div>

            {/* Table View */}
            {view === "table" && (
              <div className="card overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 pr-3 text-xs uppercase text-stone-500 font-semibold">Name</th>
                      <th className="text-left py-2 pr-3 text-xs uppercase text-stone-500 font-semibold">Title</th>
                      <th className="text-left py-2 pr-3 text-xs uppercase text-stone-500 font-semibold">Company</th>
                      <th className="text-left py-2 pr-3 text-xs uppercase text-stone-500 font-semibold">Email</th>
                      <th className="text-left py-2 pr-3 text-xs uppercase text-stone-500 font-semibold">Stage</th>
                      <th className="text-right py-2 pr-3 text-xs uppercase text-stone-500 font-semibold">Fit</th>
                      <th className="text-left py-2 pr-3 text-xs uppercase text-stone-500 font-semibold">Campaign</th>
                      <th className="text-center py-2 text-xs uppercase text-stone-500 font-semibold">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.length === 0 ? (
                      <tr><td colSpan={8} className="py-8 text-center text-stone-400">No prospects match your filters.</td></tr>
                    ) : (
                      filtered.map((p) => (
                        <tr
                          key={p.id}
                          onClick={() => setSelectedId(selectedId === p.id ? null : p.id)}
                          className={`border-b border-stone-100 hover:bg-stone-50 cursor-pointer transition ${
                            selectedId === p.id ? "bg-accentSoft/30" : ""
                          }`}
                        >
                          <td className="py-2.5 pr-3">
                            <div className="flex items-center gap-2">
                              <div className="font-medium">{p.dm_name}</div>
                              <div className="flex items-center gap-1">
                                {p.dm_linkedin && (
                                  <a
                                    href={p.dm_linkedin} target="_blank" rel="noreferrer"
                                    className="text-[#0A66C2] hover:opacity-70 transition"
                                    onClick={(e) => e.stopPropagation()}
                                    title={p.dm_linkedin}
                                  ><LinkedInIcon /></a>
                                )}
                                {p.email && (
                                  <a
                                    href={`mailto:${p.email}`}
                                    className="text-stone-400 hover:text-stone-600 transition"
                                    onClick={(e) => e.stopPropagation()}
                                    title={p.email}
                                  ><EmailIcon /></a>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="py-2.5 pr-3 text-stone-600">{p.dm_title}</td>
                          <td className="py-2.5 pr-3 font-medium">{p.company}</td>
                          <td className="py-2.5 pr-3 text-stone-500 mono text-xs">{p.email || "—"}</td>
                          <td className="py-2.5 pr-3">
                            <select
                              className="text-xs rounded-full px-2 py-0.5 font-medium border-0 cursor-pointer bg-transparent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1"
                              style={{
                                background: STAGE_BG[p.stage] || "#f3f1ea",
                                color: STAGE_FG[p.stage] || "#555148",
                              }}
                              value={p.stage}
                              onChange={(e) => {
                                e.stopPropagation();
                                changeStage(p, e.target.value);
                              }}
                              onClick={(e) => e.stopPropagation()}
                            >
                              {STAGES.map((s) => (
                                <option key={s} value={s}>{s}</option>
                              ))}
                            </select>
                          </td>
                          <td className="py-2.5 pr-3 text-right">
                            {p.fit_score ? <span className="pill pill-accent text-[10px]">{Math.round(p.fit_score * 100)}%</span> : "—"}
                          </td>
                          <td className="py-2.5 pr-3 text-xs text-stone-500">{p.session_name}</td>
                          <td className="py-2.5 text-center">
                            {p.notes.length > 0 ? (
                              <span className="pill pill-accent text-[10px]">{p.notes.length}</span>
                            ) : (
                              <span className="text-stone-300 text-xs">—</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Board View (Kanban) */}
            {view === "board" && (
              <div className="flex gap-3 overflow-x-auto pb-4">
                {STAGES.map((stage) => (
                  <div key={stage} className="min-w-[240px] w-[240px] shrink-0">
                    <div className="flex items-center gap-2 mb-2 px-1">
                      <span className={`pill text-[10px] ${STAGE_COLORS[stage] || ""}`}>{stage}</span>
                      <span className="text-xs text-stone-400">{stageGroups[stage]?.length || 0}</span>
                    </div>
                    <div className="space-y-2">
                      {(stageGroups[stage] || []).map((p) => (
                        <div
                          key={p.id}
                          onClick={() => setSelectedId(selectedId === p.id ? null : p.id)}
                          className={`card text-sm cursor-pointer transition hover:border-accent/30 ${
                            selectedId === p.id ? "ring-2 ring-accent" : ""
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="font-medium text-sm">{p.dm_name}</div>
                            <div className="flex items-center gap-1">
                              {p.dm_linkedin && (
                                <a
                                  href={p.dm_linkedin} target="_blank" rel="noreferrer"
                                  className="text-[#0A66C2] hover:opacity-70 transition"
                                  onClick={(e) => e.stopPropagation()}
                                  title={p.dm_linkedin}
                                ><LinkedInIcon className="w-3 h-3" /></a>
                              )}
                              {p.email && (
                                <a
                                  href={`mailto:${p.email}`}
                                  className="text-stone-400 hover:text-stone-600 transition"
                                  onClick={(e) => e.stopPropagation()}
                                  title={p.email}
                                ><EmailIcon className="w-3 h-3" /></a>
                              )}
                            </div>
                          </div>
                          <div className="text-xs text-stone-500">{p.dm_title}</div>
                          <div className="text-xs font-medium mt-1">{p.company}</div>
                          <div className="flex items-center gap-1.5 mt-1.5">
                            {p.fit_score && (
                              <span className="pill pill-accent text-[10px]">{Math.round(p.fit_score * 100)}% fit</span>
                            )}
                            {p.notes.length > 0 && (
                              <span className="text-[10px] text-stone-400">{p.notes.length} notes</span>
                            )}
                          </div>
                          {/* Move stage dropdown */}
                          <div className="mt-2 pt-2 border-t border-stone-100">
                            <select
                              aria-label="Move to stage"
                              className="text-[10px] w-full rounded px-1.5 py-0.5 border border-stone-200 bg-white cursor-pointer"
                              value={p.stage}
                              onChange={(e) => {
                                e.stopPropagation();
                                changeStage(p, e.target.value);
                              }}
                              onClick={(e) => e.stopPropagation()}
                            >
                              {STAGES.map((s) => (
                                <option key={s} value={s}>{s}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                      ))}
                      {(stageGroups[stage] || []).length === 0 && (
                        <div className="text-xs text-stone-400 p-3 text-center border border-dashed border-stone-200 rounded-lg">
                          Empty
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* List View (grouped by company) */}
            {view === "list" && (
              <div className="space-y-4">
                {Object.entries(companyGroups).length === 0 ? (
                  <p className="text-sm text-stone-400 text-center py-8">No prospects match your filters.</p>
                ) : (
                  Object.entries(companyGroups).map(([company, members]) => (
                    <section key={company} className="card">
                      <div className="flex items-baseline justify-between mb-2">
                        <h3 className="font-semibold">{company}</h3>
                        <span className="text-xs text-stone-500">{members.length} contacts</span>
                      </div>
                      <div className="space-y-1.5">
                        {members.map((p) => (
                          <div
                            key={p.id}
                            onClick={() => setSelectedId(selectedId === p.id ? null : p.id)}
                            className={`flex items-center gap-3 py-2 px-2 rounded-lg border-b border-stone-50 last:border-0 cursor-pointer hover:bg-stone-50 transition ${
                              selectedId === p.id ? "bg-accentSoft/30" : ""
                            }`}
                          >
                            <div className="flex-1 min-w-0 flex items-center gap-2">
                              <span className="font-medium text-sm">{p.dm_name}</span>
                              <span className="text-stone-500 text-sm"> · {p.dm_title}</span>
                              <div className="flex items-center gap-1 ml-1">
                                {p.dm_linkedin && (
                                  <a
                                    href={p.dm_linkedin} target="_blank" rel="noreferrer"
                                    className="text-[#0A66C2] hover:opacity-70 transition"
                                    onClick={(e) => e.stopPropagation()}
                                    title={p.dm_linkedin}
                                  ><LinkedInIcon className="w-3 h-3" /></a>
                                )}
                                {p.email && (
                                  <a
                                    href={`mailto:${p.email}`}
                                    className="text-stone-400 hover:text-stone-600 transition"
                                    onClick={(e) => e.stopPropagation()}
                                    title={p.email}
                                  ><EmailIcon className="w-3 h-3" /></a>
                                )}
                              </div>
                            </div>
                            <select
                              className="text-[10px] rounded px-1.5 py-0.5 border border-stone-200 bg-white cursor-pointer"
                              value={p.stage}
                              onChange={(e) => {
                                e.stopPropagation();
                                changeStage(p, e.target.value);
                              }}
                              onClick={(e) => e.stopPropagation()}
                            >
                              {STAGES.map((s) => (
                                <option key={s} value={s}>{s}</option>
                              ))}
                            </select>
                            {p.fit_score && (
                              <span className="pill pill-accent text-[10px]">{Math.round(p.fit_score * 100)}%</span>
                            )}
                            {p.notes.length > 0 && (
                              <span className="text-[10px] text-stone-400">{p.notes.length} notes</span>
                            )}
                            <span className="text-[10px] text-stone-400">{p.session_name}</span>
                          </div>
                        ))}
                      </div>
                    </section>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detail / Notes Panel (slide-in from right) */}
      {selectedProspect && (
        <div className="w-96 shrink-0 border-l border-border bg-white flex flex-col h-full overflow-hidden">
          {/* Panel header */}
          <div className="px-4 py-3 border-b border-border shrink-0">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="font-semibold">{selectedProspect.dm_name}</div>
                <div className="text-sm text-stone-500">{selectedProspect.dm_title}</div>
                <div className="text-sm font-medium mt-0.5">{selectedProspect.company}</div>
              </div>
              <button
                onClick={() => setSelectedId(null)}
                className="text-stone-400 hover:text-stone-600 text-lg ml-2"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Panel body */}
          <div className="flex-1 overflow-y-auto">
            {/* Contact info */}
            <div className="px-4 py-3 border-b border-border space-y-2">
              {selectedProspect.email && (
                <div>
                  <div className="label">Email</div>
                  <a href={`mailto:${selectedProspect.email}`} className="text-sm text-stone-700 hover:text-accent transition flex items-center gap-1.5 mt-0.5">
                    <EmailIcon className="text-stone-400 shrink-0" />
                    <span className="mono break-all">{selectedProspect.email}</span>
                  </a>
                </div>
              )}
              {selectedProspect.dm_linkedin && (
                <div>
                  <div className="label">LinkedIn</div>
                  <a href={selectedProspect.dm_linkedin} target="_blank" rel="noreferrer" className="text-sm text-[#0A66C2] hover:opacity-70 transition flex items-center gap-1.5 mt-0.5">
                    <LinkedInIcon className="shrink-0" />
                    <span className="break-all">{selectedProspect.dm_linkedin.replace(/^https?:\/\//, "")}</span>
                  </a>
                </div>
              )}
              {selectedProspect.fit_score && (
                <div>
                  <div className="label">Fit Score</div>
                  <span className="pill pill-accent">{Math.round(selectedProspect.fit_score * 100)}%</span>
                </div>
              )}
              {selectedProspect.why_target && (
                <div>
                  <div className="label">Why Target</div>
                  <div className="text-sm text-stone-600">{selectedProspect.why_target}</div>
                </div>
              )}
              <div>
                <div className="label">Campaign</div>
                <div className="text-sm">{selectedProspect.session_name}</div>
              </div>
            </div>

            {/* Stage changer */}
            <div className="px-4 py-3 border-b border-border">
              <div className="label mb-1.5">Pipeline Stage</div>
              <div className="flex flex-wrap gap-1.5">
                {STAGES.map((s) => (
                  <button
                    key={s}
                    onClick={() => changeStage(selectedProspect, s)}
                    disabled={stageUpdating}
                    className={`pill cursor-pointer transition text-[11px] ${
                      selectedProspect.stage === s
                        ? STAGE_COLORS[s] || "ring-2 ring-accent bg-accentSoft text-accent"
                        : "hover:bg-stone-200"
                    } ${selectedProspect.stage === s ? "ring-1 ring-offset-1 ring-accent" : ""}`}
                  >
                    {s}
                  </button>
                ))}
              </div>
              {stageUpdating && <div className="text-xs text-stone-400 mt-1">Updating…</div>}
            </div>

            {/* Notes */}
            <div className="px-4 py-3">
              <div className="label mb-2">Notes & Comments</div>

              {/* Add note */}
              <div className="mb-3">
                <textarea
                  className="textarea text-sm h-20"
                  placeholder="Add a note — meeting feedback, call summary, next steps…"
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                      addNote(selectedProspect);
                    }
                  }}
                />
                <div className="flex items-center justify-between mt-1.5">
                  <span className="text-[10px] text-stone-400">Cmd+Enter to save</span>
                  <button
                    onClick={() => addNote(selectedProspect)}
                    disabled={addingNote || !noteText.trim()}
                    className="btn btn-primary text-xs py-1"
                  >
                    {addingNote ? "Saving…" : "Add Note"}
                  </button>
                </div>
              </div>

              {/* Notes list */}
              {selectedProspect.notes.length === 0 ? (
                <p className="text-xs text-stone-400 text-center py-4">No notes yet. Add one above.</p>
              ) : (
                <div className="space-y-2">
                  {selectedProspect.notes.map((note) => (
                    <div key={note.id} className="p-2.5 rounded-lg bg-stone-50 border border-stone-100 group">
                      <div className="text-sm whitespace-pre-wrap">{note.content}</div>
                      <div className="flex items-center justify-between mt-1.5">
                        <span className="text-[10px] text-stone-400">
                          {new Date(note.created_at).toLocaleString()}
                        </span>
                        <button
                          onClick={() => deleteNote(selectedProspect, note.id)}
                          className="text-[10px] text-stone-400 hover:text-danger opacity-0 group-hover:opacity-100 transition"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Stage color maps for the inline select in table view
const STAGE_BG: Record<string, string> = {
  "Sourced": "#f3f1ea",
  "Researched": "#dff5e8",
  "Outreach Sent": "#ffe9d3",
  "Replied": "#dff5e8",
  "Qualified": "#dff5e8",
  "Demo Booked": "#dff5e8",
  "Lost": "#fde2de",
};

const STAGE_FG: Record<string, string> = {
  "Sourced": "#555148",
  "Researched": "#0a7c4a",
  "Outreach Sent": "#b25400",
  "Replied": "#0a7c4a",
  "Qualified": "#0a7c4a",
  "Demo Booked": "#0a7c4a",
  "Lost": "#c0392b",
};
