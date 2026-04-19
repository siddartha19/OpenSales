// Shared types for SalesOS frontend

export type Prospect = {
  company: string;
  dm_name: string;
  dm_title: string;
  dm_linkedin?: string;
  why_target?: string;
  fit_score?: number;
};

export type Draft = {
  to_name: string;
  to_email: string;
  company: string;
  subject: string;
  body: string;
  personalization_hooks?: string[];
  dossier?: Prospect;
};

export type SentResult = {
  success: boolean;
  message_id?: string;
  mode?: "mock" | "real";
  error?: string;
};

export type Activity = { event: string; [k: string]: any };

export type SessionInfo = {
  session_id: string;
  name: string;
  worksheet_name: string;
  created_at: string;
  phase: string;
  run_ids: string[];
  prospects_json: string;
  drafts_json: string;
};

export type FollowUpVariant = {
  id: string;
  type: "gentle_nudge" | "value_add" | "meeting_request";
  label: string;
  subject: string;
  body: string;
};

export type FollowUpSet = {
  prospect: Prospect;
  to_email: string;
  variants: FollowUpVariant[];
  selected_variant?: string;
};

export type CompanyInfo = {
  name: string;
  domain: string;
  industry: string;
  description: string;
  team_size: string;
  meeting_link: string;
};

export type ICPProfile = {
  id: string;
  name: string;
  description: string;
  created_at: string;
};

export type CRMNote = {
  id: string;
  content: string;
  created_at: string;
};

export type CRMProspect = {
  id: string;
  session_id: string;
  session_name: string;
  company: string;
  dm_name: string;
  dm_title: string;
  dm_linkedin?: string;
  email?: string;
  fit_score?: number;
  why_target?: string;
  stage: string;
  subject_sent?: string;
  sent_at?: string;
  created_at: string;
  notes: CRMNote[];
};

export type StatsOverview = {
  total_campaigns: number;
  active_campaigns: number;
  total_prospects: number;
  total_sent: number;
  total_replied: number;
  total_demos: number;
  response_rate: number;
  conversion_rate: number;
  pipeline: Record<string, number>;
  recent_sessions: SessionInfo[];
};

export type AnalyticsData = {
  overview: StatsOverview;
  campaign_breakdown: {
    session_id: string;
    name: string;
    phase: string;
    prospects: number;
    sent: number;
    replied: number;
    demos: number;
    created_at: string;
  }[];
  stage_funnel: { stage: string; count: number; pct: number }[];
  daily_activity: { date: string; sent: number; sourced: number }[];
};
