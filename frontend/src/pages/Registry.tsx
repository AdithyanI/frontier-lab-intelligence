import { useEffect, useMemo, useState } from 'react'
import { getJSON, type Registry as RegistryData } from '../api'

export default function Registry() {
  const [data, setData] = useState<RegistryData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [role, setRole] = useState('all')

  useEffect(() => {
    getJSON<RegistryData>('/api/registry?limit=150')
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [])

  const roles = useMemo(() => {
    if (!data) return []
    const set = new Set<string>()
    for (const c of data.candidates) if (c.role) set.add(c.role)
    return Array.from(set).sort()
  }, [data])

  const filtered = useMemo(() => {
    if (!data) return []
    const needle = q.trim().toLowerCase()
    return data.candidates.filter((c) => {
      if (role !== 'all' && c.role !== role) return false
      if (!needle) return true
      return (
        c.handle.toLowerCase().includes(needle) ||
        (c.display_name ?? '').toLowerCase().includes(needle)
      )
    })
  }, [data, q, role])

  return (
    <div className="page">
      <div className="page-kicker">THE REGISTRY · WHO WE TRACK</div>
      <h1 className="page-title">Registry</h1>
      <p className="page-sub">
        Every entity the system tracks — real people and labs, resolved from
        raw accounts, not the accounts themselves. Labs are hand-curated: a
        small, known list with verified official channels. People are still
        candidates below: ranked by evidence, not yet promoted by a human or
        an automated curator.
      </p>

      {error && (
        <div className="error-note">Could not load registry: {error}</div>
      )}

      <section className="registry-section">
        <h2 className="registry-h2">Labs</h2>
        <p className="registry-lede">
          10 organizations, chosen by judgment — the case is obvious: founders
          and research leads are named publicly, and official channels are
          easy to verify by hand. Each linked lab is anchored to its X account
          inside the same graph as the people below.
        </p>
        {data && (
          <table>
            <thead>
              <tr>
                <th>Lab</th>
                <th>Status</th>
                <th>X account</th>
                <th>Channels</th>
                <th className="num">Followers</th>
              </tr>
            </thead>
            <tbody>
              {data.labs.map((l) => (
                <tr key={l.slug}>
                  <td className="handle">{l.name}</td>
                  <td>
                    <span className={`status-pill tone-${l.status}`}>
                      {l.status}
                    </span>
                  </td>
                  <td>
                    {l.x_handle ? (
                      <a
                        href={`https://x.com/${l.x_handle}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        @{l.x_handle}
                      </a>
                    ) : (
                      <span className="muted">—</span>
                    )}
                    {l.x_handle && !l.linked && (
                      <span className="muted small-note"> (not in graph)</span>
                    )}
                  </td>
                  <td>
                    <div className="channel-list">
                      {l.website && (
                        <a href={l.website} target="_blank" rel="noreferrer">
                          web
                        </a>
                      )}
                      {l.github_org && (
                        <a
                          href={`https://github.com/${l.github_org}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          github
                        </a>
                      )}
                      {l.blog_feed && <span className="muted">blog</span>}
                      {l.arxiv_query && <span className="muted">arXiv</span>}
                    </div>
                  </td>
                  <td className="num">
                    {l.followers_count ? (
                      l.followers_count.toLocaleString('en-US')
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="registry-section">
        <h2 className="registry-h2">People — candidates</h2>
        <div className="registry-status-banner">
          <span className="status-pill tone-candidate">0 tracked</span>
          <p>
            No person has been promoted into the registry yet — the
            auto-curation pass (an LLM reading each account&rsquo;s evidence
            and deciding track / reject with cited reasons) hasn&rsquo;t run.
            Below is the candidate pool ranked by evidence, for you to look at
            while that gets built.
          </p>
        </div>
        <p className="registry-lede">
          Two independent rankings, side by side: <b>Digg rank</b> (raw
          follower-weighted attention) and <b>PageRank</b> (importance from
          who follows whom in the graph). Large disagreement between them is
          itself a signal worth a second look — e.g. SSI ranks #401 by
          followers but #24 by graph structure: the community pays it
          outsized attention despite a modest follower count.
        </p>
        <div className="table-tools">
          <input
            className="search"
            type="search"
            placeholder="Search handle or name…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search candidates"
          />
          <select
            className="role-select"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            aria-label="Filter by role"
          >
            <option value="all">All roles</option>
            {roles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          {data && (
            <span className="table-count">
              {filtered.length.toLocaleString('en-US')} shown ·{' '}
              {data.candidates_pool_total.toLocaleString('en-US')} in pool
            </span>
          )}
        </div>
        {data && (
          <table>
            <thead>
              <tr>
                <th>Account</th>
                <th>Role</th>
                <th className="num">Digg rank</th>
                <th className="num">PageRank</th>
                <th>Disagreement</th>
                <th className="num">Followers</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id}>
                  <td className="handle">
                    <a
                      href={`https://x.com/${c.handle}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      @{c.handle}
                    </a>
                    {c.display_name && (
                      <div
                        className="muted"
                        style={{ fontSize: 12.5, fontWeight: 400 }}
                      >
                        {c.display_name}
                      </div>
                    )}
                  </td>
                  <td>{c.role ?? <span className="muted">—</span>}</td>
                  <td className="num">
                    {c.digg_rank ?? <span className="muted">—</span>}
                  </td>
                  <td className="num">
                    {c.pagerank_rank ?? <span className="muted">—</span>}
                  </td>
                  <td>{disagreementLabel(c.disagreement)}</td>
                  <td className="num">
                    {c.followers_count?.toLocaleString('en-US') ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}

function disagreementLabel(d: number | null) {
  if (d === null) return <span className="muted">—</span>
  if (Math.abs(d) < 30) return <span className="muted">aligned</span>
  const strong = Math.abs(d) >= 100
  return (
    <span className={strong ? 'disagreement-strong' : undefined}>
      {d > 0 ? `graph +${d}` : `digg +${-d}`}
    </span>
  )
}
