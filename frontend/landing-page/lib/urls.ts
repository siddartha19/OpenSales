// Single source of truth for outbound links from the marketing site to
// the actual product app.
//
// The landing page is deployed separately (Render static site) from the
// product app (Next.js dev server / ngrok / Render web service). So we
// can't use relative URLs — we need an absolute URL to the app host.
//
// Set NEXT_PUBLIC_APP_URL at build time on Render. In dev, it falls back
// to http://localhost:3000 which is where `npm run dev` in /frontend
// (the product app) listens.
//
// IMPORTANT: NEXT_PUBLIC_* env vars are inlined at BUILD time, so changing
// the value requires a rebuild. Don't include a trailing slash.

const RAW = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";
export const APP_URL = RAW.replace(/\/+$/, "");

export const LOGIN_URL = `${APP_URL}/login`;
export const SIGNUP_URL = `${APP_URL}/signup`;

export const GITHUB_URL = "https://github.com/siddartha19/SalesOS";

// Enterprise contact. Set NEXT_PUBLIC_ENTERPRISE_CONTACT_URL on Render to a
// Cal.com link, Tally form, or mailto:. Defaults to a sensible mailto.
export const ENTERPRISE_CONTACT_URL =
  process.env.NEXT_PUBLIC_ENTERPRISE_CONTACT_URL ||
  "mailto:hello@opensales.dev?subject=OpenSales%20Enterprise%20inquiry";
