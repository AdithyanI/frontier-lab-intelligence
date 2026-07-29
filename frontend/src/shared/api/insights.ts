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

export type InvestmentAgentRelevance = 'direct' | 'indirect'
export type InvestmentAgentDirection = 'positive' | 'negative' | 'mixed' | 'unclear'

export type InvestmentAgentMateriality = 'material' | 'immaterial' | 'unknown'

export interface InvestmentAgentExposure {
  ticker: string
  affected_driver: string
  direction: InvestmentAgentDirection
  materiality: InvestmentAgentMateriality
  size_basis?: string | null
  impact?: string
  /** Superseded by `impact` in investment-agent-v11; kept so earlier runs still render. */
  note?: string
}

export interface InvestmentAgentCompanyAssessment {
  mechanism_title: string
  mechanism: string
  splits: boolean
  exposures: InvestmentAgentExposure[]
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
  investment_headline: string
  development_summary: string
  portfolio_readthrough: string
  prior_assumption: string | null
  company_assessments: InvestmentAgentCompanyAssessment[]
  rejected_after_memo: Array<{ ticker: string; reason: string }>
  no_match_reason: string | null
  company_names: Record<string, string>
  memo_calls: InvestmentAgentMemoCall[]
  provenance: {
    primary_event_id: string
    source_event_count: number
    original_post: {
      url: string
      author: string
    } | null
    artifacts: Array<{
      artifact_id: string
      title: string
      url: string
    }>
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
  development_count: number
  surfaced_development_count: number
  suppressed_development_count: number
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

export type InsightsResponse = InvestmentAgentInsightsResponse

export interface InsightDate extends FeedDate {
  content_kind: 'investment_agent'
}

export interface InsightDates {
  available: boolean
  reason?: string | null
  audience: InsightAudience
  latest_date: string | null
  dates: InsightDate[]
}
