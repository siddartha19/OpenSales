import { Github, BookOpen, Building2, ArrowRight } from "lucide-react";

import { GITHUB_URL, ENTERPRISE_CONTACT_URL } from "@/lib/urls";

type Tier = {
  id: string;
  name: string;
  tagline: string;
  price: string;
  priceSuffix: string;
  pill: { label: string; accent?: boolean };
  perks: string[];
  cta: {
    primary: { label: string; href: string; icon: React.ReactNode };
    secondary?: { label: string; href: string; icon: React.ReactNode };
  };
  highlight?: boolean;
};

const tiers: Tier[] = [
  {
    id: "self-host",
    name: "Self-host",
    tagline: "Run it on your machine. MIT licensed.",
    price: "$0",
    priceSuffix: "/ forever",
    pill: { label: "MIT · open-source", accent: true },
    perks: [
      "Self-host on any machine",
      "Bring your own API keys",
      "No SaaS lock-in, no seat fees",
      "No data leaves your environment",
    ],
    cta: {
      primary: {
        label: "Clone the repo",
        href: GITHUB_URL,
        icon: <Github size={14} strokeWidth={2.25} />,
      },
      secondary: {
        label: "Read the docs",
        href: `${GITHUB_URL}#readme`,
        icon: <BookOpen size={14} strokeWidth={2.25} />,
      },
    },
  },
  {
    id: "enterprise",
    name: "Enterprise",
    tagline: "For teams running outbound at scale.",
    price: "Custom",
    priceSuffix: "",
    pill: { label: "Talk to founder" },
    perks: [
      "Unlimited prospects & sends",
      "Dedicated cloud or on-prem deploy",
      "SSO, audit logs, custom roles",
      "Custom agents for your workflow",
      "Slack channel + priority support",
    ],
    cta: {
      primary: {
        label: "Contact sales",
        href: ENTERPRISE_CONTACT_URL,
        icon: <Building2 size={14} strokeWidth={2.25} />,
      },
    },
  },
];

function Check() {
  return (
    <span
      className="mt-0.5 inline-flex w-4 h-4 rounded-full items-center justify-center shrink-0"
      style={{ background: "#dff5e8", color: "#0a7c4a" }}
    >
      <svg width="9" height="9" viewBox="0 0 10 10" fill="none" aria-hidden>
        <path
          d="M1.5 5.2L4 7.5L8.5 2.5"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}

function TierCard({ tier }: { tier: Tier }) {
  const cardClass = tier.highlight
    ? "card p-7 md:p-8 relative flex flex-col"
    : "card p-7 md:p-8 flex flex-col";

  const cardStyle = tier.highlight
    ? {
        borderColor: "#0a7c4a",
        boxShadow:
          "0 0 0 1px #0a7c4a, 0 8px 24px -12px rgba(10, 124, 74, 0.25)",
      }
    : undefined;

  return (
    <div className={cardClass} style={cardStyle}>
      {tier.highlight && (
        <div
          className="absolute -top-3 left-1/2 -translate-x-1/2 px-2.5 py-0.5 text-[11px] mono font-semibold rounded-full text-white"
          style={{ background: "#0a7c4a" }}
        >
          {tier.pill.label}
        </div>
      )}

      <div>
        <h3 className="text-[18px] font-semibold tracking-tight">{tier.name}</h3>
        <p className="mt-1 text-stone-500 text-[13.5px] leading-relaxed">
          {tier.tagline}
        </p>
      </div>

      <div className="mt-5 inline-flex items-baseline gap-1.5">
        <span className="text-[40px] font-bold tracking-tightest leading-none">
          {tier.price}
        </span>
        {tier.priceSuffix && (
          <span className="text-stone-500 text-[13px] mono">
            {tier.priceSuffix}
          </span>
        )}
      </div>

      {!tier.highlight && (
        <div
          className={`mt-3 pill mono text-[11px] ${
            tier.pill.accent ? "pill-accent" : ""
          }`}
        >
          {tier.pill.label}
        </div>
      )}

      <ul className="mt-6 space-y-2.5 text-left">
        {tier.perks.map((p) => (
          <li key={p} className="flex items-start gap-2.5 text-[14px]">
            <Check />
            <span>{p}</span>
          </li>
        ))}
      </ul>

      <div className="mt-auto pt-7 flex flex-col gap-2">
        <a
          href={tier.cta.primary.href}
          target={tier.cta.primary.href.startsWith("http") ? "_blank" : undefined}
          rel="noreferrer"
          className={`btn ${tier.highlight ? "btn-primary" : ""} justify-center`}
        >
          {tier.cta.primary.icon}
          {tier.cta.primary.label}
          {tier.highlight && <ArrowRight size={14} strokeWidth={2.25} />}
        </a>
        {tier.cta.secondary && (
          <a
            href={tier.cta.secondary.href}
            target={
              tier.cta.secondary.href.startsWith("http") ? "_blank" : undefined
            }
            rel="noreferrer"
            className="btn btn-ghost justify-center"
          >
            {tier.cta.secondary.icon}
            {tier.cta.secondary.label}
          </a>
        )}
      </div>
    </div>
  );
}

export default function Pricing() {
  return (
    <section id="pricing" className="max-w-6xl mx-auto px-6 py-20 md:py-24">
      <div className="max-w-2xl mx-auto text-center mb-12">
        <span className="label">Pricing</span>
        <h2 className="mt-2 text-[32px] md:text-[40px] font-semibold tracking-tightest leading-[1.1]">
          Self-host it free. Or go Enterprise.
        </h2>
        <p className="mt-3 text-stone-500 text-[15px] leading-relaxed">
          OpenSales is open source. Talk to us when you need a dedicated
          deploy, SSO, and bespoke agents for your team.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-5 md:gap-6 items-stretch max-w-3xl mx-auto">
        {tiers.map((tier) => (
          <TierCard key={tier.id} tier={tier} />
        ))}
      </div>

      <p className="mt-8 text-center text-[12.5px] text-stone-500">
        Both plans use your own LLM and data-source API keys. No markup on
        tokens or credits.
      </p>
    </section>
  );
}
