import { useEffect, useMemo, useRef, useState } from 'react'
import { siArxiv, siGithub, siRss, siX } from 'simple-icons'
import {
  getJSON,
  type Entity,
  type EntityChannel,
  type EntityKind,
  type Registry as RegistryData,
} from '../api'

type KindFilter = 'all' | EntityKind

const BRAND_ICON: Record<string, string> = {
  github: siGithub.path,
  x: siX.path,
  arxiv: siArxiv.path,
  blog: siRss.path,
}

const FIRST = 40
const STEP = 40

const fmt = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US')

const typeLabel = (kind: EntityKind) =>
  kind === 'lab' ? 'Lab' : kind === 'person' ? 'Person' : 'Unknown'

function ChannelGlyph({ kind }: { kind: string }) {
  if (kind === 'website') {
    return (
      <svg
        className="ch-ico"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18" />
        <path d="M12 3a15 15 0 0 1 4 9 15 15 0 0 1-4 9 15 15 0 0 1-4-9 15 15 0 0 1 4-9Z" />
      </svg>
    )
  }
  const path = BRAND_ICON[kind]
  if (!path) return null
  return (
    <svg className="ch-ico" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d={path} />
    </svg>
  )
}

function channelLabel(channel: EntityChannel): string {
  switch (channel.kind) {
    case 'website':
      try {
        return channel.url
          ? new URL(channel.url).hostname.replace(/^www\./, '')
          : 'Website'
      } catch {
        return 'Website'
      }
    case 'github':
      return channel.key || channel.label || 'GitHub'
    case 'arxiv':
      return 'arXiv'
    case 'blog':
      return 'Blog'
    default:
      return channel.label || channel.key
  }
}

export default function Registry() {
  const [data, setData] = useState<RegistryData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [kind, setKind] = useState<KindFilter>('all')
  const [shown, setShown] = useState(FIRST)
  const [selected, setSelected] = useState<Entity | null>(null)

  useEffect(() => {
    getJSON<RegistryData>('/api/registry?limit=5000')
      .then(setData)
      .catch((cause) => setError(String(cause)))
  }, [])

  const filtered = useMemo(() => {
    if (!data) return []
    const needle = query.trim().toLowerCase()
    return data.entities.filter((entity) => {
      if (kind !== 'all' && entity.kind !== kind) return false
      if (!needle) return true
      return (
        entity.name.toLowerCase().includes(needle) ||
        (entity.bio ?? '').toLowerCase().includes(needle) ||
        entity.channels.some((channel) =>
          channel.key.toLowerCase().includes(needle),
        )
      )
    })
  }, [data, kind, query])

  useEffect(() => setShown(FIRST), [kind, query])

  const visible = filtered.slice(0, shown)
  const filters: { key: KindFilter; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: data?.total ?? 0 },
    { key: 'lab', label: 'Labs', count: data?.counts.lab ?? 0 },
    { key: 'person', label: 'People', count: data?.counts.person ?? 0 },
    { key: 'unknown', label: 'Unknown', count: data?.counts.unknown ?? 0 },
  ]

  return (
    <div className="page">
      <div className="page-kicker">ENTITY UNIVERSE · WHO WE HAVE OBSERVED</div>
      <h1 className="page-title">Registry</h1>
      <p className="page-sub">
        {data
          ? `${fmt(data.total)} identities. ${fmt(data.counts.lab)} known labs; ${fmt(data.counts.unknown)} remain unknown until classification.`
          : 'Every observed channel resolves to one entity. Unresolved identities remain unknown.'}
      </p>

      {error && (
        <div className="error-note">Could not load registry: {error}</div>
      )}

      <div className="table-tools">
        <input
          className="search"
          type="search"
          placeholder="Search name, handle, or bio…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="Search entities"
        />
        <div className="seg" role="tablist" aria-label="Filter by type">
          {filters.map((filter) => (
            <button
              key={filter.key}
              role="tab"
              aria-selected={kind === filter.key}
              className={kind === filter.key ? 'is-active' : undefined}
              onClick={() => setKind(filter.key)}
            >
              {filter.label}
              <span className="seg-count">{fmt(filter.count)}</span>
            </button>
          ))}
        </div>
        {data && (
          <span className="table-count">
            {fmt(visible.length)} of {fmt(filtered.length)}
          </span>
        )}
      </div>

      {!data && !error && <div className="registry-loading skeleton" />}

      {data && visible.length > 0 && (
        <table className="ent-table">
          <thead>
            <tr>
              <th>Entity</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((entity) => {
              const xChannel = entity.channels.find((channel) => channel.kind === 'x')
              return (
                <tr
                  key={entity.id}
                  className="ent-row"
                  onClick={() => setSelected(entity)}
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      setSelected(entity)
                    }
                  }}
                >
                  <td>
                    <span className="ent-name">{entity.name}</span>
                    {xChannel && (
                      <span className="ent-handle">@{xChannel.key}</span>
                    )}
                  </td>
                  <td>
                    <span className={`ent-type ent-type--${entity.kind}`}>
                      {typeLabel(entity.kind)}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      {data && visible.length === 0 && (
        <div className="registry-empty">
          {kind === 'person' && !query
            ? 'No people have been classified yet.'
            : 'No entities match this view.'}
        </div>
      )}

      {filtered.length > shown && (
        <button
          className="load-more"
          onClick={() => setShown((current) => current + STEP)}
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
  entity: Entity | null
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (entity && !dialog.open) dialog.showModal()
    if (!entity && dialog.open) dialog.close()
  }, [entity])

  if (!entity) return <dialog ref={ref} className="ent-card" onClose={onClose} />

  const xChannel = entity.channels.find((channel) => channel.kind === 'x')
  const otherChannels = entity.channels.filter((channel) => channel.kind !== 'x')

  return (
    <dialog
      ref={ref}
      className="ent-card"
      onClose={onClose}
      onClick={(event) => {
        if (event.target === ref.current) onClose()
      }}
    >
      <div className="ent-card-inner">
        <button className="ent-card-close" onClick={onClose} aria-label="Close">
          ✕
        </button>

        <header className="ent-card-head">
          <span className={`ent-type ent-type--${entity.kind}`}>
            {typeLabel(entity.kind)}
          </span>
          <h2>{entity.name}</h2>
        </header>

        {entity.bio ? (
          <p className="ent-card-bio">{entity.bio}</p>
        ) : (
          <p className="ent-card-bio muted">No bio observed yet.</p>
        )}

        {otherChannels.length > 0 && (
          <div className="ent-card-channels">
            <div className="ent-card-label">Channels</div>
            <ul>
              {otherChannels.map((channel) => (
                <li key={channel.id}>
                  <a href={channel.url ?? undefined} target="_blank" rel="noreferrer">
                    <ChannelGlyph kind={channel.kind} />
                    <span className="ent-ch-label">{channelLabel(channel)}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {xChannel && (
          <footer className="ent-card-foot">
            <a
              className="ent-x-tag"
              href={xChannel.url ?? `https://x.com/${xChannel.key}`}
              target="_blank"
              rel="noreferrer"
            >
              <svg
                className="ent-x-mark"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d={siX.path} />
              </svg>
              @{xChannel.key}
              <span className="ent-x-go">↗</span>
            </a>
          </footer>
        )}
      </div>
    </dialog>
  )
}
