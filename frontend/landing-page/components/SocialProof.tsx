export default function SocialProof() {
  const logos = ["Exa", "Crustdata", "Apify", "SendGrid", "LangGraph", "OpenCode"];
  return (
    <section className="border-y hairline bg-white">
      <div className="max-w-5xl mx-auto px-6 py-6 flex flex-col md:flex-row items-center gap-4 md:gap-10 justify-center">
        <span className="label">Powered by</span>
        <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
          {logos.map((l) => (
            <span
              key={l}
              className="text-[13px] font-semibold tracking-tight text-stone-400 hover:text-stone-500 transition"
            >
              {l}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
