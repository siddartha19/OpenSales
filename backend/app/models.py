"""Pydantic models — the typed contract between agents, services, and the UI."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Stage = Literal[
    "Sourced",
    "Researched",
    "Outreach Sent",
    "Replied",
    "Qualified",
    "Demo Booked",
    "Lost",
]


# ---------- Sessions ----------


class Session(BaseModel):
    """A named campaign session. Each session gets its own Google Sheet tab."""
    session_id: str
    name: str
    worksheet_name: str  # sanitized version of name for the sheet tab
    created_at: str = ""
    phase: str = "idle"  # idle | sourcing | review | drafting | ready | sending | done
    run_ids: list[str] = Field(default_factory=list)
    prospects_json: str = "[]"  # stored as JSON string for SQLite
    drafts_json: str = "[]"


class CreateSessionRequest(BaseModel):
    name: str


class SessionResponse(BaseModel):
    session: Session
    sheet_url: Optional[str] = None


# ---------- Domain models ----------


class DiscoveredCompany(BaseModel):
    """One company found by SDR via Exa."""
    name: str
    domain: Optional[str] = None
    snippet: str = ""
    url: Optional[str] = None
    published_date: Optional[str] = None


class DecisionMaker(BaseModel):
    """Decision-maker found at a company."""
    name: str
    title: str
    company: str
    linkedin_url: Optional[str] = None
    email: Optional[str] = None  # only set after enrich


class ProspectDossier(BaseModel):
    """SDR's output. AE consumes this."""
    company: str
    company_url: Optional[str] = None
    dm_name: str
    dm_title: str
    dm_linkedin: Optional[str] = None
    why_target: str = ""  # 1-2 sentences from public sources, no fabrication
    fit_score: float = Field(default=0.7, ge=0, le=1)


class LinkedInProfile(BaseModel):
    source: Literal["apify_cache", "apify_live", "exa_fallback", "none"] = "none"
    about: Optional[str] = None
    headline: Optional[str] = None
    experience: list[dict] = Field(default_factory=list)
    recent_posts: list[dict] = Field(default_factory=list)
    fallback_reason: Optional[str] = None
    latency_s: Optional[float] = None


class OutreachDraft(BaseModel):
    to_name: str
    to_email: str
    company: str
    subject: str
    body: str
    personalization_hooks: list[str] = Field(default_factory=list)
    dossier: Optional[ProspectDossier] = None


class OutreachResult(BaseModel):
    success: bool
    message_id: Optional[str] = None
    mode: Literal["mock", "real"] = "mock"
    error: Optional[str] = None
    sheet_row: Optional[int] = None


# ---------- API request/response models ----------


class StartCampaignRequest(BaseModel):
    icp: str
    email_mode: Literal["mock", "real"] = "mock"
    target_count: int = 8
    session_id: Optional[str] = None


class CampaignResponse(BaseModel):
    run_id: str
    status: Literal["running", "ready_for_review", "complete", "error"]
    session_id: Optional[str] = None
    prospects: list[ProspectDossier] = Field(default_factory=list)
    drafts: list[OutreachDraft] = Field(default_factory=list)
    sent: list[OutreachResult] = Field(default_factory=list)
    activity: list[dict] = Field(default_factory=list)
    error: Optional[str] = None


class DraftRequest(BaseModel):
    run_id: str
    prospects: list[ProspectDossier]
    email_mode: Literal["mock", "real"] = "mock"
    session_id: Optional[str] = None


class SendRequest(BaseModel):
    run_id: str
    drafts: list[OutreachDraft]
    email_mode: Literal["mock", "real"] = "mock"
    session_id: Optional[str] = None


class ObjectionRequest(BaseModel):
    prospect_email: str
    prospect_name: str
    company: str
    original_email: str
    reply: str


class ObjectionResponse(BaseModel):
    response_subject: str
    response_body: str
    reasoning: str = ""


class TraceRow(BaseModel):
    run_id: str
    parent_run_id: Optional[str] = None
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    input: Optional[str] = None
    output: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    status: str = "success"
    started_at: str = ""
    ended_at: str = ""


class TraceTreeNode(BaseModel):
    row: TraceRow
    children: list["TraceTreeNode"] = Field(default_factory=list)


TraceTreeNode.model_rebuild()


# ---------- Company Profile (owner's company — set once) ----------


class CompanyProfile(BaseModel):
    """The sending company's identity — configured once during onboarding.

    Scraped via Firecrawl + manual input. Injected into every AE email draft
    so the LLM knows what 'we' actually do.
    """
    company_name: str
    website_url: str
    tagline: str = ""                          # one-liner, e.g. "AI-powered sales automation"
    value_proposition: str = ""                 # 2-3 sentences: what you do, for whom, why
    product_description: str = ""              # what you sell (features, use cases)
    key_differentiators: list[str] = Field(default_factory=list)  # 3-5 bullets
    target_industries: list[str] = Field(default_factory=list)
    company_size: str = ""                     # e.g. "Series A, 15 people"
    founder_name: str = ""
    founder_linkedin: Optional[str] = None
    scraped_website_summary: Optional[str] = None  # auto-filled by Firecrawl
    scraped_raw_markdown: Optional[str] = None     # raw website content (truncated)
    created_at: str = ""
    updated_at: str = ""


class CompanyProfileRequest(BaseModel):
    """Request body for creating/updating the company profile."""
    company_name: str
    website_url: str
    tagline: str = ""
    value_proposition: str = ""
    product_description: str = ""
    key_differentiators: list[str] = Field(default_factory=list)
    target_industries: list[str] = Field(default_factory=list)
    company_size: str = ""
    founder_name: str = ""
    founder_linkedin: Optional[str] = None
    auto_scrape: bool = True  # scrape the website on save


# ---------- ICP Definitions (max 3 saved profiles) ----------


class ICPDefinition(BaseModel):
    """A saved Ideal Customer Profile that can be selected per-campaign."""
    id: str = ""
    name: str                                   # e.g. "Enterprise SaaS CTO"
    description: str                            # free-text ICP (what SDR uses today)
    industry: Optional[str] = None
    company_size_range: Optional[str] = None    # e.g. "50-500 employees"
    geography: Optional[str] = None
    target_titles: list[str] = Field(default_factory=list)  # e.g. ["CTO", "VP Eng"]
    pain_points: list[str] = Field(default_factory=list)     # their problems
    why_we_fit: str = ""                        # why YOUR product solves THEIR problem
    created_at: str = ""
    updated_at: str = ""


class ICPCreateRequest(BaseModel):
    """Request body for creating an ICP."""
    name: str
    description: str
    industry: Optional[str] = None
    company_size_range: Optional[str] = None
    geography: Optional[str] = None
    target_titles: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    why_we_fit: str = ""


class ICPUpdateRequest(BaseModel):
    """Request body for updating an ICP."""
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    company_size_range: Optional[str] = None
    geography: Optional[str] = None
    target_titles: Optional[list[str]] = None
    pain_points: Optional[list[str]] = None
    why_we_fit: Optional[str] = None
