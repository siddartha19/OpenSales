"""FastAPI backend for SalesOS.

Endpoints:
  POST /api/campaign/start       — Phase 1: SDR sources prospects
  POST /api/campaign/draft       — Phase 2: AE drafts emails per prospect
  POST /api/campaign/send        — Phase 3: send + log to sheets
  POST /api/campaign/objection   — bonus: AE drafts reply to a paste-in objection
  GET  /api/runs                 — recent traces
  GET  /api/trace/{trace_id}     — full trace tree + summary
  GET  /api/health               — service config presence
  GET  /api/sheet                — pipeline sheet URL

Mounts NOTHING for static — Next.js is the frontend, served separately.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse


def _get_user_email(request: Request) -> str:
    """Extract user email from X-User-Email header (set by the Next.js proxy)."""
    return (request.headers.get("x-user-email") or "").strip().lower()

from . import agent as agent_mod
from .config import (
    ALLOWED_ORIGINS,
    EMAIL_FALLBACK_RECIPIENT,
    SENDGRID_FROM_NAME,
    health_summary,
)
from .models import (
    CampaignResponse,
    CompanyProfileRequest,
    CreateSessionRequest,
    DraftRequest,
    ICPCreateRequest,
    ICPUpdateRequest,
    ObjectionRequest,
    ObjectionResponse,
    OutreachDraft,
    OutreachResult,
    ProspectDossier,
    SendRequest,
    StartCampaignRequest,
)
from .services import company as company_svc
from .services import firecrawl_svc
from .services import mailer as email_svc
from .services import observability as obs
from .services import sendgrid_activity as sg_activity_svc
from .services import sessions as sessions_svc
from .services import users as users_svc

app = FastAPI(title="SalesOS Backend", version="1.0.0")

origins = (
    [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
    if ALLOWED_ORIGINS != "*"
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Health & utility ----------


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", **health_summary()}


# ---------- Auth: signup + login ----------


@app.post("/api/auth/signup")
async def signup(body: dict) -> dict:
    """Register a new user."""
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="name, email, and password are required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = users_svc.signup(name, email, password)
    if user is None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    return {"user": user}


@app.post("/api/auth/login")
async def login(body: dict) -> dict:
    """Validate credentials. Frontend sets the cookie itself."""
    email = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password are required")

    user = users_svc.verify_credentials(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user": user}


@app.get("/api/users")
async def list_users() -> dict:
    """Admin endpoint: list all registered users."""
    return {"users": users_svc.list_users()}


# ---------- SendGrid delivery diagnostics ----------
#
# SendGrid's `sg.send()` returns 202 (accepted for processing) the moment the
# API gateway takes the message. That is NOT delivery confirmation. The
# Email Activity API is the source of truth — it tells us whether the
# message was actually `delivered` to the recipient MX or `not_delivered`
# (e.g. the recipient domain doesn't exist or rejected SMTP).
#
# These endpoints expose that truth so the UI can stop showing "sent" for
# emails that quietly bounced.


@app.get("/api/diagnostics/sendgrid/recent")
async def sendgrid_recent(limit: int = 25) -> dict:
    """Recent SendGrid activity with delivery status grouped by status."""
    return await sg_activity_svc.status_summary(limit=limit)


@app.post("/api/diagnostics/sendgrid/lookup")
async def sendgrid_lookup(body: dict) -> dict:
    """Resolve our X-Message-Id values to actual delivery status.

    Body: {message_ids: ["abc...", "def..."]}
    Returns: {results: {<id>: {status, to_email, last_event_time, ...}},
              missing: [...]}
    """
    ids = body.get("message_ids") or []
    found = await sg_activity_svc.lookup_by_message_ids(ids)
    missing = [i for i in ids if i not in found]
    return {"results": found, "missing": missing}


# ---------- Sessions ----------


@app.post("/api/sessions")
async def create_session(req: CreateSessionRequest, request: Request) -> dict:
    user_email = _get_user_email(request)
    sess = sessions_svc.create_session(req.name, user_email=user_email)
    return {"session": sess}


@app.get("/api/sessions")
async def list_sessions(request: Request) -> dict:
    user_email = _get_user_email(request)
    return {"sessions": sessions_svc.list_sessions(user_email=user_email)}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    sess = sessions_svc.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": sess}


@app.put("/api/sessions/{session_id}")
async def update_session(session_id: str, body: dict) -> dict:
    sess = sessions_svc.update_session(
        session_id,
        name=body.get("name"),
        phase=body.get("phase"),
        prospects_json=body.get("prospects_json"),
        drafts_json=body.get("drafts_json"),
    )
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": sess}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    ok = sessions_svc.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


# ---------- Company Profile ----------


@app.get("/api/company-profile")
async def get_company_profile(request: Request) -> dict:
    user_email = _get_user_email(request)
    profile = company_svc.get_company_profile(user_email=user_email)
    return {"profile": profile}


@app.post("/api/company-profile")
async def save_company_profile(req: CompanyProfileRequest, request: Request) -> dict:
    user_email = _get_user_email(request)
    data = req.model_dump()
    auto_scrape = data.pop("auto_scrape", True)

    # Auto-scrape company website via Firecrawl if requested
    if auto_scrape and req.website_url:
        scrape_result = await firecrawl_svc.scrape_and_summarize(req.website_url)
        if scrape_result.get("raw_markdown"):
            data["scraped_website_summary"] = scrape_result.get("summary", "")
            data["scraped_raw_markdown"] = scrape_result.get("raw_markdown", "")[:2000]

    profile = company_svc.save_company_profile(data, user_email=user_email)
    return {"profile": profile}


@app.delete("/api/company-profile")
async def delete_company_profile(request: Request) -> dict:
    user_email = _get_user_email(request)
    ok = company_svc.delete_company_profile(user_email=user_email)
    if not ok:
        raise HTTPException(status_code=404, detail="No company profile found")
    return {"deleted": True}


# ---------- ICP Definitions ----------


@app.get("/api/icps")
async def list_icps(request: Request) -> dict:
    user_email = _get_user_email(request)
    return {"icps": company_svc.list_icps(user_email=user_email)}


@app.post("/api/icps")
async def create_icp(req: ICPCreateRequest, request: Request) -> dict:
    user_email = _get_user_email(request)
    data = req.model_dump()
    icp = company_svc.create_icp(data, user_email=user_email)
    if icp is None:
        raise HTTPException(status_code=400, detail="Maximum 3 ICPs allowed. Delete one first.")
    return {"icp": icp}


@app.get("/api/icps/{icp_id}")
async def get_icp(icp_id: str) -> dict:
    icp = company_svc.get_icp(icp_id)
    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found")
    return {"icp": icp}


@app.put("/api/icps/{icp_id}")
async def update_icp(icp_id: str, req: ICPUpdateRequest) -> dict:
    # Only pass non-None fields
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    # Merge with existing
    existing = company_svc.get_icp(icp_id)
    if not existing:
        raise HTTPException(status_code=404, detail="ICP not found")
    merged = {**existing, **update_data}
    # Remove metadata fields before saving
    for key in ("id", "created_at", "updated_at"):
        merged.pop(key, None)
    icp = company_svc.update_icp(icp_id, merged)
    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found")
    return {"icp": icp}


@app.delete("/api/icps/{icp_id}")
async def delete_icp(icp_id: str) -> dict:
    ok = company_svc.delete_icp(icp_id)
    if not ok:
        raise HTTPException(status_code=404, detail="ICP not found")
    return {"deleted": True}


# ---------- Firecrawl website scrape (standalone) ----------


@app.post("/api/scrape-website")
async def scrape_website(body: dict) -> dict:
    """Scrape any website via Firecrawl. Used for owner onboarding + prospect research."""
    url = body.get("url", "")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    result = await firecrawl_svc.scrape_and_summarize(url)
    return {"result": result}


# ---------- Campaign phases ----------


@app.post("/api/campaign/start", response_model=CampaignResponse)
async def start_campaign(req: StartCampaignRequest) -> CampaignResponse:
    """Phase 1: parse ICP, run SDR, return prospect dossiers for review."""
    run_id = f"run_{uuid.uuid4().hex[:10]}"

    # Link run to session
    if req.session_id:
        sessions_svc.add_run_id(req.session_id, run_id)
        sessions_svc.update_session(req.session_id, phase="sourcing")

    obs.log_event(
        trace_id=run_id,
        agent_name="vp",
        event_type="agent",
        input=f"start_campaign | target={req.target_count}",
        output=f"Run {run_id} started",
        duration_ms=5,
    )

    prospects = await agent_mod.run_sourcing(req.icp, run_id, req.target_count)

    activity = []
    for p in prospects:
        activity.append({"event": "sourced", "prospect": p.dm_name, "company": p.company})

    # Persist prospects + activity to session
    if req.session_id:
        sessions_svc.update_session(
            req.session_id,
            phase="review" if prospects else "idle",
            prospects_json=json.dumps([p.model_dump() for p in prospects]),
            activity_json=json.dumps(activity),
        )

    status = "ready_for_review" if prospects else "error"
    return CampaignResponse(
        run_id=run_id,
        session_id=req.session_id,
        status=status,
        prospects=prospects,
        activity=activity,
        error=None if prospects else "SDR returned no prospects. Check ICP or service health.",
    )


@app.post("/api/campaign/draft")
async def draft_outreach(req: DraftRequest) -> EventSourceResponse:
    """Phase 2: AE drafts personalized emails — streams progress via SSE.

    Each prospect emits step-by-step events so the frontend shows a live trace:
      - { step: "enriching", prospect: "Name", ... }
      - { step: "scraping_linkedin", ... }
      - { step: "scraping_website", ... }
      - { step: "finding_activity", ... }
      - { step: "drafting_email", ... }
      - { step: "draft_complete", draft: {...} }
    Final event: { step: "all_done", drafts: [...] }
    """
    async def event_generator():
        if req.session_id:
            sessions_svc.update_session(req.session_id, phase="drafting")

        obs.log_event(
            trace_id=req.run_id,
            agent_name="vp",
            event_type="agent",
            input=f"draft_outreach | {len(req.prospects)} prospects",
            output="Routing each to AE — streaming progress",
            duration_ms=10,
        )

        drafts: list[OutreachDraft] = []
        activity: list[dict] = []

        for idx, p in enumerate(req.prospects):
            # Emit: starting this prospect
            yield {
                "event": "progress",
                "data": json.dumps({
                    "step": "starting",
                    "prospect": p.dm_name,
                    "company": p.company,
                    "index": idx,
                    "total": len(req.prospects),
                }),
            }

            try:
                # Emit: enriching
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "step": "enriching",
                        "prospect": p.dm_name,
                        "detail": f"Looking up contact info for {p.dm_name}",
                    }),
                }

                draft = await agent_mod.draft_outreach_for_prospect(
                    p,
                    trace_id=req.run_id,
                    from_name=SENDGRID_FROM_NAME or "Alera Founder",
                    fallback_email=EMAIL_FALLBACK_RECIPIENT,
                )
                drafts.append(draft)
                activity.append({"event": "drafted", "prospect": p.dm_name, "subject": draft.subject})

                # Emit: draft complete for this prospect
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "step": "draft_complete",
                        "prospect": p.dm_name,
                        "index": idx,
                        "total": len(req.prospects),
                        "subject": draft.subject,
                        "draft": draft.model_dump(),
                    }),
                }

            except Exception as e:
                activity.append({"event": "draft_error", "prospect": p.dm_name, "error": str(e)})
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "step": "draft_error",
                        "prospect": p.dm_name,
                        "error": str(e)[:200],
                    }),
                }

        # Persist drafts + activity to session
        if req.session_id:
            sessions_svc.update_session(
                req.session_id,
                phase="ready",
                drafts_json=json.dumps([d.model_dump() for d in drafts]),
                activity_json=json.dumps(activity),
            )

        # Final event with all drafts
        yield {
            "event": "done",
            "data": json.dumps({
                "step": "all_done",
                "run_id": req.run_id,
                "session_id": req.session_id,
                "drafts": [d.model_dump() for d in drafts],
                "activity": activity,
            }),
        }

    return EventSourceResponse(event_generator())


@app.post("/api/campaign/send", response_model=CampaignResponse)
async def send_outreach(req: SendRequest) -> CampaignResponse:
    """Phase 3: send approved emails via SendGrid."""
    if req.session_id:
        sessions_svc.update_session(req.session_id, phase="sending")

    obs.log_event(
        trace_id=req.run_id,
        agent_name="vp",
        event_type="agent",
        input=f"send_outreach | {len(req.drafts)} drafts",
        output="Approved. Sending.",
        duration_ms=8,
    )

    sent: list[OutreachResult] = []
    activity: list[dict] = []
    for d in req.drafts:
        t0 = time.time()
        res = email_svc.send_email(
            to_email=d.to_email,
            to_name=d.to_name,
            subject=d.subject,
            body=d.body,
        )
        duration = int((time.time() - t0) * 1000)

        obs.log_event(
            trace_id=req.run_id,
            agent_name="ae",
            tool_name="send_outreach_email",
            event_type="tool",
            input=f"to={d.to_email} subject={d.subject}",
            output=json.dumps(res),
            duration_ms=duration,
            status="success" if res.get("success") else "error",
        )

        sent.append(
            OutreachResult(
                success=bool(res.get("success")),
                message_id=res.get("message_id"),
                error=res.get("error"),
            )
        )
        activity.append(
            {
                "event": "sent",
                "to": d.to_email,
                "success": res.get("success"),
            }
        )

    # Update session to done + persist activity
    if req.session_id:
        sessions_svc.update_session(
            req.session_id,
            phase="done",
            activity_json=json.dumps(activity),
        )

    return CampaignResponse(
        run_id=req.run_id,
        session_id=req.session_id,
        status="complete",
        drafts=req.drafts,
        sent=sent,
        activity=activity,
    )


@app.post("/api/campaign/objection", response_model=ObjectionResponse)
async def draft_objection(req: ObjectionRequest) -> ObjectionResponse:
    """Bonus: paste-in reply, AE drafts a non-defensive response."""
    trace_id = f"obj_{uuid.uuid4().hex[:8]}"
    out = await agent_mod.draft_objection_reply(
        prospect_name=req.prospect_name,
        company=req.company,
        original_email=req.original_email,
        reply=req.reply,
        trace_id=trace_id,
    )
    return ObjectionResponse(**out)


# ---------- Trace UI data ----------


@app.get("/api/runs")
async def list_runs(limit: int = 30) -> dict:
    return {"runs": obs.list_recent_traces(limit)}


@app.get("/api/trace/{trace_id}")
async def get_trace(trace_id: str) -> dict:
    rows = obs.fetch_trace(trace_id)
    summary = obs.trace_summary(trace_id)
    return {"summary": summary, "rows": rows}


# ---------- Eval results passthrough ----------


@app.get("/api/evals")
async def get_evals() -> dict:
    """Returns most recent eval run results from disk if present."""
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "evals" / "last_run.json"
    if not p.exists():
        return {"available": False, "message": "Run `python backend/evals/run.py` to generate."}
    try:
        return {"available": True, **json.loads(p.read_text())}
    except Exception as e:
        return {"available": False, "error": str(e)}


# ---------- Stats / Analytics / CRM ----------


from .services import governance as gov_svc
from .services import crm as crm_svc


@app.get("/api/stats")
async def get_stats() -> dict:
    """Aggregated stats for the overview dashboard.

    Pipeline counts are built per-prospect using the same logic as the CRM
    endpoint: sheet stage first, then CRM manual override on top.  This means
    when a user moves a prospect to 'Demo Booked' in the CRM, the overview
    funnel reflects it immediately.
    """
    all_sessions = sessions_svc.list_sessions()
    total_campaigns = len(all_sessions)
    active_campaigns = sum(1 for s in all_sessions if s.get("phase") not in ("idle", "done"))

    # Batch-load CRM overrides once
    stage_overrides = crm_svc.all_stage_overrides()

    total_prospects = 0
    pipeline: dict[str, int] = {}

    for s in all_sessions:
        session_id = s["session_id"]

        # Parse prospects
        try:
            session_prospects = json.loads(s.get("prospects_json", "[]"))
        except Exception:
            session_prospects = []
        total_prospects += len(session_prospects)

        # Parse drafts for name→email mapping (used to infer "Researched")
        try:
            session_drafts = json.loads(s.get("drafts_json", "[]"))
        except Exception:
            session_drafts = []
        drafted_names: set[str] = {d.get("to_name", "") for d in session_drafts}
        phase = s.get("phase", "idle")

        # Sheet-based stages
        ws = s.get("worksheet_name")
        sheet_stage_map: dict[str, str] = {}
        if ws:
            try:
                from .services.sheets import read_all
                if read_all:
                    rows = read_all(worksheet=ws) or []
                    for row in rows[1:] if len(rows) > 1 else []:
                        if len(row) > 6:
                            dm = row[2] if len(row) > 2 else ""
                            st = row[6] if len(row) > 6 else ""
                            if dm and st:
                                sheet_stage_map[dm] = st
            except Exception:
                pass

        # Session-level CRM overrides
        session_overrides = stage_overrides.get(session_id, {})

        # Compute the effective stage for each prospect
        for p in session_prospects:
            dm_name = p.get("dm_name", "")
            # Priority: CRM override > sheet > inferred from phase
            if dm_name in session_overrides:
                stage = session_overrides[dm_name]
            elif dm_name in sheet_stage_map:
                stage = sheet_stage_map[dm_name]
            elif phase == "done" and dm_name in drafted_names:
                stage = "Outreach Sent"
            elif dm_name in drafted_names:
                stage = "Researched"
            else:
                stage = "Sourced"
            pipeline[stage] = pipeline.get(stage, 0) + 1

    total_sent = pipeline.get("Outreach Sent", 0)
    total_replied = pipeline.get("Replied", 0)
    total_demos = pipeline.get("Demo Booked", 0)
    response_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
    conversion_rate = (total_demos / total_prospects * 100) if total_prospects > 0 else 0

    return {
        "total_campaigns": total_campaigns,
        "active_campaigns": active_campaigns,
        "total_prospects": total_prospects,
        "total_sent": total_sent,
        "total_replied": total_replied,
        "total_demos": total_demos,
        "response_rate": round(response_rate, 1),
        "conversion_rate": round(conversion_rate, 1),
        "pipeline": pipeline,
        "recent_sessions": all_sessions[:5],
    }


@app.get("/api/analytics")
async def get_analytics() -> dict:
    """Redirects to stats — analytics page removed."""
    return await get_stats()


@app.get("/api/crm/prospects")
async def get_crm_prospects() -> dict:
    """All prospects across all campaigns for the CRM view.
    Includes manual stage overrides and notes."""
    all_sessions = sessions_svc.list_sessions()
    prospects = []
    prospect_id = 0

    # Batch-load all CRM overrides + notes
    stage_overrides = crm_svc.all_stage_overrides()
    all_notes = crm_svc.all_notes()

    for s in all_sessions:
        session_id = s["session_id"]
        session_name = s["name"]

        # Get prospects from session
        try:
            session_prospects = json.loads(s.get("prospects_json", "[]"))
        except Exception:
            session_prospects = []

        # Get drafts from session for email data
        try:
            session_drafts = json.loads(s.get("drafts_json", "[]"))
        except Exception:
            session_drafts = []

        draft_map: dict[str, dict] = {}
        for d in session_drafts:
            key = d.get("to_name", "")
            draft_map[key] = d

        # Derive stages from session phase (no sheets)
        phase = s.get("phase", "idle")
        drafted_names = set(d.get("to_name", "") for d in session_drafts)

        # Session-level overrides and notes
        session_overrides = stage_overrides.get(session_id, {})
        session_notes = all_notes.get(session_id, {})

        for p in session_prospects:
            prospect_id += 1
            dm_name = p.get("dm_name", "")
            draft = draft_map.get(dm_name, {})

            # Derive stage: override > phase-based inference
            default_stage = "Sourced"
            if dm_name in drafted_names:
                default_stage = "Researched"
            if phase == "done" and dm_name in drafted_names:
                default_stage = "Outreach Sent"
            stage = session_overrides.get(dm_name) or default_stage
            notes = session_notes.get(dm_name, [])

            prospects.append({
                "id": f"p_{prospect_id}",
                "session_id": session_id,
                "session_name": session_name,
                "company": p.get("company", ""),
                "dm_name": dm_name,
                "dm_title": p.get("dm_title", ""),
                "dm_linkedin": p.get("dm_linkedin"),
                "email": draft.get("to_email"),
                "fit_score": p.get("fit_score"),
                "why_target": p.get("why_target"),
                "stage": stage,
                "subject_sent": draft.get("subject"),
                "created_at": s.get("created_at", ""),
                "notes": notes,
            })

    return {"prospects": prospects}


# ---------- CRM Notes + Stage ----------


@app.post("/api/crm/notes")
async def add_crm_note(body: dict) -> dict:
    """Add a note/comment to a prospect."""
    session_id = body.get("session_id", "")
    dm_name = body.get("dm_name", "")
    content = body.get("content", "").strip()
    if not session_id or not dm_name or not content:
        raise HTTPException(status_code=400, detail="session_id, dm_name, and content are required")
    note = crm_svc.add_note(session_id, dm_name, content)
    return {"note": note}


@app.delete("/api/crm/notes/{note_id}")
async def delete_crm_note(note_id: str) -> dict:
    """Delete a note."""
    ok = crm_svc.delete_note(note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"deleted": True}


@app.post("/api/crm/stage")
async def set_crm_stage(body: dict) -> dict:
    """Manually override a prospect's pipeline stage."""
    session_id = body.get("session_id", "")
    dm_name = body.get("dm_name", "")
    stage = body.get("stage", "")
    if not session_id or not dm_name or not stage:
        raise HTTPException(status_code=400, detail="session_id, dm_name, and stage are required")
    valid_stages = ["Sourced", "Researched", "Outreach Sent", "Replied", "Qualified", "Demo Booked", "Lost"]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"stage must be one of: {', '.join(valid_stages)}")
    result = crm_svc.set_stage(session_id, dm_name, stage)
    return {"stage": result}


# ---------- Governance bridge ----------


@app.get("/api/governance")
async def get_governance() -> dict:
    """Combined governance data (company + ICPs) for the frontend."""
    profile = company_svc.get_company_profile()
    icps_list = company_svc.list_icps()

    # Bridge company profile to simpler format for governance page
    company_data = {}
    if profile:
        company_data = {
            "name": profile.get("company_name", ""),
            "domain": profile.get("website_url", ""),
            "industry": ", ".join(profile.get("target_industries", [])),
            "description": profile.get("value_proposition", ""),
            "team_size": profile.get("company_size", ""),
            "meeting_link": profile.get("meeting_link", ""),
        }

    # Bridge ICPs
    bridged_icps = []
    for icp in icps_list:
        bridged_icps.append({
            "id": icp.get("id", ""),
            "name": icp.get("name", ""),
            "description": icp.get("description", ""),
            "created_at": icp.get("created_at", ""),
        })

    return {"company": company_data, "icps": bridged_icps}


@app.post("/api/governance/company")
async def save_governance_company(body: dict) -> dict:
    """Save company info from governance page."""
    # Bridge to existing company profile format
    profile_data = {
        "company_name": body.get("name", ""),
        "website_url": body.get("domain", ""),
        "target_industries": [body.get("industry", "")] if body.get("industry") else [],
        "value_proposition": body.get("description", ""),
        "company_size": body.get("team_size", ""),
        "meeting_link": body.get("meeting_link", ""),
    }
    company_svc.save_company_profile(profile_data)
    return {"saved": True}


@app.post("/api/governance/icps")
async def create_governance_icp(body: dict) -> dict:
    """Create ICP from governance page."""
    icp_data = {
        "name": body.get("name", ""),
        "description": body.get("description", ""),
    }
    result = company_svc.create_icp(icp_data)
    if result is None:
        raise HTTPException(status_code=400, detail="Maximum ICPs reached")
    return {"icp": {
        "id": result.get("id", ""),
        "name": result.get("name", ""),
        "description": result.get("description", ""),
        "created_at": result.get("created_at", ""),
    }}


@app.put("/api/governance/icps/{icp_id}")
async def update_governance_icp(icp_id: str, body: dict) -> dict:
    """Update ICP from governance page."""
    existing = company_svc.get_icp(icp_id)
    if not existing:
        raise HTTPException(status_code=404, detail="ICP not found")
    update_data = {**existing}
    for key in ("id", "created_at", "updated_at"):
        update_data.pop(key, None)
    if "name" in body:
        update_data["name"] = body["name"]
    if "description" in body:
        update_data["description"] = body["description"]
    result = company_svc.update_icp(icp_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="ICP not found")
    return {"icp": {
        "id": result.get("id", ""),
        "name": result.get("name", ""),
        "description": result.get("description", ""),
        "created_at": result.get("created_at", ""),
    }}


@app.delete("/api/governance/icps/{icp_id}")
async def delete_governance_icp(icp_id: str) -> dict:
    """Delete ICP from governance page."""
    ok = company_svc.delete_icp(icp_id)
    if not ok:
        raise HTTPException(status_code=404, detail="ICP not found")
    return {"deleted": True}


# ---------- Follow-up / Nudge ----------


@app.post("/api/campaign/followup")
async def generate_followups(body: dict) -> dict:
    """Generate 3 follow-up variants per prospect."""
    prospects = body.get("prospects", [])
    meeting_link = body.get("meeting_link", "")
    followups = []

    for p in prospects:
        dm_name = p.get("dm_name", "Prospect")
        company = p.get("company", "the company")
        followups.append({
            "prospect": p,
            "to_email": p.get("email", f"{dm_name.lower().replace(' ', '.')}@{company.lower().replace(' ', '')}.com"),
            "variants": [
                {
                    "id": f"gentle_{uuid.uuid4().hex[:6]}",
                    "type": "gentle_nudge",
                    "label": "Gentle Nudge",
                    "subject": f"Quick follow-up, {dm_name.split()[0]}",
                    "body": f"Hi {dm_name.split()[0]},\n\nJust wanted to float this back to the top of your inbox. I know things get busy — would love to hear your thoughts on my previous note.\n\nNo pressure at all, but if there's a better time or a colleague who handles this, happy to adjust.\n\nBest,",
                },
                {
                    "id": f"value_{uuid.uuid4().hex[:6]}",
                    "type": "value_add",
                    "label": "Value Add",
                    "subject": f"Thought this might be useful for {company}",
                    "body": f"Hi {dm_name.split()[0]},\n\nI came across some interesting data on how companies in your space are approaching outbound automation — thought it might resonate with what you're building at {company}.\n\nHappy to share more details if you're curious. Either way, hope it's helpful.\n\nCheers,",
                },
                {
                    "id": f"meeting_{uuid.uuid4().hex[:6]}",
                    "type": "meeting_request",
                    "label": "Meeting Request",
                    "subject": f"15 min chat, {dm_name.split()[0]}?",
                    "body": f"Hi {dm_name.split()[0]},\n\nWould you be open to a quick 15-minute call this week? I'd love to learn more about what {company} is working on and share a few ideas that might be relevant.\n\n{f'Here is my calendar link: {meeting_link}' if meeting_link else 'Happy to work around your schedule — just let me know what works.'}\n\nLooking forward to it,",
                },
            ],
            "selected_variant": None,
        })

    return {"followups": followups}


@app.get("/")
async def root() -> dict:
    return {
        "name": "SalesOS Backend",
        "ui": "Next.js on :3000",
        "endpoints": [
            "/api/auth/signup",
            "/api/auth/login",
            "/api/users",
            "/api/health",
            "/api/stats",
            "/api/analytics",
            "/api/governance",
            "/api/crm/prospects",
            "/api/company-profile",
            "/api/icps",
            "/api/icps/{icp_id}",
            "/api/scrape-website",
            "/api/sessions",
            "/api/sessions/{session_id}",
            "/api/campaign/start",
            "/api/campaign/draft",
            "/api/campaign/send",
            "/api/campaign/objection",
            "/api/campaign/followup",
            "/api/runs",
            "/api/trace/{trace_id}",
            "/api/evals",
            "/api/diagnostics/sendgrid/recent",
            "/api/diagnostics/sendgrid/lookup",
        ],
    }
