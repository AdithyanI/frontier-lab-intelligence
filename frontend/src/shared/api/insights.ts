import type { FeedDate } from './evidence'

export type InsightAudience = 'investment' | 'ai_engineering'
export type InsightDecision = 'surface' | 'suppress'
export type InsightStatus = 'kept' | 'suppressed' | 'all'
export type BriefDeliveryChannel = 'slack' | 'email'

export interface BriefDeliveryChannelStatus {
  channel: BriefDeliveryChannel
  label: string
  configured: boolean
  available: boolean
  destination: string
  pdf_delivery: 'link' | 'attachment'
}

export interface BriefDeliveryStatus {
  schema_version: string
  available: boolean
  reason: string | null
  audience: InsightAudience
  date: string | null
  total_insight_count: number
  top_insight_count: number
  channels: BriefDeliveryChannelStatus[]
}

export interface BriefDeliveryResult {
  schema_version: string
  status: 'sent'
  channel: BriefDeliveryChannel
  destination: string
  audience: InsightAudience
  date: string
  insight_count: number
  pdf_delivery: 'link' | 'attachment'
  pdf_filename: string
  report_version: string
  delivery_id: string
  provider_id: string
  sent_at: string
}

export interface InsightItem {
  candidate_id: string
  event_id: string
  day: string
  feed_rank: number
  audience: InsightAudience
  decision: InsightDecision
  decision_reason: string
  title: string
  summary: string | null
  why_it_matters: string | null
  action: string | null
  action_label: 'Watchpoint' | 'Experiment'
  model: string
  reasoning_effort: string
  prompt_version: string
  source_routing_run_id: string
  root_source_url: string | null
  artifacts: Array<{ title: string; url: string }>
}

export interface InsightRun {
  run_id: string
  day: string
  audience: InsightAudience
  candidate_count: number
  complete_count: number
  surfaced_count: number
  suppressed_count: number
  model: string
  prompt_version: string
  input_tokens: number
  cached_tokens: number
  reported_cost_usd: number
  counts: Record<InsightStatus, number>
}

export interface CandidateDecisionInsightsResponse {
  available: boolean
  reason?: string | null
  audience: InsightAudience
  status: InsightStatus
  content_kind: 'candidate_decisions'
  run: InsightRun | null
  items: InsightItem[]
}

export type EditorialEventRole = 'primary' | 'supporting' | 'context' | 'counterevidence'
export type EditorialCitationKind = 'event' | 'artifact' | 'web' | 'context'
export type InvestmentEntityScope = 'portfolio' | 'outside_portfolio'
export type InvestmentImpactDirection = 'positive' | 'negative' | 'mixed' | 'uncertain'

export interface EditorialEventLink {
  event_id: string
  feed_rank: number
  role: EditorialEventRole
  reason: string
}

export interface EditorialCitation {
  citation_id: string
  local_id: string
  kind: EditorialCitationKind
  url: string
  title: string
  event_id: string | null
  artifact_id: string | null
  published_at: string | null
  retrieved_at: string | null
  supports: string
  excerpt: string | null
}

export interface InvestmentEditorialAnalysis {
  affected_entities: Array<{
    name: string
    scope: InvestmentEntityScope
    impact: InvestmentImpactDirection
    mechanism: string
  }>
  key_uncertainty: string
  watchpoints: string[]
}

export interface EditorialPortfolioReference {
  basis: string
  as_of: string
  source_label: string
  source_url: string
  reader_note: string
}

export interface EngineeringEditorialAnalysis {
  decision_rule: string
}

export type EditorialAnalysis = InvestmentEditorialAnalysis | EngineeringEditorialAnalysis

export interface EditorialDeclinedItem {
  event_id: string
  feed_rank: number
  author: string
  excerpt: string
  reason: string
}

export interface EditorialInsightItem {
  insight_id: string
  local_id: string
  audience: InsightAudience
  rank: number
  rank_rationale: string
  day: string
  title: string
  what_changed: string
  interpretation: string
  next_step: string
  analysis: EditorialAnalysis
  events: EditorialEventLink[]
  citations: EditorialCitation[]
}

export interface EditorialInsightRun {
  run_id: string
  date: string
  status: 'complete'
  created_at: string
  schema_version: string
  draft_schema_version: string
  workspace: {
    run_id: string
    manifest_sha256: string
  }
  source: {
    routing_run_id: string
    cohort_sha256: string
    event_run_id: string
    feed_run_id: string
    rank_version: string
    rank_input_sha256: string
  }
  agent: {
    skill_version: string
    model: string
    notes: string | null
  }
  result_sha256: string
  counts: {
    candidate_events: number
    candidate_pairs: number
    insights_all_audiences: number
    citations_all_audiences: number
    insights: number
    included_candidates: number
    not_selected_candidates: number
  }
}

export interface EditorialInsightsResponse {
  schema_version: string
  available: boolean
  reason?: string | null
  requested_date: string | null
  date: string | null
  audience: InsightAudience
  portfolio_reference: EditorialPortfolioReference | null
  status: 'kept'
  content_kind: 'daily_editorial'
  run: EditorialInsightRun | null
  items: EditorialInsightItem[]
  declined: EditorialDeclinedItem[]
}

export type InvestmentAgentRelevance = 'direct' | 'indirect'
export type InvestmentAgentDirection = 'positive' | 'negative' | 'mixed' | 'unclear'

export interface InvestmentAgentCompanyAssessment {
  ticker: string
  bottom_line: string
  mechanism: string
  affected_driver: string
  direction: InvestmentAgentDirection
  main_uncertainty: string
  next_check: string
}

export interface InvestmentAgentMemoCall {
  turn: number
  call_id: string
  arguments: {
    ticker: string
    connection_type: InvestmentAgentRelevance
    mechanism: string
    affected_operating_driver: string
    why_memo_is_needed: string
  }
}

export interface InvestmentAgentItem {
  run_id: string
  day: string
  development_id: string
  daily_rank: number
  decision: InsightDecision
  development_summary: string
  portfolio_readthrough: string
  company_assessments: InvestmentAgentCompanyAssessment[]
  rejected_after_memo: Array<{ ticker: string; reason: string }>
  no_match_reason: string | null
  company_names: Record<string, string>
  memo_calls: InvestmentAgentMemoCall[]
  source: {
    title: string
    url: string
    author: string
    primary_event_id: string
    source_event_count: number
  } | null
  telemetry: {
    model: string
    reasoning_effort: string
    prompt_version: string
    company_universe_count: number
    memo_count: number
    turn_count: number
    input_tokens: number
    cached_tokens: number
    output_tokens: number
    reasoning_tokens: number
    reported_cost_usd: number
    completed_at: string
  }
}

export interface InvestmentAgentInsightsResponse {
  schema_version: string
  available: boolean
  reason?: string | null
  requested_date: string | null
  date: string | null
  audience: 'investment'
  status: InsightStatus
  content_kind: 'investment_agent'
  run: {
    date: string
    development_count: number
    surfaced_development_count: number
    suppressed_development_count: number
    company_assessment_count: number
    rejected_company_count: number
    model: string
    reasoning_effort: string
    prompt_version: string
    turn_count: number
    input_tokens: number
    cached_tokens: number
    output_tokens: number
    reasoning_tokens: number
    reported_cost_usd: number
  } | null
  items: InvestmentAgentItem[]
}

export type InsightsResponse =
  | CandidateDecisionInsightsResponse
  | EditorialInsightsResponse
  | InvestmentAgentInsightsResponse

export interface InsightDate extends FeedDate {
  content_kind: 'daily_editorial' | 'candidate_decisions' | 'investment_agent'
  candidate_count: number
  included_candidate_count: number
  not_selected_candidate_count: number
}

export interface InsightDates {
  available: boolean
  reason?: string | null
  audience: InsightAudience
  latest_date: string | null
  dates: InsightDate[]
}
