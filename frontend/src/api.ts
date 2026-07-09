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
  digg_rank: number | null
  role: string | null
  github_url: string | null
  tracked_followers: number
}

export interface Lab {
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
  tracked_followers: number
}

export interface Candidate {
  id: number
  handle: string
  display_name: string | null
  bio: string | null
  followers_count: number | null
  digg_rank: number | null
  pagerank_rank: number | null
  role: string | null
  tracked_followers: number
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
