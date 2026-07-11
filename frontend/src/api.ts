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

export async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}
