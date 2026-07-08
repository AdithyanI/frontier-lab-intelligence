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

export interface Account {
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

export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}
