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
  bio: string | null
  channels: EntityChannel[]
}

export interface Registry {
  entities: Entity[]
  total: number
  filtered_total: number
  counts: Record<RegistryGroup, number>
  limit: number
  offset: number
  direction: 'asc' | 'desc'
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
  sources: number
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
  high_support_amplifiers: number
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
  relationship: 'reply' | 'quote' | 'retweet' | 'related'
  relation_type: 'reply_parent' | 'same_conversation' | 'quote' | 'retweet' | null
  target_post_id: string | null
  parent_post_id: string | null
  depth: number
  same_author_as_root: boolean
}

export interface SignalEvent {
  event_id: string
  is_grouped: boolean
  root: FeedItem
  why_grouped: string[]
  anchor_types: Array<'same_target' | 'same_conversation'>
  member_count: number
  link_count: number
  author_count: number
  registry_account_count: number
  first_hand_count: number
  amplifiers: FeedAmplifier[]
  peak_attention_score: number
  peak_public_interactions: number
  latest_evidence_at: string
  evidence: EventEvidence[]
}

export interface EventResponse {
  available: boolean
  reason?: string
  date?: string
  lane?: 'all' | 'network' | 'firsthand'
  sort?: 'attention' | 'recent' | 'engagement'
  query?: string
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

export async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}
