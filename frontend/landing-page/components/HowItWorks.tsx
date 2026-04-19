const steps = [
  {
    label: "Step 01",
    title: "VP Sales plans",
    desc: "Reads your ICP and produces a structured campaign brief — segments, sourcing strategy, messaging angles, a target count.",
    snippet: "vp_planning",
    sub: "icp_hash=b41f… segments=3",
  },
  {
    label: "Step 02",
    title: "SDR sources via Exa + Crustdata",
    desc: "Web-wide search, company + decision-maker enrichment, LinkedIn signal extraction via Apify with a 24h cache.",
    snippet: "sdr_shortlist",
    sub: "fit≥0.75 → 8 prospects",
  },
  {
    label: "Step 03",
    title: "AE drafts personalized emails",
    desc: "Every draft quotes a real, recent signal — not generic mad-libs. You review, edit, approve. Then send via SendGrid.",
    snippet: "ae_personalize",
    sub: "hook=\"Series-A post Mar 12\"",
  },
];

export default function HowItWorks() {
  return (
    <section id="how" className="max-w-6xl mx-auto px-6 py-20 md:py-24">
      <div className="max-w-2xl mb-10">
        <span className="label">How it works</span>
        <h2 className="mt-2 text-[32px] md:text-[40px] font-semibold tracking-tightest leading-[1.1]">
          Three agents. One coherent pipeline.
        </h2>
        <p className="mt-3 text-stone-500 text-[15px] leading-relaxed">
          Built on a LangGraph supervisor. Each agent hands off clean state,
          writes its reasoning to a trace, and can be re-run independently.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {steps.map((s) => (
          <div key={s.title} className="card card-hover">
            <div className="label">{s.label}</div>
            <h3 className="mt-2 text-[19px] font-semibold tracking-tight leading-snug">
              {s.title}
            </h3>
            <p className="mt-2 text-[14px] text-stone-500 leading-relaxed">
              {s.desc}
            </p>
            <div className="mt-5 pt-4 border-t hairline mono text-[12px] flex items-center gap-2.5">
              <span className="text-stone-400">›</span>
              <span className="text-accent font-semibold">{s.snippet}</span>
              <span className="text-stone-500 truncate">{s.sub}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
