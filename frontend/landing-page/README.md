# OpenSales — Landing Page

Marketing site for [OpenSales](https://github.com/siddartha19/SalesOS) — an open-source,
multi-agent AI sales team that runs outbound end-to-end.

Built with Next.js 14 (App Router), Tailwind, Inter (next/font/google), and lucide-react.
The design system matches the product dashboard exactly (warm off-white paper, deep ink,
forest-green accent, 1px hairlines, no shadows beyond a 1px line).

## Develop

```bash
cd frontend/landing-page
npm install
npm run dev        # http://localhost:3001
```

## Build

```bash
npm run build
npm run start
```

## Deploy on Render

A `render.yaml` is included. Push to GitHub and point Render at this repo —
it will auto-detect the blueprint. Or create a new Web Service manually:

- **Root directory**: `frontend/landing-page`
- **Build command**: `npm install && npm run build`
- **Start command**: `npm run start`
- **Environment**: `NODE_VERSION=20`

Render provides the `PORT` env var; the `start` script reads it automatically.

## Links

- Repo: https://github.com/siddartha19/SalesOS
- Login (Get started / Sign in): `/login` on the same deployment

## Sections

1. Sticky nav with GitHub + Sign in / Get started
2. Hero with tagline, subhead, CTAs, npx snippet, terminal dashboard preview
3. Social proof strip (Exa · Crustdata · Apify · SendGrid · LangGraph · OpenCode)
4. How it works — VP Sales, SDR, AE
5. What you get — 6-card feature grid
6. Full dashboard preview (sidebar, ICP input, live activity, prospects)
7. Built for founders + pull quote
8. Pricing — Free, MIT, self-host
9. Footer — Product / Resources / Community / Legal
