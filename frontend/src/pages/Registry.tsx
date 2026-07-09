import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  getJSON,
  type EntityChannel,
  type Registry as RegistryData,
} from '../api'

type Kind = 'lab' | 'person'

interface EntityRow {
  key: string
  kind: Kind
  primary: string
  handle: string | null
  role: string | null
  followers: number | null
  graphFollows: number
  bio: string | null
  seedRank: number | null
  pagerankRank: number | null
  notes: string | null
  channels: EntityChannel[]
}

const FIRST = 40
const STEP = 40

const fmt = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US')

export default function Registry() {
  const [data, setData] = useState<RegistryData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [kind, setKind] = useState<'all' | Kind>('all')
  const [shown, setShown] = useState(FIRST)
  const [selected, setSelected] = useState<EntityRow | null>(null)

  useEffect(() => {
    getJSON<RegistryData>('/api/registry?limit=5000')
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [])

  const entities = useMemo<EntityRow[]>(() => {
    if (!data) return []
    const labs: EntityRow[] = data.labs.map((l) => ({
      key: `lab-${l.slug}`,
      kind: 'lab',
      primary: l.name,
      handle: l.x_handle,
      role: null,
      followers: l.followers_count,
      graphFollows: l.graph_follows,
      bio: null,
      seedRank: null,
      pagerankRank: null,
      notes: l.notes,
      channels: l.channels ?? [],
    }))
    const people: EntityRow[] = data.candidates.map((c) => ({
      key: `person-${c.id}`,
      kind: 'person',
      primary: c.display_name ?? `@${c.handle}`,
      handle: c.handle,
      role: c.role,
      followers: c.followers_count,
      graphFollows: c.graph_follows,
      bio: c.bio,
      seedRank: c.seed_rank,
      pagerankRank: c.pagerank_rank,
      notes: null,
      channels: [],
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
        (e.handle ?? '').toLowerCase().includes(needle) ||
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
        channels. Open any row to see its full profile.
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
            {fmt(visible.length)} of {fmt(filtered.length)}
          </span>
        )}
      </div>

      {data && (
        <table className="ent-table">
          <thead>
            <tr>
              <th>Entity</th>
              <th>Type</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((e) => (
              <tr
                key={e.key}
                className="ent-row"
                onClick={() => setSelected(e)}
                tabIndex={0}
                onKeyDown={(ev) => {
                  if (ev.key === 'Enter' || ev.key === ' ') {
                    ev.preventDefault()
                    setSelected(e)
                  }
                }}
              >
                <td className="ent-name">{e.primary}</td>
                <td>
                  <span className={`ent-type ent-type--${e.kind}`}>
                    {e.kind === 'lab' ? 'Lab' : 'Person'}
                  </span>
                </td>
                <td>{e.role ?? <span className="muted">—</span>}</td>
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
          Show {fmt(Math.min(STEP, filtered.length - shown))} more
        </button>
      )}

      <EntityCard entity={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

function EntityCard({
  entity,
  onClose,
}: {
  entity: EntityRow | null
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dlg = ref.current
    if (!dlg) return
    if (entity && !dlg.open) dlg.showModal()
    if (!entity && dlg.open) dlg.close()
  }, [entity])

  if (!entity) return <dialog ref={ref} className="ent-card" onClose={onClose} />

  const facts: { label: string; value: ReactNode }[] = []
  facts.push({
    label: 'Type',
    value: entity.kind === 'lab' ? 'Lab' : 'Person',
  })
  if (entity.role) facts.push({ label: 'Role', value: entity.role })
  facts.push({ label: 'Followers', value: fmt(entity.followers) })
  facts.push({ label: 'Graph follows', value: fmt(entity.graphFollows) })
  if (entity.kind === 'person') {
    facts.push({ label: 'Seed rank', value: fmt(entity.seedRank) })
    facts.push({ label: 'PageRank', value: fmt(entity.pagerankRank) })
  }

  const xUrl = entity.handle ? `https://x.com/${entity.handle}` : null

  return (
    <dialog
      ref={ref}
      className="ent-card"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose()
      }}
    >
      <div className="ent-card-inner">
        <header className="ent-card-head">
          <div>
            <span className={`ent-type ent-type--${entity.kind}`}>
              {entity.kind === 'lab' ? 'Lab' : 'Person'}
            </span>
            <h2>{entity.primary}</h2>
          </div>
          <button
            className="ent-card-close"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </header>

        {(entity.bio || entity.notes) && (
          <p className="ent-card-bio">{entity.bio ?? entity.notes}</p>
        )}

        <dl className="ent-card-facts">
          {facts.map((f) => (
            <div key={f.label}>
              <dt>{f.label}</dt>
              <dd>{f.value}</dd>
            </div>
          ))}
        </dl>

        {entity.channels.length > 0 && (
          <div className="ent-card-channels">
            <div className="ent-card-label">Channels</div>
            <ul>
              {entity.channels.map((c) => (
                <li key={c.id}>
                  <a href={c.url} target="_blank" rel="noreferrer">
                    <span className="ent-ch-kind">{c.kind}</span>
                    <span className="ent-ch-label">{c.label}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {xUrl && (
          <footer className="ent-card-foot">
            <a
              className="ent-x-tag"
              href={xUrl}
              target="_blank"
              rel="noreferrer"
            >
              <span>𝕏</span>
              @{entity.handle}
              <span className="ent-x-go">↗</span>
            </a>
          </footer>
        )}
      </div>
    </dialog>
  )
}
