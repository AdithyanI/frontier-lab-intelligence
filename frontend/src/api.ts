export interface StageStat {
  label: string
  value: number
}

export interface Stage {
  id: string
  name: string
  state: 'live' | 'in-progress' | 'pending'
  summary: string
  stats: StageStat[]
}

export interface EntityChannel {
  id: number
  kind: string
  key: string
  label: string | null
  url: string | null
}

export type EntityKind =
  | 'person'
  | 'organization'
  | 'unsure'
  | 'unknown'

export type RegistryState = 'active' | 'rejected'
export type RegistryGroup = EntityKind | 'rejected'

export interface Entity {
  id: number
  slug: string
  name: string
  kind: EntityKind
  kind_reason: string | null
  registry_state: RegistryState
  rejection_reason_code: string | null
  rejection_reason: string | null
  rejection_source: string | null
  rejection_evidence_url: string | null
  followers_count: number | null
  reach_rank: number | null
  network_rank: number | null
  network_follow_count: number | null
  network_follow_share: number | null
  network_source_total: number | null
  network_rank_total: number | null
  network_channel_count: number | null
  bio: string | null
  channels: EntityChannel[]
}

export interface Registry {
  entities: Entity[]
  total: number
  filtered_total: number
  counts: Record<RegistryGroup, number>
  reach_rank_total: number
  network_context: {
    snapshot_id: string
    snapshot_completed_at: string | null
    network_source_total: number
    network_rank_total: number
    parent_snapshot_id: string | null
    incremental: boolean
  } | null
  limit: number
  offset: number
  sort: 'reach' | 'network'
  direction: 'asc' | 'desc'
}

export interface RegistryIntakeResult {
  audit_id: number
  handle: string
  mode: 'screen' | 'direct'
  outcome: 'existing' | 'active' | 'rejected'
  entity_id: number | null
  registry_decision: 'existing' | 'keep' | 'remove' | 'review' | 'manual_keep'
  decision_reason: string
  kind: EntityKind | null
  kind_reason: string | null
  followers_count: number | null
  entity: Entity | null
}

export interface RankingNode {
  rank: number
  cohort_follow_count: number
  cohort_follow_share: number
  x_id: string
  handle: string
  display_name: string | null
  followers_count: number | null
  registry_state: 'active' | 'unknown'
  entity_id: number | null
  entity_kind: string | null
  entity_name: string | null
}

export interface RankingRun {
  algorithm: string
  snapshot_id: string
  completed_at: string
  source_accounts: number
  source_entities: number
  edges: number
  ranked_accounts: number
  active_accounts: number
  unknown_accounts: number
}

export interface Rankings {
  available: boolean
  reason?: string
  run?: RankingRun
  nodes?: RankingNode[]
}

export interface RankingFollower {
  x_id: string
  handle: string
  display_name: string | null
  entity_name: string | null
  rank: number | null
  cohort_follow_count: number | null
}

export interface RankingFollowers {
  available: boolean
  x_id?: string
  total?: number
  followers?: RankingFollower[]
}

export interface FeedDate {
  day: string
  item_count: number
}

export interface FeedDates {
  available: boolean
  reason?: string
  latest_complete_date?: string
  date_from?: string
  date_to?: string
  run_id?: string
  dates?: FeedDate[]
}

export interface FeedAuthor {
  x_id: string | null
  handle: string
  name: string
  entity_id: number | null
  entity_name: string | null
  entity_kind: string | null
}

export interface FeedAmplifier {
  entity_id: number
  entity_name: string
  entity_kind: string
  handle: string
  relation_type: 'quote' | 'retweet'
  network_support: number
  source_url: string
}

export interface FeedMetrics {
  likes: number | null
  replies: number | null
  reposts: number | null
  quotes: number | null
  views: number | null
  bookmarks: number | null
}

export interface FeedScoreComponents {
  registry_amplifiers: number
  originator_network_support: number
  originator_network_rank: number | null
  public_interactions: number
  network_attention_percentile: number
  originator_support_percentile: number
  public_engagement_percentile: number
}

export interface FeedItem {
  post_id: string
  author: FeedAuthor
  published_at: string
  text: string
  url: string
  post_type: 'original' | 'quote' | 'retweet' | 'reply'
  observed_directly: boolean
  context: { target_post_id: string; target_handle: string } | null
  amplifiers: FeedAmplifier[]
  metrics: FeedMetrics
  attention_score: number
  score_components: FeedScoreComponents
}

export interface FeedRun {
  run_id: string
  date_from: string
  date_to: string
  source_post_count: number
  normalized_post_count: number
  relation_count: number
  ranking: {
    run_id: string
    algorithm: string
    snapshot_id: string
    completed_at: string
  } | null
}

export interface FeedResponse {
  available: boolean
  reason?: string
  date?: string
  lane?: 'all' | 'network' | 'firsthand'
  sort?: 'attention' | 'recent' | 'engagement'
  query?: string
  event_id?: string
  total?: number
  limit?: number
  offset?: number
  run?: FeedRun
  score_formula?: {
    version: string
    network_attention_weight: number
    originator_support_weight: number
    public_engagement_weight: number
    note: string
  }
  items?: FeedItem[]
}

export interface EventEvidence {
  post_id: string
  author: {
    handle: string
    name: string
    entity_id: number | null
    entity_name: string | null
  }
  published_at: string
  text: string
  url: string
  post_type: 'original' | 'quote' | 'retweet' | 'reply'
  observed_directly: boolean
  day: string
  is_new_on_day: boolean
  relationship: 'reply' | 'quote' | 'retweet' | 'related'
  relation_type: 'reply_parent' | 'quote' | 'retweet' | null
  target_post_id: string | null
  parent_post_id: string | null
  parent_missing: boolean
  depth: number
  same_author_as_root: boolean
}

export interface SignalEvent {
  event_id: string
  canonical_root_post_id: string
  presentation_root_post_id: string
  snapshot_cutoff: string
  snapshot_content_sha256: string
  first_activity_day: string
  previous_activity_day: string | null
  is_continuation: boolean
  is_grouped: boolean
  root: FeedItem
  why_grouped: string[]
  anchor_types: Array<'same_target' | 'reply_parent'>
  member_count: number
  lifetime_member_count: number
  day_member_count: number
  prior_context_count: number
  link_count: number
  author_count: number
  registry_account_count: number
  first_hand_count: number
  amplifiers: FeedAmplifier[]
  daily_rank: number
  peak_attention_score: number
  daily_score_basis: {
    post_id: string
    author: FeedAuthor
    published_at: string
    attention_score: number
    score_components: FeedScoreComponents
  }
  peak_public_interactions: number
  latest_evidence_at: string
  evidence: EventEvidence[]
  audience_routing: {
    feed_rank: number
    snapshot_content_sha256: string
    evidence_sha256: string
    input_sha256: string
    ai_engineering: {
      relevant: boolean
      reason: string
    }
    investment: {
      relevant: boolean
      reason: string
    }
  } | null
}

export interface EventResponse {
  available: boolean
  reason?: string
  date?: string
  lane?: 'all' | 'network' | 'firsthand'
  sort?: 'attention' | 'recent' | 'engagement'
  query?: string
  routing_filter?:
    | 'all'
    | 'relevant'
    | 'not_relevant'
    | 'not_evaluated'
  routing_counts?: {
    all: number
    relevant: number
    not_relevant: number
    not_evaluated: number
  }
  daily_rank_total?: number
  audience_routing_run?: {
    run_id: string
    model: string
    reasoning_effort: string
    prompt_version: string
    source_event_run_id: string
    source_feed_run_id: string
    selection_kind: 'top_ranked' | 'single_event' | 'review_cohort'
    selection_limit: number | null
    expected_count: number
    completed_count: number
    updated_at: string
  } | null
  total?: number
  limit?: number
  offset?: number
  run?: {
    run_id: string
    feed_run_id: string
    clustering_contract: 'exact-structural-v1'
    cluster_count: number
    member_count: number
    link_count: number
  }
  score_formula?: FeedResponse['score_formula']
  items?: SignalEvent[]
}

export type ArtifactKind =
  | 'paper'
  | 'repository'
  | 'announcement'
  | 'article'
  | 'video'
  | 'other'

export type ArtifactType = 'web' | 'x_article' | 'document' | 'repository' | 'video'

export type ArtifactFetchState =
  | 'catalogued'
  | 'fetching'
  | 'ready'
  | 'retryable'
  | 'unavailable'

export interface ArtifactItem {
  artifact_id: string
  canonical_url: string
  host: string
  artifact_kind: ArtifactKind
  artifact_type: ArtifactType
  title: string | null
  first_seen_at: string
  last_seen_at: string
  observation_count: number
  best_source_rank: number
  source_published_at: string
  first_source_published_at: string | null
  last_source_published_at: string | null
  source_kind: string | null
  source_provider: string | null
  source_url: string | null
  source_event_id: string | null
  fetch_state: ArtifactFetchState
  fetch_method: string | null
  fetched_at: string | null
  extractor_contract: string | null
  text_char_count: number | null
  error_code: string | null
}

export interface ArtifactLibrary {
  available: boolean
  reason?: string
  items: ArtifactItem[]
  total: number
  matching_total: number
  date?: string
  query?: string
  counts?: Record<ArtifactFetchState, number>
  limit: number
  offset: number
}

export interface ArtifactDates {
  available: boolean
  reason?: string
  latest_date?: string
  date_from?: string
  date_to?: string
  dates: FeedDate[]
}

export interface InsightCitation {
  quote: string
  url: string
  source_type: string
  source_id: string
  author: string | null
  title: string | null
  source_sha256: string
  block_index: number
  section_ordinal: number | null
  char_start: number
  char_end: number
}

export type InsightAudience = 'investment' | 'ai_engineering'

export type InsightClaimPosture =
  | 'directly_documented'
  | 'first_party_report'
  | 'third_party_observation'
  | 'opinion_or_forecast'

export interface InvestmentInsightFields {
  investment_implication: string
  what_to_watch: string
}

export type EngineeringActionType =
  | 'investigate'
  | 'reproduce'
  | 'benchmark'
  | 'prototype'
  | 'regression_test'
  | 'monitor'

export interface EngineeringInsightFields {
  action_type: EngineeringActionType
  engineering_action: string
  validation_boundary: string
}

export interface InsightItem {
  candidate_id: string
  event_id: string
  day: string
  editorial_rank: number
  feed_rank: number | null
  decision_value: string
  claim: string
  claim_posture: InsightClaimPosture
  why_it_matters: string
  audience_fields: InvestmentInsightFields | EngineeringInsightFields
  citation: InsightCitation
}

export type ExtractedInsightItem = Omit<
  InsightItem,
  'editorial_rank' | 'decision_value'
>

export interface ExtractedInsightRun {
  run_id: string
  day: string
  audience: InsightAudience
  candidate_count: number
  complete_count: number
  extracted_count: number
}

export interface ExtractedInsightsResponse {
  available: boolean
  reason?: string | null
  audience: InsightAudience
  run: ExtractedInsightRun | null
  items: ExtractedInsightItem[]
}

export interface InsightRun {
  run_id: string
  day: string
  audience: InsightAudience
  prompt_version: string
  editor_prompt_version: string
  model: string
  candidate_count: number
  extracted_count: number
  selected_count: number
  failed_count: number
  reported_cost_usd: number
  cache_hit_requests: number
  cache_eligible_requests: number
}

export interface InsightsResponse {
  available: boolean
  reason?: string | null
  audience: InsightAudience
  run: InsightRun | null
  items: InsightItem[]
}

export interface InsightDates {
  available: boolean
  reason?: string | null
  audience: InsightAudience
  latest_date: string | null
  dates: FeedDate[]
}

export async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}

export async function postJSON<T>(
  url: string,
  body: unknown,
): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as {
      detail?: string | { message?: string; hint?: string }
    } | null
    const detail = payload?.detail
    const message = typeof detail === 'string'
      ? detail
      : [detail?.message, detail?.hint].filter(Boolean).join(' ')
    throw new Error(message || `Request failed with status ${response.status}.`)
  }
  return response.json() as Promise<T>
}

const jsonCache = new Map<string, unknown>()
const jsonRequests = new Map<string, Promise<unknown>>()

/**
 * Cache immutable/read-model API responses for the lifetime of this page.
 * Concurrent callers share one request, so route prefetch and the destination
 * page never duplicate the same expensive read.
 */
export function getCachedJSON<T>(url: string): Promise<T> {
  if (jsonCache.has(url)) return Promise.resolve(jsonCache.get(url) as T)

  const pending = jsonRequests.get(url)
  if (pending) return pending as Promise<T>

  const request = getJSON<T>(url)
    .then((value) => {
      jsonCache.set(url, value)
      return value
    })
    .finally(() => jsonRequests.delete(url))

  jsonRequests.set(url, request)
  return request
}
