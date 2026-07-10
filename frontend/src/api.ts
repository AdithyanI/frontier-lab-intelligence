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
  counts: Record<RegistryGroup, number>
}

export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}
