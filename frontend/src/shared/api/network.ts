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

