import { Star } from "lucide-react";

import { GITHUB_URL, LOGIN_URL, SIGNUP_URL } from "@/lib/urls";

export default function Nav() {
  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur border-b hairline">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <a href="/" className="flex items-center gap-2.5">
          <span
            className="inline-flex items-center justify-center w-7 h-7 rounded-lg text-white font-bold text-[13px]"
            style={{ background: "#0c0e16" }}
          >
            S
          </span>
          <span className="font-semibold text-[15px] tracking-tight">
            OpenSales
          </span>
        </a>

        <nav className="hidden md:flex items-center gap-7 text-sm text-stone-500">
          <a href="#product" className="hover:text-ink transition">Product</a>
          <a href="#how" className="hover:text-ink transition">How it works</a>
          <a href="#trace" className="hover:text-ink transition">Trace</a>
          <a href="#pricing" className="hover:text-ink transition">Pricing</a>
          <a
            href={`${GITHUB_URL}#readme`}
            target="_blank"
            rel="noreferrer"
            className="hover:text-ink transition"
          >
            Docs
          </a>
        </nav>

        <div className="flex items-center gap-2">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="pill hidden sm:inline-flex gap-1.5 hover:bg-stone-50 transition"
          >
            <Star size={12} strokeWidth={2.25} />
            <span className="mono">github</span>
          </a>
          <a
            href={LOGIN_URL}
            target="_blank"
            rel="noreferrer"
            className="btn btn-ghost"
          >
            Sign in
          </a>
          <a
            href={SIGNUP_URL}
            target="_blank"
            rel="noreferrer"
            className="btn btn-primary"
          >
            Get started
          </a>
        </div>
      </div>
    </header>
  );
}
