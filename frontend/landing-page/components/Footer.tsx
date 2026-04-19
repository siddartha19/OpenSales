import { Github, Twitter, Linkedin } from "lucide-react";

import { GITHUB_URL } from "@/lib/urls";

const columns = [
  {
    heading: "Product",
    links: [
      { label: "How it works", href: "#how" },
      { label: "Features", href: "#product" },
      { label: "Trace", href: "#trace" },
      { label: "Pricing", href: "#pricing" },
    ],
  },
  {
    heading: "Resources",
    links: [
      { label: "Docs", href: `${GITHUB_URL}#readme` },
      { label: "Quickstart", href: `${GITHUB_URL}#quickstart` },
      { label: "Changelog", href: `${GITHUB_URL}/releases` },
      { label: "Roadmap", href: `${GITHUB_URL}/issues` },
    ],
  },
  {
    heading: "Community",
    links: [
      { label: "GitHub", href: GITHUB_URL },
      { label: "Discussions", href: `${GITHUB_URL}/discussions` },
      { label: "Issues", href: `${GITHUB_URL}/issues` },
      { label: "Contribute", href: `${GITHUB_URL}/blob/main/CONTRIBUTING.md` },
    ],
  },
  {
    heading: "Legal",
    links: [
      { label: "MIT License", href: `${GITHUB_URL}/blob/main/LICENSE` },
      { label: "Privacy", href: "#" },
      { label: "Terms", href: "#" },
      { label: "Security", href: "#" },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="bg-white border-t hairline">
      <div className="max-w-6xl mx-auto px-6 pt-14 pb-8">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2.5">
              <span
                className="inline-flex items-center justify-center w-7 h-7 rounded-lg text-white font-bold text-[13px]"
                style={{ background: "#0c0e16" }}
              >
                S
              </span>
              <span className="font-semibold text-[15px] tracking-tight">
                OpenSales
              </span>
            </div>
            <p className="mt-3 text-[13px] text-stone-500 leading-relaxed max-w-[230px]">
              Your AI sales team that runs outbound end-to-end.
            </p>
          </div>
          {columns.map((col) => (
            <div key={col.heading}>
              <div className="label mb-3">{col.heading}</div>
              <ul className="space-y-2">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      target={l.href.startsWith("http") ? "_blank" : undefined}
                      rel={l.href.startsWith("http") ? "noreferrer" : undefined}
                      className="text-[13.5px] text-stone-500 hover:text-ink transition"
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-5 border-t hairline flex items-center justify-between flex-wrap gap-3">
          <span className="text-[12.5px] text-stone-500 mono">
            © 2026 OpenSales · MIT
          </span>
          <div className="flex items-center gap-1">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              aria-label="GitHub"
              className="w-8 h-8 inline-flex items-center justify-center rounded-md text-stone-500 hover:bg-stone-50 hover:text-ink transition"
            >
              <Github size={15} />
            </a>
            <a
              href="https://x.com/gcs319"
              target="_blank"
              rel="noreferrer"
              aria-label="Twitter"
              className="w-8 h-8 inline-flex items-center justify-center rounded-md text-stone-500 hover:bg-stone-50 hover:text-ink transition"
            >
              <Twitter size={15} />
            </a>
            <a
              href="https://www.linkedin.com/in/siddartha19"
              target="_blank"
              rel="noreferrer"
              aria-label="LinkedIn"
              className="w-8 h-8 inline-flex items-center justify-center rounded-md text-stone-500 hover:bg-stone-50 hover:text-ink transition"
            >
              <Linkedin size={15} />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
