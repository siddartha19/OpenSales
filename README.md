# OpenSales

> Your AI sales team that runs outbound end-to-end.

A multi-agent outbound sales system. Paste an ICP. A VP-of-Sales agent plans the campaign, an SDR agent finds target companies and decision-makers, an AE agent enriches contacts and writes personalized cold emails using fresh signal from LinkedIn and the open web. You review the drafts and click send. Every prospect lands in a Google Sheet pipeline. Every agent step is traced with token cost and latency.


```
┌─────────────────────────────────────────────────────────────┐
│  ICP in. Pipeline out. 3 agents. Real emails. Full trace.  │
└─────────────────────────────────────────────────────────────┘
```

---

## Why OpenSales

Outbound sales is one of the most expensive functions a startup runs. A single SDR today costs $6k–$1 K lakhs/year. Most early-stage founders do it themselves and lose 10-15 hours a week to prospecting and writing cold emails. The work is real, the work is repetitive, and the work is exactly what AI agents can now do well.

OpenSales replaces the SDR + AE pair with two specialist agents and a manager that reviews their output. It works on real public data (LinkedIn, web search, B2B people databases) and sends real emails through real transports. No simulated paths anywhere.

The whole thing runs locally. You ship outbound from your own machine, with your own SendGrid sender, your own pipeline sheet, and your own LLM key. No SaaS lock-in.

---

## What it does

- **Discover companies** matching your ICP via Exa neural search.
- **Find decision-makers** at each company via Crustdata's people search.
- **Enrich contacts** with verified emails and rich profile data via Crustdata.
- **Pull LinkedIn signal** (About section, recent posts, experience) via Apify, with a 24-hour cache and automatic Exa fallback when the scrape times out.
- **Draft personalized cold emails** that quote something the prospect actually said or did in the last few weeks. No "I hope this email finds you well." No "circling back." A 10-case eval set enforces it.
- **Send via SendGrid** straight from the approval queue, with status, message ID, and any errors surfaced inline.
- **Log to Google Sheets** with a 7-stage pipeline (`Sourced → Researched → Outreach Sent → Replied → Qualified → Demo Booked → Lost`).
- **Trace every agent step** in a custom observability UI: tree view, per-step token cost, expandable prompts, total $ per campaign.
- **Handle objections** when a prospect replies — paste the reply, the AE drafts a non-defensive response in seconds.

---

## Architecture

```
              Next.js Frontend (auth-gated, ngrok-tunneled)
                    /login → /  → /trace/[runId]
                              │
                              ▼
                Next.js API routes proxy to FastAPI
                              │
                              ▼
              ┌───────────────────────────────────┐
              │   VP Sales Agent (Supervisor)     │
              │   parses ICP, plans campaign      │
              │   reviews drafts before send      │
              └─────┬──────────────┬──────────────┘
                    │              │
            ┌───────▼──────┐  ┌────▼──────────────────┐
            │  SDR Agent    │  │      AE Agent          │
            │               │  │                        │
            │ Exa: companies│  │ Crustdata: enrich      │
            │ Crustdata: DMs│  │ Apify: LinkedIn (cached│
            │               │  │   + Exa fallback)      │
            │ Output:       │  │ Exa: web activity      │
            │   prospect    │  │ LLM: draft personalized│
            │   dossier     │  │   cold email           │
            │               │  │ SendGrid: send         │
            │               │  │ Sheets: log + stage    │
            └───────────────┘  └───────┬────────────────┘
                                       │
                            VP reviews + approves send
```

Built on [LangGraph](https://github.com/langchain-ai/langgraph)'s supervisor pattern. The VP delegates to specialists by name. Each specialist has only the tools it needs.

---

## Quick start

### Prerequisites

- Python 3.11+ with [uv](https://github.com/astral-sh/uv)
- Node.js 20+
- ngrok ([download](https://ngrok.com/download)) — only if you want a public URL for the demo
- API keys for: OpenRouter, Crustdata, Exa, Apify, SendGrid
- A Google Cloud service account with Sheets API enabled
- A target Google Sheet, shared with the service account email

### Install

```bash
git clone https://github.com/yourname/opensales.git
cd opensales

# Backend
cd backend
uv sync

# Frontend
cd ../frontend
npm install

# Symlink env
cd frontend && ln -s ../.env .env.local
```

### Configure

Copy `.env.example` to `.env` and fill in your keys:

```bash
# LLM via OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...
LLM_MODEL=google/gemini-2.0-flash-001

# People sourcing
CRUSTDATA_API_KEY=...

# Web signal
EXA_API_KEY=...

# LinkedIn enrichment (cached 24h)
APIFY_API_TOKEN=apify_api_...
APIFY_LINKEDIN_ACTOR_ID=apify~linkedin-profile-scraper

# Outreach
SENDGRID_API_KEY=SG...
SENDGRID_FROM_EMAIL=you@yourdomain.com
SENDGRID_FROM_NAME=Your Name

# Pipeline
GOOGLE_SHEET_ID=1abc...xyz
GOOGLE_SERVICE_ACCOUNT_JSON=./service_account.json

# Auth (hardcoded credential pair for demo)
AUTH_EMAIL=hr@yourdomain.com
AUTH_PASSWORD=ChangeMe123
AUTH_SECRET=$(openssl rand -hex 32)
```

### Run

Three terminals:

```bash
# Terminal 1: FastAPI backend
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Terminal 2: Next.js frontend
cd frontend && npm run dev

# Terminal 3 (optional): public URL via ngrok
ngrok http 3000
```

Open [http://localhost:3000](http://localhost:3000) (or your ngrok URL). Login with `AUTH_EMAIL` / `AUTH_PASSWORD`. Paste an ICP. Hit Run.

### Pre-warm the LinkedIn cache (optional, for demo)

Apify LinkedIn scrapes take 10-30 seconds. For a smooth demo, pre-scrape your known prospects:

```bash
cd backend
uv run python scripts/prewarm.py
```

Edit the `DEMO_RECIPIENTS` list in `prewarm.py` first.

---

## Usage

### Web UI

1. Login.
2. Paste an ICP. Example: *"Indian AI startup founders, Series A or earlier, raised in 2024-2025, building agent products."*
3. Click **Run sales team**.
4. Watch live activity. SDR returns 8 prospect cards in ~10 seconds.
5. Select 3 prospects. Click **Draft outreach**.
6. AE drafts personalized emails (cached LinkedIn = ~2s, live = ~25s).
7. Review each draft. Edit if needed. Click **Approve & Send**.
8. Check the Google Sheet. Open the trace UI to see exactly what each agent did and what it cost.

### CLI

```bash
cd backend
uv run python -m app.cli "Indian AI startup founders, Series A, building agent products"
```

### Objection handling

Paste a reply into the objection box. AE drafts a response that addresses the concern without being defensive. Common cases handled: "we already use X", "not the right time", "send me more info", "remove me from your list."

---

## Tech stack


| Layer            | Tech                                        | Why                                                                                       |
| ---------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Agent runtime    | [LangGraph](https://github.com/langchain-ai/langgraph) + `langgraph-supervisor` | Battle-tested supervisor pattern, persistent memory via `MemorySaver`.                    |
| LLM              | [OpenRouter](https://openrouter.ai) → Gemini 2.0 Flash | $0.10/$0.40 per 1M tokens. Fast tool-calling. Switch model with one env var.   |
| Company discovery| [Exa](https://exa.ai)                       | Neural search across the open web. Finds companies Crustdata can't.                       |
| People search    | [Crustdata](https://crustdata.com)          | Purpose-built for B2B people search. Filters, autocomplete, enrich.                       |
| LinkedIn data    | [Apify](https://apify.com) + SQLite cache   | Rich LinkedIn profiles + recent posts. Cached 24h. Falls back to Exa on timeout/failure.  |
| Email            | [SendGrid](https://sendgrid.com)            | Reliable, free tier covers 100 emails/day. Live sends via your own sender domain.         |
| Pipeline         | Google Sheets API                           | Mentor-visible artifact. Familiar to every salesperson alive.                             |
| Observability    | SQLite + custom React tree view             | Trace tree, per-step token + cost, expandable prompts. ~30KB, no external service.        |
| Backend          | FastAPI + Pydantic + uv                     | Async-native, fast cold start, modern Python tooling.                                     |
| Frontend         | Next.js 14 (App Router) + Tailwind          | One framework for UI + API proxy. Server-side env handling for keys.                      |
| Auth             | HMAC-signed httpOnly cookie + middleware    | 50 lines of code. No NextAuth, no Clerk.                                                  |
| Hosting          | Local + ngrok                               | Run on your own machine. ngrok tunnel for public demo URL.                                |


---

## Repo layout

```
opensales/
  .env                    # Shared, gitignored
  .gitignore
  backend/
    pyproject.toml
    app/
      main.py             # FastAPI entrypoint
      config.py
      models.py
      agent.py            # LangGraph supervisor + agents
      cli.py              # python -m app.cli "..."
      services/
        crustdata.py
        exa.py
        apify.py          # LinkedIn scrape + cache + fallback
        email.py
        sheets.py
        observability.py  # SQLite logger + LangGraph callback
    evals/
      cold_email_quality.json
      run.py
    scripts/
      prewarm.py
  frontend/
    middleware.ts         # Auth gate
    app/
      layout.tsx
      page.tsx            # Management UI
      login/page.tsx
      trace/[runId]/page.tsx
      api/
        auth/login/route.ts
        auth/logout/route.ts
        chat/route.ts
        runs/route.ts
        runs/[id]/route.ts
    lib/
      auth.ts             # HMAC sign/verify
    components/
```

---

## Eval

Cold email quality is enforced by a 10-case eval set in `backend/evals/cold_email_quality.json`. Each case defines must-include patterns (specific quote from prospect activity, under 100 words, specific subject) and anti-patterns ("I hope this email finds you well", "circling back", emoji on a non-emoji prospect).

Run:

```bash
cd backend
uv run python -m evals.run
```

Output: pass/fail per case, % pass, flagged anti-patterns. Run before and after every prompt change.

---

## Roadmap

Things this v0 does NOT do, and roughly when they'd land:

- [ ] **Real reply handling via SendGrid Inbound Parse webhooks.** Currently you paste replies manually.
- [ ] **Multi-channel outreach** (LinkedIn DM, WhatsApp). Email-only today.
- [ ] **Follow-up sequences** (day 3, day 7 nudges).
- [ ] **Sales Engineer agent** for technical discovery questions.
- [ ] **CSM agent** for post-deal handoff and onboarding.
- [ ] **Multi-user / role-based access.** Hardcoded single-user auth today.
- [ ] **Production deployment** (Fly.io / Render / Vercel split).
- [ ] **A/B testing** of subject lines via the eval pipeline.
- [ ] **Reply tracking** + auto-stage transitions in the pipeline sheet.
- [ ] **Calendar integration** for "book a demo" flow.

PRs welcome. Pick a checkbox.

---

## Design choices worth knowing

A few non-obvious calls in the v0:

- **Apify is wrapped in a cache + fallback.** LinkedIn scrapers are slow (10-30s) and unreliable (~20% failure). The `apify.py` service caches 24h and falls back to Exa on timeout. The trace UI shows source (`apify_cache` vs `apify_live` vs `exa_fallback`) so you always know where signal came from.
- **Custom observability beats wiring Langfuse.** SQLite + a React tree view ships in 90 minutes and gets you the same diagnostic power. No vendor lock-in, no auth setup, no separate dashboard.
- **The VP agent reviews drafts before send.** Not just for safety. The review step is what stops AI slop. If a draft has any anti-pattern, the VP sends it back to the AE with feedback.
- **Every send is reviewed before it goes out.** The VP agent and the human-in-the-loop approval queue both gate the SendGrid call. No background blasts.
- **One LLM provider.** OpenRouter fronts ~50 models with one API key, one billing dashboard, one SDK. Swap models with one env var without rewriting agent code.


## License

MIT. Use it. Sell it. Modify it. Just don't blame me when SendGrid suspends your account for sending 10,000 cold emails on day one.

---

## Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for the supervisor pattern that made the multi-agent build tractable.
- [Crustdata](https://crustdata.com) for the people search API that actually works for India.
- [Exa](https://exa.ai) for neural web search that returns useful results, not SEO sludge.
- [Apify](https://apify.com) for keeping LinkedIn data accessible.
- [GrowthX](https://growthx.club) for running the buildathon and the rubric that forced every design choice in this repo.
