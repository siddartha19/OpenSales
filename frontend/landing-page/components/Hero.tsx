import { Play, Github, Copy } from "lucide-react";

import { GITHUB_URL, SIGNUP_URL } from "@/lib/urls";

export default function Hero() {
  return (
    <section className="max-w-5xl mx-auto px-6 pt-20 pb-16 md:pt-24 md:pb-20 text-center">
      <span className="pill pill-accent mb-7">
        <span className="mono text-[10.5px] tracking-wide">
          Open source · MIT · Built for India&apos;s first OpenCode Buildathon
        </span>
      </span>

      <h1 className="text-[44px] sm:text-[56px] md:text-[64px] font-bold tracking-tightest leading-[1.04] text-ink">
        Your AI sales team that
        <br className="hidden sm:block" /> runs outbound end-to-end.
      </h1>

      <p className="mt-6 mx-auto max-w-2xl text-[17px] md:text-[18px] leading-[1.55] text-stone-500">
        Paste an ICP. A VP-of-Sales agent plans the campaign, an SDR sources
        prospects, an AE drafts personalized cold emails using fresh LinkedIn
        signal. You approve. They send. Every step is traced.
      </p>

      <div className="mt-8 flex items-center justify-center gap-2.5 flex-wrap">
        <a
          href={SIGNUP_URL}
          target="_blank"
          rel="noreferrer"
          className="btn btn-primary"
        >
          <Play size={14} strokeWidth={2.5} fill="currentColor" />
          Run a campaign
        </a>
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noreferrer"
          className="btn"
        >
          <Github size={14} strokeWidth={2.25} />
          View on GitHub
        </a>
      </div>

      <div className="mt-6 inline-flex items-center gap-3 px-3 py-1.5 rounded-md border hairline bg-white mono text-[13px] text-stone-500">
        <span className="text-accent">$</span>
        <span className="text-ink">git clone github.com/siddartha19/SalesOS</span>
        <button
          aria-label="Copy"
          className="text-stone-400 hover:text-ink transition"
          type="button"
        >
          <Copy size={13} />
        </button>
      </div>

      {/* Hero visual — dashboard terminal card */}
      <div className="mt-14 max-w-4xl mx-auto">
        <TerminalCard />
      </div>
    </section>
  );
}

function TerminalCard() {
  const lines: { n: string; event: string; payload: string }[] = [
    { n: "01", event: "vp_planning", payload: "icp=\"YC seed founders, SF, $1–5M ARR\" target_count=8" },
    { n: "02", event: "vp_plan_ready", payload: "segments=3 icp_hash=b41f…" },
    { n: "03", event: "sdr_search.exa", payload: "query=\"founder + outbound + SF\" n=24" },
    { n: "04", event: "sdr_enrich.crustdata", payload: "matched=18 decision_makers=11" },
    { n: "05", event: "sdr_signal.apify", payload: "linkedin_scrape cache_hit=4/11" },
    { n: "06", event: "sdr_shortlist", payload: "fit≥0.75 → 8 prospects" },
    { n: "07", event: "ae_draft", payload: "prospect=maya@flux.ai subject_variants=2" },
    { n: "08", event: "ae_personalize", payload: "hook=\"Series-A post Mar 12\"" },
    { n: "09", event: "awaiting_approval", payload: "drafts=8 est_tokens=41.2k cost=$0.18" },
  ];

  return (
    <div className="card p-0 text-left overflow-hidden">
      {/* window chrome */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b hairline bg-[#fafaf7]">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#e6e4dc]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#e6e4dc]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#e6e4dc]" />
        </div>
        <span className="mono text-[11px] text-stone-500">
          opensales · session_8a2f · live activity
        </span>
        <span className="pill pill-accent mono text-[10px]">running</span>
      </div>

      <div className="px-5 py-4 mono text-[12.5px] leading-[1.9] bg-white">
        {lines.map((l, i) => (
          <div
            key={l.n}
            className={`flex items-start gap-3 ${
              i === lines.length - 1 ? "cursor-blink" : ""
            }`}
          >
            <span className="text-stone-400 tabular-nums select-none">{l.n}.</span>
            <span className="text-accent font-semibold shrink-0">{l.event}</span>
            <span className="text-stone-500 truncate">{l.payload}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
