"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import Link from "next/link";
import type { Prospect, Draft, SentResult, Activity, SessionInfo, FollowUpSet } from "@/types";

const DEFAULT_ICP =
  "Indian AI startup founders, Series A or earlier, building AI agent products, raised in 2024-2025.";

export default function CampaignDetailPage({ params }: { params: { id: string } }) {
  const sessionId = params.id;

  const [session, setSession] = useState<SessionInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const [icp, setIcp] = useState(DEFAULT_ICP);
  const [targetCount, setTargetCount] = useState(8);

  const [runId, setRunId] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "sourcing" | "review" | "drafting" | "ready" | "sending" | "done">("idle");
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [sent, setSent] = useState<SentResult[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Follow-up state
  const [followUpSets, setFollowUpSets] = useState<FollowUpSet[]>([]);
  const [followUpSelected, setFollowUpSelected] = useState<Set<number>>(new Set());
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [followUpSending, setFollowUpSending] = useState(false);
  const [meetingLink, setMeetingLink] = useState("");

  // Objection state
  const [objection, setObjection] = useState({
    prospect_name: "",
    company: "",
    original_email: "",
    reply: "We already use HubSpot for outreach, not interested.",
  });
  const [objectionResp, setObjectionResp] = useState<{ subject: string; body: string; reasoning: string } | null>(null);
  const [objectionLoading, setObjectionLoading] = useState(false);

  function pushActivity(items: Activity[]) {
    setActivity((prev) => [...prev, ...items]);
  }

  // Load session data
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`/api/proxy/sessions/${sessionId}`);
        const j = await r.json();
        if (j.session) {
          const sess = j.session;
          setSession(sess);
          setPhase((sess.phase as any) || "idle");
          setRunId(sess.run_ids?.[sess.run_ids.length - 1] || null);
          try { setProspects(JSON.parse(sess.prospects_json || "[]")); } catch { setProspects([]); }
          try { setDrafts(JSON.parse(sess.drafts_json || "[]")); } catch { setDrafts([]); }
        }
        // Load meeting link from governance
        try {
          const gr = await fetch("/api/proxy/governance");
          const gj = await gr.json();
          if (gj.company?.meeting_link) setMeetingLink(gj.company.meeting_link);
        } catch {}
      } catch {} finally {
        setLoading(false);
      }
    })();
  }, [sessionId]);

  async function startCampaign() {
    setError(null);
    setPhase("sourcing");
    setProspects([]);
    setDrafts([]);
    setSent([]);
    setSelected(new Set());
    pushActivity([{ event: "vp_planning", icp, target_count: targetCount }]);

    try {
      const r = await fetch("/api/proxy/campaign/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ icp, target_count: targetCount, session_id: sessionId }),
      });
      const j = await r.json();
      if (!r.ok || j.error) {
        setError(j.error || "Sourcing failed.");
        setPhase("idle");
        return;
      }
      setRunId(j.run_id);
      setProspects(j.prospects || []);
      pushActivity(j.activity || []);
      pushActivity([{ event: "ready_for_review", count: (j.prospects || []).length }]);
      setPhase("review");
    } catch (e: any) {
      setError(e?.message || "Network error during sourcing.");
      setPhase("idle");
    }
  }

  async function draftSelected() {
    if (!runId || selected.size === 0) return;
    setPhase("drafting");
    setDrafts([]);
    const picked = Array.from(selected).map((i) => prospects[i]);
    pushActivity([{ event: "vp_routing_to_ae", count: picked.length }]);

    try {
      const r = await fetch("/api/proxy/campaign/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({ run_id: runId, prospects: picked, session_id: sessionId }),
      });

      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        setError(j.error || "Drafting failed.");
        setPhase("review");
        return;
      }

      // Read SSE stream for live progress
      const reader = r.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // keep incomplete last line

          for (const line of lines) {
            if (line.startsWith("data:")) {
              const dataStr = line.slice(5).trim();
              if (!dataStr) continue;
              try {
                const evt = JSON.parse(dataStr);

                // Show live progress in activity feed
                if (evt.step === "starting") {
                  pushActivity([{
                    event: "ae_researching",
                    prospect: evt.prospect,
                    company: evt.company,
                    detail: `(${evt.index + 1}/${evt.total}) Researching ${evt.prospect}...`,
                  }]);
                } else if (evt.step === "enriching") {
                  pushActivity([{
                    event: "ae_enriching",
                    prospect: evt.prospect,
                    detail: evt.detail,
                  }]);
                } else if (evt.step === "draft_complete") {
                  // Add draft as it arrives — user sees them appear one by one
                  setDrafts((prev) => [...prev, evt.draft]);
                  pushActivity([{
                    event: "drafted",
                    prospect: evt.prospect,
                    subject: evt.subject,
                    detail: `(${evt.index + 1}/${evt.total}) Done`,
                  }]);
                } else if (evt.step === "draft_error") {
                  pushActivity([{
                    event: "draft_error",
                    prospect: evt.prospect,
                    error: evt.error,
                  }]);
                } else if (evt.step === "all_done") {
                  // Final: set all drafts (in case any were missed)
                  setDrafts(evt.drafts || []);
                  pushActivity(evt.activity || []);
                }
              } catch {
                // not valid JSON, skip
              }
            }
          }
        }
      }

      setPhase("ready");
    } catch (e: any) {
      setError(e?.message || "Network error during drafting.");
      setPhase("review");
    }
  }

  function updateDraft(idx: number, patch: Partial<Draft>) {
    setDrafts((prev) => prev.map((d, i) => (i === idx ? { ...d, ...patch } : d)));
  }

  async function sendOne(idx: number) {
    if (!runId) return;
    const d = drafts[idx];
    setPhase("sending");
    pushActivity([{ event: "ae_sending", to: d.to_email }]);
    try {
      const r = await fetch("/api/proxy/campaign/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId, drafts: [d], session_id: sessionId }),
      });
      const j = await r.json();
      const newSent = (j.sent || [])[0];
      if (newSent) setSent((prev) => [...prev, newSent]);
      pushActivity(j.activity || []);
      setDrafts((prev) => prev.filter((_, i) => i !== idx));
      setPhase(drafts.length - 1 > 0 ? "ready" : "done");
    } catch (e: any) {
      setError(e?.message || "Send failed.");
      setPhase("ready");
    }
  }

  async function sendAll() {
    if (!runId || drafts.length === 0) return;
    setPhase("sending");
    pushActivity([{ event: "ae_sending_all", count: drafts.length }]);
    try {
      const r = await fetch("/api/proxy/campaign/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId, drafts, session_id: sessionId }),
      });
      const j = await r.json();
      setSent((prev) => [...prev, ...(j.sent || [])]);
      pushActivity(j.activity || []);
      setDrafts([]);
      setPhase("done");
    } catch (e: any) {
      setError(e?.message || "Send failed.");
      setPhase("ready");
    }
  }

  // Follow-up functions
  async function generateFollowUps() {
    if (followUpSelected.size === 0) return;
    setFollowUpLoading(true);
    const picked = Array.from(followUpSelected).map((i) => prospects[i]);
    try {
      const r = await fetch("/api/proxy/campaign/followup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: runId,
          session_id: sessionId,
          prospects: picked,
          meeting_link: meetingLink,
        }),
      });
      const j = await r.json();
      setFollowUpSets(j.followups || []);
    } catch {} finally {
      setFollowUpLoading(false);
    }
  }

  async function sendFollowUps() {
    const toSend = followUpSets
      .filter((f) => f.selected_variant)
      .map((f) => {
        const variant = f.variants.find((v) => v.id === f.selected_variant);
        return variant ? { to_email: f.to_email, to_name: f.prospect.dm_name, company: f.prospect.company, subject: variant.subject, body: variant.body } : null;
      })
      .filter(Boolean);

    if (toSend.length === 0) return;
    setFollowUpSending(true);
    try {
      await fetch("/api/proxy/campaign/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId, drafts: toSend, session_id: sessionId }),
      });
      pushActivity([{ event: "followups_sent", count: toSend.length }]);
      setFollowUpSets([]);
      setFollowUpSelected(new Set());
    } catch {} finally {
      setFollowUpSending(false);
    }
  }

  function selectFollowUpVariant(setIdx: number, variantId: string) {
    setFollowUpSets((prev) =>
      prev.map((f, i) => (i === setIdx ? { ...f, selected_variant: variantId } : f))
    );
  }

  async function draftObjection() {
    setObjectionLoading(true);
    setObjectionResp(null);
    try {
      const r = await fetch("/api/proxy/campaign/objection", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prospect_email: "demo@salesos.opensource",
          prospect_name: objection.prospect_name || "the prospect",
          company: objection.company || "the company",
          original_email: objection.original_email || "(our previous outreach)",
          reply: objection.reply,
        }),
      });
      const j = await r.json();
      setObjectionResp({ subject: j.response_subject, body: j.response_body, reasoning: j.reasoning });
    } catch (e: any) {
      setObjectionResp({ subject: "Error", body: e?.message || "failed", reasoning: "" });
    } finally {
      setObjectionLoading(false);
    }
  }

  const phaseLabel = useMemo(
    () =>
      ({
        idle: "Ready",
        sourcing: "VP routing → SDR sourcing prospects…",
        review: "SDR done. Select prospects to draft outreach.",
        drafting: "VP routing → AE enriching, drafting emails…",
        ready: "Drafts ready. Review and approve to send.",
        sending: "Sending via SendGrid…",
        done: "Sent. Done.",
      } as const)[phase],
    [phase]
  );

  if (loading) {
    return <div className="flex items-center justify-center h-screen text-stone-400">Loading campaign…</div>;
  }

  return (
    <div>
      {/* Header */}
      <header className="border-b border-border bg-white">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/campaigns" className="text-stone-400 hover:text-stone-600 text-sm">← Campaigns</Link>
            <div>
              <div className="font-semibold">{session?.name || "Campaign"}</div>
              <div className="text-xs text-stone-500">{session?.phase || "idle"}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {runId && <Link href={`/trace/${runId}`} className="btn text-sm">View trace →</Link>}
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        {/* ICP form */}
        <section className="card">
          <div className="flex items-baseline justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold">Define your ICP</h2>
              <p className="text-sm text-stone-500">VP Sales will plan, SDR will source, AE will draft.</p>
            </div>
            <div className="text-xs pill">{phaseLabel}</div>
          </div>
          <textarea
            className="textarea h-24"
            value={icp}
            onChange={(e) => setIcp(e.target.value)}
            placeholder="e.g. Indian AI startup founders, Series A or earlier…"
          />
          <div className="flex flex-wrap items-end gap-3 mt-3">
            <div>
              <label className="label">Target count</label>
              <input
                type="number" min={3} max={15}
                value={targetCount}
                onChange={(e) => setTargetCount(Number(e.target.value))}
                className="input mt-1 w-24"
              />
            </div>
            <button
              onClick={startCampaign}
              disabled={phase === "sourcing" || phase === "drafting" || phase === "sending"}
              className="btn btn-primary ml-auto"
            >
              {phase === "sourcing" ? "Sourcing…" : "▶ Run sales team"}
            </button>
          </div>
          {error && <div className="text-sm pill pill-danger mt-3">{error}</div>}
        </section>

        {/* Live activity */}
        <section className="card">
          <div className="flex items-baseline justify-between mb-2">
            <h3 className="font-semibold">Live activity</h3>
            <span className="text-xs text-stone-500">{activity.length} events</span>
          </div>
          <div className="bg-stone-50 rounded-md p-3 font-mono text-xs max-h-44 overflow-auto space-y-1">
            {activity.length === 0 && <div className="text-stone-400">No activity yet — click Run.</div>}
            {activity.map((a, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-stone-400">{String(i + 1).padStart(2, "0")}.</span>
                <span className="font-semibold text-accent">{a.event}</span>
                <span className="text-stone-600 truncate">
                  {Object.entries(a)
                    .filter(([k]) => k !== "event")
                    .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
                    .join(" · ")}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Prospects */}
        {prospects.length > 0 && (
          <section className="card">
            <div className="flex items-baseline justify-between mb-3">
              <div>
                <h3 className="font-semibold">Prospects ({prospects.length})</h3>
                <p className="text-sm text-stone-500">SDR found these via Exa + Crustdata. Pick who to enrich + draft.</p>
              </div>
              <button
                onClick={draftSelected}
                disabled={selected.size === 0 || phase === "drafting"}
                className="btn btn-primary"
              >
                {phase === "drafting" ? "Drafting…" : `Draft outreach (${selected.size})`}
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {prospects.map((p, i) => {
                const isSel = selected.has(i);
                return (
                  <label key={i} className={`card cursor-pointer transition ${isSel ? "ring-2 ring-accent" : ""}`}>
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox" checked={isSel}
                        onChange={() => {
                          const next = new Set(selected);
                          if (isSel) next.delete(i); else next.add(i);
                          setSelected(next);
                        }}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline justify-between gap-2">
                          <div className="font-semibold truncate">{p.dm_name}</div>
                          {typeof p.fit_score === "number" && (
                            <span className="pill pill-accent">{Math.round((p.fit_score || 0) * 100)}% fit</span>
                          )}
                        </div>
                        <div className="text-sm text-stone-600">
                          {p.dm_title} · <span className="font-medium">{p.company}</span>
                        </div>
                        {p.why_target && <div className="text-sm text-stone-700 mt-2">{p.why_target}</div>}
                        {p.dm_linkedin && (
                          <a href={p.dm_linkedin} target="_blank" rel="noreferrer" className="text-xs text-accent mt-2 inline-block hover:underline">
                            {p.dm_linkedin.replace(/^https?:\/\//, "")}
                          </a>
                        )}
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          </section>
        )}

        {/* Drafts */}
        {drafts.length > 0 && (
          <section className="card">
            <div className="flex items-baseline justify-between mb-3">
              <div>
                <h3 className="font-semibold">Drafts ({drafts.length})</h3>
                <p className="text-sm text-stone-500">VP review before send. Click body to edit.</p>
              </div>
              <button onClick={sendAll} disabled={phase === "sending"} className="btn btn-primary">
                {phase === "sending" ? "Sending…" : `▶ Send all (${drafts.length})`}
              </button>
            </div>
            <div className="space-y-3">
              {drafts.map((d, i) => (
                <div key={i} className="card">
                  <div className="flex items-baseline justify-between gap-2 mb-2">
                    <div>
                      <div className="text-xs text-stone-500">To</div>
                      <div className="font-medium">{d.to_name} <span className="text-stone-500">&lt;{d.to_email}&gt;</span></div>
                    </div>
                    <button onClick={() => sendOne(i)} className="btn btn-primary">Approve & Send</button>
                  </div>
                  <input className="input mb-2 font-medium" value={d.subject} onChange={(e) => updateDraft(i, { subject: e.target.value })} />
                  <textarea className="textarea h-32 mono text-sm" value={d.body} onChange={(e) => updateDraft(i, { body: e.target.value })} />
                  {d.personalization_hooks && d.personalization_hooks.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      <span className="label mr-1">Hooks:</span>
                      {d.personalization_hooks.map((h, j) => (
                        <span key={j} className="pill pill-accent text-xs">{h}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Sent results */}
        {sent.length > 0 && (
          <section className="card">
            <div className="flex items-baseline justify-between mb-3">
              <h3 className="font-semibold">Sent ({sent.length})</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {sent.map((s, i) => (
                <div key={i} className="card">
                  <div className="flex items-center gap-2">
                    <span className={`pill ${s.success ? "pill-accent" : "pill-danger"}`}>{s.success ? "sent" : "failed"}</span>
                    {s.message_id && <span className="text-xs mono text-stone-500 truncate">{s.message_id}</span>}
                  </div>
                  {s.error && <div className="text-sm text-danger mt-1">{s.error}</div>}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Follow-Up / Nudge — visible after emails sent */}
        {(phase === "done" || sent.length > 0) && prospects.length > 0 && (
          <section className="card">
            <h3 className="font-semibold mb-1">Follow Up / Nudge</h3>
            <p className="text-sm text-stone-500 mb-3">
              Select prospects to generate 3 follow-up options each: gentle nudge, value-add, or meeting request.
            </p>

            {/* Meeting link */}
            <div className="mb-3">
              <label className="label">Meeting link (for meeting-request variant)</label>
              <input
                className="input mt-1"
                placeholder="https://calendly.com/you/30min"
                value={meetingLink}
                onChange={(e) => setMeetingLink(e.target.value)}
              />
            </div>

            {/* Prospect selection for follow-up */}
            {followUpSets.length === 0 && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3">
                  {prospects.map((p, i) => {
                    const isSel = followUpSelected.has(i);
                    return (
                      <label key={i} className={`flex items-center gap-2 p-2 rounded-lg border transition cursor-pointer ${isSel ? "border-accent bg-accentSoft/30" : "border-border"}`}>
                        <input
                          type="checkbox" checked={isSel}
                          onChange={() => {
                            const next = new Set(followUpSelected);
                            if (isSel) next.delete(i); else next.add(i);
                            setFollowUpSelected(next);
                          }}
                        />
                        <div className="text-sm">
                          <span className="font-medium">{p.dm_name}</span>
                          <span className="text-stone-500"> · {p.company}</span>
                        </div>
                      </label>
                    );
                  })}
                </div>
                <button
                  onClick={generateFollowUps}
                  disabled={followUpSelected.size === 0 || followUpLoading}
                  className="btn btn-primary"
                >
                  {followUpLoading ? "Generating…" : `Generate follow-ups (${followUpSelected.size})`}
                </button>
              </>
            )}

            {/* Follow-up draft options */}
            {followUpSets.length > 0 && (
              <div className="space-y-4 mt-3">
                {followUpSets.map((fset, si) => (
                  <div key={si} className="card">
                    <div className="font-medium text-sm mb-2">
                      {fset.prospect.dm_name} <span className="text-stone-500">· {fset.prospect.company}</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                      {fset.variants.map((v) => (
                        <label
                          key={v.id}
                          className={`card cursor-pointer transition text-sm ${
                            fset.selected_variant === v.id ? "ring-2 ring-accent" : ""
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            <input
                              type="radio"
                              name={`followup-${si}`}
                              checked={fset.selected_variant === v.id}
                              onChange={() => selectFollowUpVariant(si, v.id)}
                              className="mt-1"
                            />
                            <div>
                              <div className={`pill text-[10px] mb-1 ${
                                v.type === "gentle_nudge" ? "" :
                                v.type === "value_add" ? "pill-accent" :
                                "pill-warn"
                              }`}>
                                {v.label}
                              </div>
                              <div className="font-medium text-xs">{v.subject}</div>
                              <div className="text-xs text-stone-500 mt-1 line-clamp-3">{v.body}</div>
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
                <div className="flex gap-2">
                  <button
                    onClick={sendFollowUps}
                    disabled={followUpSending || !followUpSets.some((f) => f.selected_variant)}
                    className="btn btn-primary"
                  >
                    {followUpSending ? "Sending…" : "Send selected follow-ups"}
                  </button>
                  <button onClick={() => { setFollowUpSets([]); setFollowUpSelected(new Set()); }} className="btn">
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </section>
        )}

        {/* Objection handling */}
        <section className="card">
          <h3 className="font-semibold mb-1">Got a reply? Draft an objection response</h3>
          <p className="text-sm text-stone-500 mb-3">Paste a reply, AE drafts a 2-sentence non-defensive response.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-2">
            <input className="input" placeholder="Prospect name (optional)" value={objection.prospect_name} onChange={(e) => setObjection({ ...objection, prospect_name: e.target.value })} />
            <input className="input" placeholder="Company (optional)" value={objection.company} onChange={(e) => setObjection({ ...objection, company: e.target.value })} />
          </div>
          <textarea className="textarea h-20 mb-2" placeholder="Their reply…" value={objection.reply} onChange={(e) => setObjection({ ...objection, reply: e.target.value })} />
          <button onClick={draftObjection} disabled={objectionLoading} className="btn btn-primary">
            {objectionLoading ? "Drafting…" : "Draft objection response"}
          </button>
          {objectionResp && (
            <div className="mt-3 card">
              <div className="font-medium">Subject: {objectionResp.subject}</div>
              <pre className="whitespace-pre-wrap text-sm mt-2 mono">{objectionResp.body}</pre>
              {objectionResp.reasoning && (
                <div className="text-xs text-stone-500 mt-2 italic">Reasoning: {objectionResp.reasoning}</div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
