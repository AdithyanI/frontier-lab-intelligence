import { getCachedJSON } from './client'

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
  network_position: number
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

export interface FeedRankComponents {
  version: 'daily-rank-v2'
  trusted_votes: number
  voters: FeedAmplifier[]
  mean_voter_position: number
  author_position: number
  public_interactions: number
  decided_at_layer: 1 | 2 | 3 | 4 | 5 | null
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
  sort?: 'rank' | 'recent' | 'engagement'
  query?: string
  event_id?: string
  total?: number
  limit?: number
  offset?: number
  run?: FeedRun
  rank_contract?: {
    version: string
    kind: string
    layers: string[]
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
  relationship: 'reply' | 'quote' | 'retweet' | 'related'
  relation_type: 'reply_parent' | 'primary_thread' | 'quote' | 'retweet' | null
  target_post_id: string | null
  parent_post_id: string | null
  parent_missing: boolean
  depth: number
  same_author_as_root: boolean
}

export interface FeedEvent {
  event_id: string
  canonical_root_post_id: string
  presentation_root_post_id: string
  semantic_snapshot_sha256: string
  first_activity_day: string
  is_grouped: boolean
  root: FeedItem
  why_grouped: string[]
  anchor_types: Array<'same_target' | 'reply_parent' | 'conversation_root'>
  member_count: number
  lifetime_member_count: number
  day_member_count: number
  activity_days: string[]
  link_count: number
  author_count: number
  registry_entity_count: number
  first_hand_count: number
  amplifiers: FeedAmplifier[]
  daily_rank: number
  rank_components: FeedRankComponents
  latest_evidence_at: string
  evidence: EventEvidence[]
  relationship_counts: {
    author_updates: number
    replies: number
    quotes: number
    retweets: number
    related: number
  }
  routing_state: 'evaluated' | 'not_selected' | 'stale' | 'unavailable'
  audience_routing: {
    feed_rank: number
    semantic_snapshot_sha256: string
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
  sort?: 'rank' | 'recent' | 'engagement'
  query?: string
  projection?: 'day' | 'week'
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
    rank_version: string
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
  include_evidence?: boolean
  run?: {
    run_id: string
    feed_run_id: string
    clustering_contract: string
  }
  rank_contract?: FeedResponse['rank_contract']
  items?: FeedEvent[]
}

export interface EventPageQuery {
  date: string
  sort: 'rank' | 'recent' | 'engagement'
  routingFilter: 'all' | 'relevant' | 'not_relevant' | 'not_evaluated'
  query: string
  eventId?: string
  offset?: number
  limit?: number
}

export function eventPageUrl({
  date,
  sort,
  routingFilter,
  query,
  eventId,
  offset = 0,
  limit = 20,
}: EventPageQuery) {
  const params = new URLSearchParams({
    date,
    lane: 'all',
    sort,
    routing: routingFilter,
    q: query,
    event_id: eventId ?? '',
    include_evidence: 'false',
    limit: String(limit),
    offset: String(offset),
  })
  return `/api/events?${params}`
}

export function prefetchExactEvent(date: string, eventId: string) {
  void getCachedJSON<EventResponse>(
    eventPageUrl({
      date,
      sort: 'rank',
      routingFilter: 'all',
      query: '',
      eventId,
    }),
  ).catch(() => undefined)
}
