import type { FeedDate } from './evidence'

export type InsightAudience = 'investment' | 'ai_engineering'
export type InsightDecision = 'surface' | 'suppress'
export type InsightStatus = 'kept' | 'suppressed' | 'all'

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
export type EngineeringAction = 'test' | 'adopt' | 'watch' | 'ignore'

export interface EditorialEventLink {
  event_id: string
  feed_rank: number
  role: EditorialEventRole
  reason: string
  root_url: string
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
  system_surface: string
  technical_implication: string
  recommended_action: EngineeringAction
  experiment: {
    hypothesis: string
    smallest_test: string
    success_metric: string
    stop_condition: string
  }
  constraints: string[]
}

export type EditorialAnalysis = InvestmentEditorialAnalysis | EngineeringEditorialAnalysis

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
}

export type InsightsResponse = CandidateDecisionInsightsResponse | EditorialInsightsResponse

export interface InsightDate extends FeedDate {
  suppressed_count: number
  evaluated_count: number
}

export interface InsightDates {
  available: boolean
  reason?: string | null
  audience: InsightAudience
  latest_date: string | null
  dates: InsightDate[]
}
