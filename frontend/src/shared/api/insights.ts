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

export interface InvestmentAgentCompany {
  ticker: string
  bet_id: string
  threshold_met: boolean
  impact: string
}

export interface InvestmentAgentConnection {
  mechanism: string
  companies: InvestmentAgentCompany[]
}

export interface InvestmentAgentMemoCall {
  turn: number
  call_id: string
  arguments: {
    ticker: string
    connection_type: InvestmentAgentRelevance
    mechanism: string
    candidate_bet_id: string
    why_memo_is_needed: string
  }
}

export interface InvestmentAgentItem {
  run_id: string
  day: string
  development_id: string
  daily_rank: number
  decision: InsightDecision
  headline: string
  what_changed: string
  connections: InvestmentAgentConnection[]
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
    company_connection_count: number
    memo_rejected_count: number
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
