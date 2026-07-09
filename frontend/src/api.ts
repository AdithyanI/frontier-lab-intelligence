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

export interface XChannel {
  id: number
  handle: string
  display_name: string | null
  bio: string | null
  followers_count: number | null
  seed_rank: number | null
  role: string | null
  github_url: string | null
  graph_follows: number
}

export interface EntityChannel {
  id: number
  kind: string
  key: string
  label: string
  url: string
}

export interface Lab {
  id: number
  slug: string
  name: string
  x_handle: string | null
  website: string | null
  blog_feed: string | null
  github_org: string | null
  arxiv_query: string | null
  notes: string | null
  followers_count: number | null
  linked: boolean
  graph_follows: number
  channels: EntityChannel[]
}

export interface Candidate {
  id: number
  handle: string
  display_name: string | null
  bio: string | null
  followers_count: number | null
  seed_rank: number | null
  pagerank_rank: number | null
  role: string | null
  graph_follows: number
  disagreement: number | null
}

export interface Registry {
  labs: Lab[]
  candidates: Candidate[]
  candidates_pool_total: number
}

export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}
