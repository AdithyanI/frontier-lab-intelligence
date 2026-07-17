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

export interface InsightsResponse {
  available: boolean
  reason?: string | null
  audience: InsightAudience
  status: InsightStatus
  run: InsightRun | null
  items: InsightItem[]
}

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
