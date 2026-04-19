import { Plus, Search, Play } from "lucide-react";

const sessions = [
  { name: "YC seed founders · SF", time: "2m ago", active: true },
  { name: "DevTools Series-A", time: "1h ago" },
  { name: "Fintech CFOs · NYC", time: "yesterday" },
  { name: "AI infra startups", time: "3d ago" },
];

const prospects = [
  { name: "Maya Chen", title: "CEO, Flux.ai", fit: 92, hook: "Series-A · Mar 12" },
  { name: "David Park", title: "Founder, Loop", fit: 87, hook: "Hiring 3 AEs" },
  { name: "Priya Shah", title: "CEO, Sondr", fit: 84, hook: "Posted re: outbound" },
  { name: "Tom Weiss", title: "CTO, Relay", fit: 81, hook: "Launched v2 · Apr 01" },
];

const activity = [
  { n: "14", ev: "sdr_enrich.crustdata", p: "matched=18 dm=11" },
  { n: "15", ev: "sdr_signal.apify", p: "cache_hit=4/11" },
  { n: "16", ev: "sdr_shortlist", p: "fit≥0.75 → 8" },
  { n: "17", ev: "ae_draft", p: "maya@flux.ai" },
  { n: "18", ev: "ae_personalize", p: "hook=Series-A post" },
];

export default function DashboardPreview() {
  return (
    <section id="trace" className="max-w-6xl mx-auto px-6 py-20 md:py-24">
      <div className="max-w-2xl mb-10">
        <span className="label">Inside the product</span>
        <h2 className="mt-2 text-[32px] md:text-[40px] font-semibold tracking-tightest leading-[1.1]">
          A dashboard built like a terminal.
        </h2>
        <p className="mt-3 text-stone-500 text-[15px] leading-relaxed">
          Define your ICP on the left. Watch the agents work on the right.
          Approve drafts before anything sends.
        </p>
      </div>

      <div className="card p-0 overflow-hidden">
        {/* window chrome */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b hairline bg-[#fafaf7]">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#e6e4dc]" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#e6e4dc]" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#e6e4dc]" />
          </div>
          <span className="mono text-[11px] text-stone-500">
            app.opensales.dev / sessions / 8a2f
          </span>
          <span className="pill mono text-[10px]">live</span>
        </div>

        <div className="grid grid-cols-12 min-h-[520px]">
          {/* Sidebar */}
          <aside className="col-span-12 md:col-span-3 border-b md:border-b-0 md:border-r hairline bg-[#fafaf7] p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="label">Sessions</span>
              <button className="text-stone-500 hover:text-ink transition" aria-label="New">
                <Plus size={14} />
              </button>
            </div>
            <div className="relative mb-3">
              <Search
                size={13}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-stone-400"
              />
              <input
                placeholder="Search"
                className="w-full pl-7 pr-2 py-1.5 text-[13px] rounded-md border hairline bg-white outline-none"
                readOnly
              />
            </div>
            <ul className="space-y-1">
              {sessions.map((s) => (
                <li
                  key={s.name}
                  className={`px-2.5 py-2 rounded-md text-[13px] cursor-default ${
                    s.active
                      ? "bg-white border hairline"
                      : "hover:bg-white"
                  }`}
                >
                  <div className="font-medium text-ink truncate">{s.name}</div>
                  <div className="text-[11px] text-stone-500 mt-0.5 mono">
                    {s.time}
                  </div>
                </li>
              ))}
            </ul>
          </aside>

          {/* Main */}
          <main className="col-span-12 md:col-span-9 p-5 md:p-6 space-y-5">
            {/* ICP textarea */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="label">Define your ICP</label>
                <span className="mono text-[11px] text-stone-500">
                  target_count · 8
                </span>
              </div>
              <div className="rounded-md border hairline bg-white p-3 mono text-[13px] text-ink leading-relaxed">
                YC seed-stage B2B founders in SF, $1–5M ARR, hiring their first
                AEs, posted about outbound in the last 30 days.
                <span className="inline-block w-px h-3.5 bg-ink ml-0.5 align-middle animate-pulse" />
              </div>
              <div className="mt-3 flex items-center gap-2">
                <button className="btn btn-primary">
                  <Play size={13} strokeWidth={2.5} fill="currentColor" />
                  Run agents
                </button>
                <button className="btn">Save ICP</button>
                <span className="ml-auto mono text-[11px] text-stone-500">
                  est. tokens 41.2k · $0.18
                </span>
              </div>
            </div>

            {/* Two column: activity + prospects */}
            <div className="grid md:grid-cols-2 gap-4">
              <div className="rounded-md border hairline bg-[#0c0e16] text-white overflow-hidden">
                <div className="px-3 py-2 border-b border-white/10 flex items-center justify-between">
                  <span className="label" style={{ color: "#a9a497" }}>
                    Live activity
                  </span>
                  <span className="mono text-[10px] text-[#dff5e8]">● running</span>
                </div>
                <div className="px-3 py-2.5 mono text-[11.5px] leading-[1.85]">
                  {activity.map((a, i) => (
                    <div
                      key={a.n}
                      className={`flex items-start gap-2.5 ${
                        i === activity.length - 1 ? "cursor-blink" : ""
                      }`}
                    >
                      <span className="text-[#555148] tabular-nums">{a.n}.</span>
                      <span className="text-[#3ddc97] font-semibold shrink-0">
                        {a.ev}
                      </span>
                      <span className="text-[#a9a497] truncate">{a.p}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-md border hairline bg-white overflow-hidden">
                <div className="px-3 py-2 border-b hairline flex items-center justify-between">
                  <span className="label">Prospects</span>
                  <span className="mono text-[11px] text-stone-500">8 / 8</span>
                </div>
                <ul className="divide-y hairline">
                  {prospects.map((p) => (
                    <li key={p.name} className="px-3 py-2.5 flex items-center gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="text-[13px] font-medium truncate">
                          {p.name}
                        </div>
                        <div className="text-[11.5px] text-stone-500 truncate">
                          {p.title} · <span className="mono">{p.hook}</span>
                        </div>
                      </div>
                      <span className="pill pill-accent mono text-[11px]">
                        {p.fit}% fit
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </main>
        </div>
      </div>
    </section>
  );
}
