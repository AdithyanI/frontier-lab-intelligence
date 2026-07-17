import type { FeedDate } from './evidence'

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
