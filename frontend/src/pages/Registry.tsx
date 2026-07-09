import { useEffect, useMemo, useState } from 'react'
import { getJSON, type Registry as RegistryData } from '../api'

type Kind = 'lab' | 'person'

interface EntityRow {
  key: string
  kind: Kind
  primary: string
  secondary: string | null
  role: string | null
  followers: number | null
  href: string | null
}

const FIRST = 40
const STEP = 40

export default function Registry() {
  const [data, setData] = useState<RegistryData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [kind, setKind] = useState<'all' | Kind>('all')
  const [shown, setShown] = useState(FIRST)

  useEffect(() => {
    getJSON<RegistryData>('/api/registry?limit=150')
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [])

  const entities = useMemo<EntityRow[]>(() => {
    if (!data) return []
    const labs: EntityRow[] = data.labs.map((l) => ({
      key: `lab-${l.slug}`,
      kind: 'lab',
      primary: l.name,
      secondary: l.x_handle ? `@${l.x_handle}` : null,
      role: null,
      followers: l.followers_count,
      href: l.x_handle ? `https://x.com/${l.x_handle}` : null,
    }))
    const people: EntityRow[] = data.candidates.map((c) => ({
      key: `person-${c.id}`,
      kind: 'person',
      primary: c.display_name ?? `@${c.handle}`,
      secondary: c.display_name ? `@${c.handle}` : null,
      role: c.role,
      followers: c.followers_count,
      href: `https://x.com/${c.handle}`,
    }))
    return [...labs, ...people].sort(
      (a, b) => (b.followers ?? -1) - (a.followers ?? -1),
    )
  }, [data])

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return entities.filter((e) => {
      if (kind !== 'all' && e.kind !== kind) return false
      if (!needle) return true
      return (
        e.primary.toLowerCase().includes(needle) ||
        (e.secondary ?? '').toLowerCase().includes(needle) ||
        (e.role ?? '').toLowerCase().includes(needle)
      )
    })
  }, [entities, q, kind])

  useEffect(() => {
    setShown(FIRST)
  }, [q, kind])

  const visible = filtered.slice(0, shown)

  return (
    <div className="page">
      <div className="page-kicker">ENTITY PLANE · WHO WE TRACK</div>
      <h1 className="page-title">Registry</h1>
      <p className="page-sub">
        Every entity the system tracks — labs and people, resolved from raw
        channels. Search, filter, and open any one to see its channels.
      </p>

      {error && (
        <div className="error-note">Could not load registry: {error}</div>
      )}

      <div className="table-tools">
        <input
          className="search"
          type="search"
          placeholder="Search name, handle, or role…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search entities"
        />
        <div className="seg" role="tablist" aria-label="Filter by type">
          {(['all', 'lab', 'person'] as const).map((k) => (
            <button
              key={k}
              role="tab"
              aria-selected={kind === k}
              className={kind === k ? 'is-active' : undefined}
              onClick={() => setKind(k)}
            >
              {k === 'all' ? 'All' : k === 'lab' ? 'Labs' : 'People'}
            </button>
          ))}
        </div>
        {data && (
          <span className="table-count">
            {visible.length.toLocaleString('en-US')} of{' '}
            {filtered.length.toLocaleString('en-US')}
          </span>
        )}
      </div>

      {data && (
        <table>
          <thead>
            <tr>
              <th>Entity</th>
              <th>Type</th>
              <th>Role</th>
              <th className="num">Followers</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((e) => (
              <tr key={e.key}>
                <td className="handle">
                  {e.href ? (
                    <a href={e.href} target="_blank" rel="noreferrer">
                      {e.primary}
                    </a>
                  ) : (
                    e.primary
                  )}
                  {e.secondary && (
                    <div
                      className="muted"
                      style={{ fontSize: 12.5, fontWeight: 400 }}
                    >
                      {e.secondary}
                    </div>
                  )}
                </td>
                <td>
                  <span className={`ent-type ent-type--${e.kind}`}>
                    {e.kind === 'lab' ? 'Lab' : 'Person'}
                  </span>
                </td>
                <td>{e.role ?? <span className="muted">—</span>}</td>
                <td className="num">
                  {e.followers?.toLocaleString('en-US') ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {filtered.length > shown && (
        <button
          className="load-more"
          onClick={() => setShown((n) => n + STEP)}
        >
          Show {Math.min(STEP, filtered.length - shown)} more
        </button>
      )}
    </div>
  )
}
