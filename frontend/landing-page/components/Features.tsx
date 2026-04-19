import {
  Target,
  Linkedin,
  Mail,
  Send,
  Sheet,
  Activity,
} from "lucide-react";

const features = [
  {
    icon: Target,
    title: "Decision-maker discovery",
    desc: "Crustdata finds the right buyer titles at matched companies — not a firehose of random contacts.",
  },
  {
    icon: Linkedin,
    title: "LinkedIn signal extraction",
    desc: "Apify scrapes fresh posts, job changes, funding mentions. Cached 24h so you don't burn credits.",
  },
  {
    icon: Mail,
    title: "Personalized cold emails",
    desc: "Every draft quotes a real recent post or event. No \"I noticed you're in SaaS\" slop.",
  },
  {
    icon: Send,
    title: "Real sends via SendGrid",
    desc: "Approve drafts in-app, then route through your own SendGrid key. Status, message IDs, and errors surface inline.",
  },
  {
    icon: Sheet,
    title: "Google Sheets pipeline",
    desc: "Every prospect lands in a sheet with 7 stages — Sourced → Enriched → Drafted → Approved → Sent → Replied → Booked.",
  },
  {
    icon: Activity,
    title: "Full trace UI",
    desc: "Per-step token cost, latency, model, and an expandable view of every prompt and tool call.",
  },
];

export default function Features() {
  return (
    <section id="product" className="bg-white border-y hairline">
      <div className="max-w-6xl mx-auto px-6 py-20 md:py-24">
        <div className="max-w-2xl mb-10">
          <span className="label">What you get</span>
          <h2 className="mt-2 text-[32px] md:text-[40px] font-semibold tracking-tightest leading-[1.1]">
            Everything outbound needs. Nothing it doesn&apos;t.
          </h2>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.title} className="card card-hover">
                <div
                  className="w-9 h-9 rounded-md inline-flex items-center justify-center mb-4"
                  style={{ background: "#dff5e8", color: "#0a7c4a" }}
                >
                  <Icon size={18} strokeWidth={2} />
                </div>
                <h3 className="text-[16px] font-semibold tracking-tight">
                  {f.title}
                </h3>
                <p className="mt-1.5 text-[14px] text-stone-500 leading-relaxed">
                  {f.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
