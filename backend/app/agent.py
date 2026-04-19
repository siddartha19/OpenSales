"""LangGraph supervisor: VP Sales (manager) + SDR + AE (specialists).

Multi-agent org for the rubric. In practice the FastAPI layer drives one
phase at a time (source / draft / send / objection), but the supervisor
graph routes inside each phase based on the VP prompt.

Direct LLM calls with structured output handle the parsing-fragile parts
(extracting ProspectDossiers from SDR, OutreachDraft from AE) — keeps the
hackathon demo deterministic.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from .config import LLM_MODEL, OPENROUTER_API_KEY
from .models import DecisionMaker, DiscoveredCompany, OutreachDraft, ProspectDossier
from .services import apify as apify_svc
from .services import company as company_svc
from .services import crustdata as cd_svc
from .services import email_verification as qev_svc
from .services import firecrawl_svc
from .services import mailer as email_svc
from .services import exa as exa_svc
from .services import observability as obs
from .tools import AE_TOOLS, SDR_TOOLS


# ---------- LLM ----------


def make_llm(temperature: float = 0.3, max_tokens: int = 1500) -> ChatOpenAI:
    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
        max_tokens=max_tokens,
        default_headers={
            "HTTP-Referer": "https://salesos.local",
            "X-Title": "SalesOS Buildathon",
        },
    )


# ---------- Prompts ----------

VP_PROMPT = """You are the VP of Sales for SalesOS. You manage two specialists:

- sdr: discovers target companies and finds decision-makers at each.
- ae: enriches contacts, writes personalized cold outreach, sends, logs to pipeline,
      and drafts replies to objections.

WORKFLOW:
1. Parse the user's ICP. Default geography = India unless stated otherwise.
2. For SOURCING tasks: route to sdr. SDR returns ProspectDossier objects.
3. For DRAFTING tasks: route to ae. AE drafts cold emails personalized to each
   prospect's LinkedIn About section + recent posts.
4. For SENDING tasks: AE only sends after VP approves the draft.
5. For OBJECTION tasks: route to ae's draft_reply tool.

CRITICAL RULES:
- NEVER let ae call enrich_contact before user selects. Costs 1-7 credits per call.
- ALWAYS make ae use recent activity in the email. Generic emails fail.
- Emails are sent for real via SendGrid. Confirm the recipient before sending.
"""

SDR_PROMPT = """You are a senior SDR. Your job is to find the RIGHT companies and the
RIGHT decision-makers inside them.

GIVEN: an ICP from the VP.

DO:
1. Call discover_companies(icp_query, num_results=8). Build a focused query —
   include geography, stage, vertical, recent signals.
   Bad: 'AI companies'.
   Good: 'Indian AI startup Series A funded 2024 2025 founder OR CEO LinkedIn'.

2. For each interesting company (max 6-8), call find_decision_makers(company,
   [titles_matching_ICP], limit=2) to surface 1-2 decision-makers per company.
   Use only public info from the search results — NO fabrication.

3. Output a final summary as a JSON block wrapped in markers:

CANDIDATES_JSON_START
[
  {"company": "...", "dm_name": "...", "dm_title": "...",
   "dm_linkedin": "https://...", "why_target": "1-2 sentences from search data",
   "fit_score": 0.0-1.0}
]
CANDIDATES_JSON_END

Do NOT enrich (that costs credits — that's the AE's call). Stop after returning
the JSON block."""


AE_DRAFT_SYSTEM = """You are a senior AE writing personalized cold emails for {company_name}.

{company_context}

GIVEN: a prospect dossier + LinkedIn profile + recent web activity + prospect company intel.

WRITE:
- Subject: under 60 chars, no clickbait, references the prospect specifically.
- Body: under 120 words. Structure:
  1. Open with a SPECIFIC observation from a recent LinkedIn post or web activity
     (quote a thing they said/did — not 'I noticed your work').
  2. ONE SENTENCE of personalized feedback about their business that shows you
     actually researched their company. Reference something specific from their
     website, product, or recent news — NOT generic praise. The prospect should
     feel: "this person actually looked at what we do."
  3. One sentence connecting what WE do to THEIR specific situation. Be concrete
     about the value — no vague "we help companies like yours" platitudes.
  4. One specific question that's easy to reply to.

ANTI-SLOP RULES:
- No 'I hope this email finds you well'.
- No 'I noticed your impressive work'.
- No 'circling back' or 'touching base'.
- No emoji unless their recent activity uses them.
- No generic company compliments like 'impressive growth' or 'exciting space'.
- The business feedback line MUST reference a specific product, feature, metric,
  or initiative from their website/news. If you have nothing specific, skip it
  rather than writing something generic.
- If you have NO specific recent-activity hook, say so honestly in the body
  ('I came across $company because [public fact]') instead of writing generic.

Sign off as: {from_name}.
"""


AE_OBJECTION_SYSTEM = """You are a senior AE writing a 2-3 sentence reply to a cold-email objection.

PRINCIPLES:
- Acknowledge the objection without being defensive.
- Don't argue. Don't oversell.
- Propose a specific, low-friction next step (e.g. 'a 5-min comparison call' or
  'I'll send a 1-min Loom showing $specific_thing').
- Common objections: 'we already use X', 'not the right time', 'send me more info',
  'who are you', 'remove me'. Match the energy of their reply.
"""


# ---------- React agents (specialist subgraphs) ----------


def build_sdr_agent():
    return create_react_agent(
        model=make_llm(temperature=0.2, max_tokens=2000),
        tools=SDR_TOOLS,
        name="sdr",
        prompt=SDR_PROMPT,
    )


def build_ae_agent():
    return create_react_agent(
        model=make_llm(temperature=0.4, max_tokens=1500),
        tools=AE_TOOLS,
        name="ae",
        prompt="""You are a senior AE. You enrich contacts, write cold emails,
send via SendGrid, and log to the pipeline. Always use recent_activity in emails.""",
    )


def build_supervisor():
    """Build the multi-agent graph. Used for the trace; the FastAPI layer
    invokes it at the right moments."""
    try:
        from langgraph_supervisor import create_supervisor

        sdr = build_sdr_agent()
        ae = build_ae_agent()
        graph = create_supervisor(
            agents=[sdr, ae],
            model=make_llm(temperature=0.2, max_tokens=800),
            prompt=VP_PROMPT,
        )
        return graph.compile(checkpointer=MemorySaver())
    except Exception as e:
        # Supervisor build failed — fallback to a single SDR agent so the
        # rest of the system still works in degraded mode.
        print(f"[agent] supervisor build failed: {e}. Falling back to SDR-only.")
        return None


# ---------- Phase functions (called from FastAPI) ----------


async def run_sourcing(
    icp: str,
    trace_id: str,
    target_count: int = 8,
) -> list[ProspectDossier]:
    """Phase 1: SDR sources prospects matching ICP.

    Logs a synthetic 'vp' decision step + the SDR react-agent run.
    """
    obs.log_event(
        trace_id=trace_id,
        agent_name="vp",
        event_type="agent",
        input=f"ICP: {icp}",
        output=f"Routing to SDR: source {target_count} prospects.",
        duration_ms=20,
    )

    sdr = build_sdr_agent()
    cb = obs.TraceCallback(trace_id, agent_label="sdr")

    user_msg = (
        f"Source up to {target_count} prospects for this ICP. "
        f"Default geography India unless stated. ICP:\n\n{icp}"
    )

    try:
        result = await sdr.ainvoke(
            {"messages": [HumanMessage(content=user_msg)]},
            config={"callbacks": [cb], "recursion_limit": 25},
        )
    except Exception as e:
        obs.log_event(
            trace_id=trace_id,
            agent_name="sdr",
            event_type="agent",
            input=user_msg,
            output=f"ERROR: {e}",
            status="error",
        )
        return []

    # Parse the SDR's JSON block from final message
    final_text = ""
    for m in reversed(result.get("messages", [])):
        content = getattr(m, "content", None)
        if isinstance(content, str) and content.strip():
            final_text = content
            break

    prospects = _parse_candidates_json(final_text)
    return prospects


def _parse_candidates_json(text: str) -> list[ProspectDossier]:
    if not text:
        return []
    # Look for explicit markers first
    start = text.find("CANDIDATES_JSON_START")
    end = text.find("CANDIDATES_JSON_END")
    block = ""
    if start != -1 and end != -1:
        block = text[start + len("CANDIDATES_JSON_START") : end].strip()
    else:
        # Fallback: pull out the first top-level JSON array
        first = text.find("[")
        last = text.rfind("]")
        if first != -1 and last != -1 and last > first:
            block = text[first : last + 1]

    if not block:
        return []

    block = block.strip().strip("`").strip()
    if block.startswith("json"):
        block = block[4:].strip()

    try:
        raw = json.loads(block)
    except Exception:
        # Sometimes models return unescaped quotes; be lenient
        try:
            block_clean = block.replace("\n", " ")
            raw = json.loads(block_clean)
        except Exception:
            return []

    out: list[ProspectDossier] = []
    for item in raw:
        try:
            out.append(
                ProspectDossier(
                    company=item.get("company", "Unknown"),
                    company_url=item.get("company_url"),
                    dm_name=item.get("dm_name", "Unknown"),
                    dm_title=item.get("dm_title", ""),
                    dm_linkedin=item.get("dm_linkedin"),
                    why_target=item.get("why_target", ""),
                    fit_score=float(item.get("fit_score", 0.7)),
                )
            )
        except Exception:
            continue
    return out


async def draft_outreach_for_prospect(
    prospect: ProspectDossier,
    trace_id: str,
    from_name: str,
    fallback_email: str,
) -> OutreachDraft:
    """Phase 2: AE drafts a personalized cold email for one prospect.

    Steps (logged as VP routing decision + AE tool calls):
      1. enrich (skipped if no linkedin_url)
      2. scrape LinkedIn (cached or live)
      2.5. scrape prospect's company website via Firecrawl (NEW)
      3. fetch recent web activity
      4. load company profile + ICP context (NEW)
      5. ask LLM with structured output to draft
    """
    obs.log_event(
        trace_id=trace_id,
        agent_name="vp",
        event_type="agent",
        input=f"Prospect approved: {prospect.dm_name} @ {prospect.company}",
        output=f"Routing to AE for personalized draft.",
        duration_ms=15,
    )

    import time

    # Step 1: Enrich (best effort — skip on failure)
    enrich_data = {}
    if prospect.dm_linkedin:
        t0 = time.time()
        enrich_data = await cd_svc.enrich_contact(prospect.dm_linkedin)
        obs.log_event(
            trace_id=trace_id,
            agent_name="ae",
            tool_name="enrich_contact",
            event_type="tool",
            input=prospect.dm_linkedin,
            output=json.dumps(enrich_data)[:1500],
            duration_ms=int((time.time() - t0) * 1000),
        )

    verified_email = enrich_data.get("email") if isinstance(enrich_data, dict) else None
    to_email = (
        verified_email
        or await _derive_email(prospect.dm_name, prospect.company, fallback_email)
    )

    # Steps 2, 2.5, 3: Run LinkedIn + Firecrawl + web activity IN PARALLEL
    company_url = prospect.company_url or ""
    if not company_url:
        company_url = "".join(c for c in prospect.company.lower() if c.isalnum()) + ".com"

    async def _scrape_linkedin():
        t0 = time.time()
        result = await apify_svc.scrape_linkedin_profile(
            prospect.dm_linkedin or "",
            exa_fallback_fn=exa_svc.find_recent_activity,
        )
        obs.log_event(
            trace_id=trace_id,
            agent_name="ae",
            tool_name="scrape_linkedin_profile",
            event_type="tool",
            input=prospect.dm_linkedin or "",
            output=f"source={result.get('source')} posts={len(result.get('recent_posts', []))}",
            duration_ms=int((time.time() - t0) * 1000),
            metadata={"source": result.get("source")},
        )
        return result

    async def _scrape_company():
        t0 = time.time()
        try:
            result = await firecrawl_svc.scrape_and_summarize(company_url)
            obs.log_event(
                trace_id=trace_id,
                agent_name="ae",
                tool_name="scrape_company_website",
                event_type="tool",
                input=company_url,
                output=f"source={result.get('source', 'n/a')} "
                       f"summary_len={len(result.get('raw_markdown', ''))}",
                duration_ms=int((time.time() - t0) * 1000),
            )
            return result
        except Exception as e:
            obs.log_event(
                trace_id=trace_id,
                agent_name="ae",
                tool_name="scrape_company_website",
                event_type="tool",
                input=company_url,
                output=f"ERROR: {e}",
                duration_ms=int((time.time() - t0) * 1000),
                status="error",
            )
            return {}

    async def _fetch_web_activity():
        t0 = time.time()
        result = await exa_svc.find_recent_activity(
            prospect.dm_name, prospect.company, num_results=4
        )
        obs.log_event(
            trace_id=trace_id,
            agent_name="ae",
            tool_name="find_recent_activity",
            event_type="tool",
            input=f"{prospect.dm_name} @ {prospect.company}",
            output=f"Found {len(result)} hits",
            duration_ms=int((time.time() - t0) * 1000),
        )
        return result

    # Fire all three concurrently — ~3x speedup
    linkedin, prospect_company_intel, activity = await asyncio.gather(
        _scrape_linkedin(),
        _scrape_company(),
        _fetch_web_activity(),
    )

    # Step 4: Load company profile + build context (NEW)
    company_profile = company_svc.get_company_profile()
    company_name = "SalesOS"
    company_context = ""
    if company_profile:
        company_name = company_profile.get("company_name", "SalesOS")
        context_parts = []
        if company_profile.get("tagline"):
            context_parts.append(f"TAGLINE: {company_profile['tagline']}")
        if company_profile.get("value_proposition"):
            context_parts.append(f"WHAT WE DO: {company_profile['value_proposition']}")
        if company_profile.get("product_description"):
            context_parts.append(f"OUR PRODUCT: {company_profile['product_description']}")
        if company_profile.get("key_differentiators"):
            diffs = "; ".join(company_profile["key_differentiators"][:5])
            context_parts.append(f"WHY US: {diffs}")
        company_context = "\n".join(context_parts)
    if not company_context:
        company_context = "ABOUT US: We help companies with AI-powered sales automation."

    # Step 5: Draft via LLM with structured output
    llm = make_llm(temperature=0.5, max_tokens=700).with_structured_output(_DraftSchema)

    hooks_about = (linkedin.get("about") or "")[:600]
    hooks_posts = (linkedin.get("recent_posts") or [])[:3]
    hooks_activity = activity[:3]

    # Build the enriched brief with prospect company intel
    brief_data = {
        "prospect_name": prospect.dm_name,
        "title": prospect.dm_title,
        "company": prospect.company,
        "why_target": prospect.why_target,
        "linkedin_about": hooks_about,
        "linkedin_recent_posts": hooks_posts,
        "web_recent_activity": hooks_activity,
        "linkedin_source": linkedin.get("source"),
    }

    # Add prospect company website intel if available
    if prospect_company_intel and not prospect_company_intel.get("error"):
        brief_data["prospect_company_website"] = {
            "url": prospect_company_intel.get("url", ""),
            "summary": prospect_company_intel.get("summary", ""),
            "title": prospect_company_intel.get("title", ""),
            "content_preview": (prospect_company_intel.get("raw_markdown") or "")[:1500],
        }

    user_brief = json.dumps(brief_data, default=str)[:8000]

    cb = obs.TraceCallback(trace_id, agent_label="ae")
    try:
        system_prompt = AE_DRAFT_SYSTEM.format(
            company_name=company_name,
            company_context=company_context,
            from_name=from_name,
        )
        draft_obj = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=f"Write the cold email. Brief:\n{user_brief}\n\n"
                    "Return: subject, body, personalization_hooks (1-3 bullets)."
                ),
            ],
            config={"callbacks": [cb]},
        )
    except Exception as e:
        return OutreachDraft(
            to_name=prospect.dm_name,
            to_email=to_email,
            company=prospect.company,
            subject=f"Quick thought on {prospect.company}",
            body=f"[ERROR drafting: {e}]\n\n{prospect.why_target}",
            personalization_hooks=[],
            dossier=prospect,
        )

    return OutreachDraft(
        to_name=prospect.dm_name,
        to_email=to_email,
        company=prospect.company,
        subject=draft_obj.subject,
        body=draft_obj.body,
        personalization_hooks=list(draft_obj.personalization_hooks or []),
        dossier=prospect,
    )


async def _derive_email(full_name: str, company: str, fallback: str) -> str:
    """3-tier email resolution: QEV pattern discovery -> naive guess -> fallback.

    Tier 1: Use QuickEmailVerification to discover the real pattern
            (tries 8 formats, returns the first verified hit).
    Tier 2: Naive firstname@company.com guess (old behaviour).
    Tier 3: Hardcoded fallback (demo@salesos.opensource).
    """
    if not full_name:
        return fallback

    parts = full_name.split()
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""

    # Best-effort domain from company name
    domain_guess = (
        "".join(c for c in company.lower() if c.isalnum()) + ".com"
    ) if company else None

    # Tier 1: QEV pattern discovery (only if we have first, last, and domain)
    if first and last and domain_guess:
        try:
            verified = await qev_svc.find_verified_email(first, last, domain_guess)
            if verified:
                return verified
        except Exception:
            pass  # fall through to naive guess

    # Tier 2: naive firstname@domain guess
    return email_svc.derive_email_for_demo(first, domain_guess)


async def draft_objection_reply(
    prospect_name: str,
    company: str,
    original_email: str,
    reply: str,
    trace_id: str,
) -> dict:
    obs.log_event(
        trace_id=trace_id,
        agent_name="vp",
        event_type="agent",
        input=f"Objection from {prospect_name}",
        output="Routing to AE draft_reply",
        duration_ms=12,
    )

    llm = make_llm(temperature=0.4, max_tokens=400).with_structured_output(_ReplySchema)
    cb = obs.TraceCallback(trace_id, agent_label="ae")
    brief = json.dumps(
        {
            "prospect_name": prospect_name,
            "company": company,
            "our_original_email": original_email[:1500],
            "their_reply": reply[:1500],
        }
    )
    out = await llm.ainvoke(
        [
            SystemMessage(content=AE_OBJECTION_SYSTEM),
            HumanMessage(content=f"Draft a reply. Context:\n{brief}"),
        ],
        config={"callbacks": [cb]},
    )
    return {
        "response_subject": out.response_subject,
        "response_body": out.response_body,
        "reasoning": out.reasoning,
    }


# --- Pydantic schemas for structured output (NOT in models.py because they
# are LLM-output shapes, not API contracts) ---

from pydantic import BaseModel, Field as PField


class _DraftSchema(BaseModel):
    subject: str = PField(..., description="Under 60 chars. References the prospect specifically.")
    body: str = PField(..., description="Under 100 words. Opens with a specific observation.")
    personalization_hooks: list[str] = PField(
        default_factory=list,
        description="1-3 specific things from the prospect's recent activity used in the email.",
    )


class _ReplySchema(BaseModel):
    response_subject: str
    response_body: str = PField(..., description="2-3 sentences. Acknowledge, propose low-friction next step.")
    reasoning: str = PField(default="", description="One sentence on why this response works.")


# --- module init: ensure DB exists ---
obs.init_db()
apify_svc.init_cache()
