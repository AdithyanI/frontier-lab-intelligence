import { useEffect, useRef, useState } from 'react'
import { siGithub, siRss, siX } from 'simple-icons'
import {
  getJSON,
  type Entity,
  type EntityChannel,
  type EntityKind,
  type RegistryGroup,
  type Registry as RegistryData,
} from '../api'

type KindFilter = 'all' | RegistryGroup

const BRAND_ICON: Record<string, string> = {
  github: siGithub.path,
  x: siX.path,
  blog: siRss.path,
}

const FIRST = 40
const STEP = 40
const SEARCH_DELAY_MS = 180

const fmt = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US')

const TYPE_LABEL: Record<EntityKind, string> = {
  person: 'Person',
  organization: 'Organization',
  unsure: 'Unsure',
  unknown: 'Unknown',
}

const CHANNEL_KIND_ORDER = ['x', 'website', 'github', 'blog']

const channelKindLabel = (kind: string) => {
  const labels: Record<string, string> = {
    x: 'X',
    website: 'Website',
    github: 'GitHub',
    blog: 'Blog',
  }
  return labels[kind] ?? kind
}

const registryURL = (kind: KindFilter, query: string, offset: number) => {
  const params = new URLSearchParams({
    group: kind,
    limit: String(offset === 0 ? FIRST : STEP),
    offset: String(offset),
  })
  const needle = query.trim()
  if (needle) params.set('q', needle)
  return `/api/registry?${params}`
}

const typeLabel = (entity: Entity) =>
  entity.registry_state === 'rejected' ? 'Rejected' : TYPE_LABEL[entity.kind]

const typeClass = (entity: Entity) =>
  entity.registry_state === 'rejected' ? 'rejected' : entity.kind

const xHandleLabel = (channel: EntityChannel) => {
  const label = channel.label?.trim()
  return `@${label && label.toLowerCase() === channel.key ? label : channel.key}`
}

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
    case 'x':
      return xHandleLabel(channel)
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
    case 'blog':
      try {
        return channel.url
          ? new URL(channel.url).hostname.replace(/^www\./, '')
          : 'Feed'
      } catch {
        return 'Feed'
      }
    default:
      return channel.label || channel.key
  }
}

export default function Registry() {
  const [data, setData] = useState<RegistryData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [kind, setKind] = useState<KindFilter>('all')
  const [selected, setSelected] = useState<Entity | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const viewRef = useRef('all\0')

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedQuery(query),
      SEARCH_DELAY_MS,
    )
    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    const controller = new AbortController()
    const view = `${kind}\0${debouncedQuery}`
    viewRef.current = view
    setLoading(true)
    setLoadingMore(false)
    setError(null)
    setSelected(null)
    getJSON<RegistryData>(registryURL(kind, debouncedQuery, 0), {
      signal: controller.signal,
    })
      .then((page) => {
        if (viewRef.current === view) setData(page)
      })
      .catch((cause: unknown) => {
        if ((cause as Error).name !== 'AbortError') setError(String(cause))
      })
      .finally(() => {
        if (!controller.signal.aborted && viewRef.current === view) {
          setLoading(false)
        }
      })
    return () => controller.abort()
  }, [debouncedQuery, kind])

  const visible = data?.entities ?? []
  const loadMore = () => {
    if (!data || loadingMore) return
    const view = viewRef.current
    setLoadingMore(true)
    setError(null)
    getJSON<RegistryData>(
      registryURL(kind, debouncedQuery, data.entities.length),
    )
      .then((page) => {
        if (viewRef.current !== view) return
        setData((current) =>
          current
            ? { ...page, entities: [...current.entities, ...page.entities] }
            : page,
        )
      })
      .catch((cause: unknown) => {
        if (viewRef.current === view) setError(String(cause))
      })
      .finally(() => setLoadingMore(false))
  }
  const filters: { key: KindFilter; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: data?.total ?? 0 },
    { key: 'person', label: 'People', count: data?.counts.person ?? 0 },
    {
      key: 'organization',
      label: 'Organizations',
      count: data?.counts.organization ?? 0,
    },
    { key: 'unsure', label: 'Unsure', count: data?.counts.unsure ?? 0 },
    {
      key: 'rejected',
      label: 'Rejected',
      count: data?.counts.rejected ?? 0,
    },
  ]
  if ((data?.counts.unknown ?? 0) > 0) {
    filters.push({
      key: 'unknown',
      label: 'Unknown',
      count: data?.counts.unknown ?? 0,
    })
  }
  const showRejectionReason = kind === 'rejected'
  const showFollowerColumn = ['all', 'person', 'organization'].includes(kind)
  const showTypeColumn = kind !== 'person' && kind !== 'organization'

  return (
    <div className="page">
      <div className="page-kicker">ENTITY UNIVERSE · WHO WE HAVE OBSERVED</div>
      <h1 className="page-title">Registry</h1>
      <p className="page-sub">
        {data
          ? `${fmt(data.total)} identities: ${fmt(data.counts.person)} people, ${fmt(data.counts.organization)} organizations, ${fmt(data.counts.unsure)} unsure, and ${fmt(data.counts.rejected)} rejected.`
          : 'Every observed channel resolves to one structurally typed entity.'}
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
        <div className="seg" role="tablist" aria-label="Filter Registry">
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
            {fmt(visible.length)} of {fmt(data.filtered_total)}
          </span>
        )}
      </div>

      {!data && loading && !error && (
        <div className="registry-loading skeleton" />
      )}

      {data && visible.length > 0 && (
        <table className="ent-table" aria-busy={loading || loadingMore}>
          <thead>
            <tr>
              <th>Entity</th>
              {showTypeColumn && <th className="ent-type-head">Type</th>}
              {showFollowerColumn && (
                <th className="ent-followers-head">
                  {kind === 'person' ? 'X followers' : 'Combined X followers'}
                </th>
              )}
              {showRejectionReason && <th>Why rejected</th>}
            </tr>
          </thead>
          <tbody>
            {visible.map((entity) => {
              const xChannels = entity.channels.filter(
                (channel) => channel.kind === 'x',
              )
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
                    {xChannels.length > 0 && !showFollowerColumn && (
                      <span className="ent-handles">
                        {xChannels.map((channel) => (
                          <span className="ent-handle" key={channel.id}>
                            {xHandleLabel(channel)}
                          </span>
                        ))}
                      </span>
                    )}
                  </td>
                  {showTypeColumn && (
                    <td className="ent-type-cell">
                      <span className={`ent-type ent-type--${typeClass(entity)}`}>
                        {typeLabel(entity)}
                      </span>
                    </td>
                  )}
                  {showFollowerColumn && (
                    <td className="ent-followers">
                      {fmt(entity.followers_count)}
                    </td>
                  )}
                  {showRejectionReason && (
                    <td className="ent-rejection-reason">
                      {entity.rejection_reason ?? 'No rejection reason recorded.'}
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      {data && visible.length === 0 && (
        <div className="registry-empty">No entities match this view.</div>
      )}

      {data && data.entities.length < data.filtered_total && (
        <button
          className="load-more"
          onClick={loadMore}
          disabled={loadingMore}
        >
          {loadingMore
            ? 'Loading…'
            : `Show ${fmt(Math.min(STEP, data.filtered_total - data.entities.length))} more`}
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

  const orderedChannels = [...entity.channels].sort((left, right) => {
    const priority = (channel: EntityChannel) => {
      const index = CHANNEL_KIND_ORDER.indexOf(channel.kind)
      return index === -1 ? CHANNEL_KIND_ORDER.length : index
    }
    return priority(left) - priority(right) || left.key.localeCompare(right.key)
  })
  const channelGroups = orderedChannels.reduce<
    { kind: string; channels: EntityChannel[] }[]
  >((groups, channel) => {
    const current = groups.at(-1)
    if (current?.kind === channel.kind) {
      current.channels.push(channel)
    } else {
      groups.push({ kind: channel.kind, channels: [channel] })
    }
    return groups
  }, [])
  const titleId = `entity-card-title-${entity.id}`
  const bioId = `entity-card-bio-${entity.id}`
  const bioIsSourcePreview = /(?:\.{3}|…)$/.test(entity.bio?.trim() ?? '')

  return (
    <dialog
      ref={ref}
      className="ent-card"
      aria-labelledby={titleId}
      aria-describedby={entity.bio ? bioId : undefined}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === ref.current) onClose()
      }}
    >
      <button
        className="ent-card-close"
        type="button"
        onClick={onClose}
        aria-label="Close profile"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M6.5 6.5 17.5 17.5M17.5 6.5 6.5 17.5" />
        </svg>
      </button>

      <div className="ent-card-inner">
        <header className="ent-card-head">
          <span className={`ent-type ent-type--${typeClass(entity)}`}>
            {typeLabel(entity)}
          </span>
          <h2 id={titleId}>{entity.name}</h2>
        </header>

        <section className="ent-card-profile" aria-labelledby={`${bioId}-label`}>
          <div className="ent-card-label-row">
            <div className="ent-card-label" id={`${bioId}-label`}>
              Profile bio
            </div>
            {bioIsSourcePreview && (
              <span className="ent-card-source-state">Source preview</span>
            )}
          </div>
          {entity.bio ? (
            <p className="ent-card-bio" id={bioId}>
              {entity.bio}
            </p>
          ) : (
            <p className="ent-card-bio muted">No bio observed yet.</p>
          )}
          {bioIsSourcePreview && (
            <p className="ent-card-source-note">
              This snapshot ends where the source preview ends. Open the profile
              for the complete text.
            </p>
          )}
        </section>

        {entity.registry_state === 'rejected' && entity.rejection_reason && (
          <div className="ent-card-reason ent-card-reason--rejected">
            <div className="ent-card-label">Why rejected</div>
            <p>{entity.rejection_reason}</p>
          </div>
        )}

        {entity.registry_state !== 'rejected' && entity.kind_reason && (
          <div className="ent-card-reason">
            <div className="ent-card-label">Why this type</div>
            <p>{entity.kind_reason}</p>
          </div>
        )}

        {orderedChannels.length > 0 && (
          <div className="ent-card-channels">
            <div className="ent-card-label">Channels</div>
            <dl className="ent-channel-list">
              {channelGroups.map((group) => (
                <div className="ent-channel-row" key={group.kind}>
                  <dt>
                    <ChannelGlyph kind={group.kind} />
                    <span>{channelKindLabel(group.kind)}</span>
                  </dt>
                  <dd>
                    {group.channels.map((channel) =>
                      channel.url ? (
                        <a
                          className="ent-card-channel"
                          href={channel.url}
                          target="_blank"
                          rel="noreferrer"
                          key={channel.id}
                        >
                          <span>{channelLabel(channel)}</span>
                          <span className="ent-channel-go" aria-hidden="true">
                            ↗
                          </span>
                        </a>
                      ) : (
                        <span
                          className="ent-card-channel is-unavailable"
                          key={channel.id}
                        >
                          {channelLabel(channel)}
                        </span>
                      ),
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </dialog>
  )
}
