import { useEffect, useRef, useState } from 'react'
import {
  getJSON,
  type Entity,
  type RegistryGroup,
  type Registry as RegistryData,
} from '../api'
import EntityCard, { typeClass, typeLabel, xHandleLabel } from '../components/EntityCard'

type KindFilter = 'all' | RegistryGroup
type SortField = 'followers' | 'network'
type SortDirection = 'asc' | 'desc'

const FIRST = 40
const STEP = 40
const SEARCH_DELAY_MS = 180

const fmt = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US')

const registryURL = (
  kind: KindFilter,
  query: string,
  offset: number,
  sort: SortField,
  direction: SortDirection,
) => {
  const params = new URLSearchParams({
    group: kind,
    limit: String(offset === 0 ? FIRST : STEP),
    offset: String(offset),
    sort,
    direction,
  })
  const needle = query.trim()
  if (needle) params.set('q', needle)
  return `/api/registry?${params}`
}

export default function Registry() {
  const initialQuery = new URLSearchParams(window.location.search).get('q') ?? ''
  const [data, setData] = useState<RegistryData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState(initialQuery)
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery)
  const [kind, setKind] = useState<KindFilter>('all')
  const [sortField, setSortField] = useState<SortField>('followers')
  const [sortDirection, setSortDirection] =
    useState<SortDirection>('desc')
  const [selected, setSelected] = useState<Entity | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const viewRef = useRef('all\0followers\0desc')

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedQuery(query),
      SEARCH_DELAY_MS,
    )
    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    const controller = new AbortController()
    const view = `${kind}\0${debouncedQuery}\0${sortField}\0${sortDirection}`
    viewRef.current = view
    setLoading(true)
    setLoadingMore(false)
    setError(null)
    setSelected(null)
    getJSON<RegistryData>(
      registryURL(kind, debouncedQuery, 0, sortField, sortDirection),
      { signal: controller.signal },
    )
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
  }, [debouncedQuery, kind, sortDirection, sortField])

  const visible = data?.entities ?? []
  const loadMore = () => {
    if (!data || loadingMore) return
    const view = viewRef.current
    setLoadingMore(true)
    setError(null)
    getJSON<RegistryData>(
      registryURL(
        kind,
        debouncedQuery,
        data.entities.length,
        sortField,
        sortDirection,
      ),
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
  const showNetworkRankColumn = showFollowerColumn
  const showTypeColumn = kind !== 'person' && kind !== 'organization'
  const changeSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((current) => (current === 'desc' ? 'asc' : 'desc'))
      return
    }
    setSortField(field)
    setSortDirection(field === 'network' ? 'asc' : 'desc')
  }

  return (
    <section className="network-view registry-view" aria-labelledby="registry-title">
      <h2 className="network-view-title" id="registry-title">Registry</h2>
      <p className="network-view-sub">
        Resolved people and organizations, with every observed channel attached
        to a single identity.
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
              {showNetworkRankColumn && (
                <th
                  className="ent-network-head"
                  aria-sort={
                    sortField === 'network'
                      ? sortDirection === 'asc'
                        ? 'ascending'
                        : 'descending'
                      : 'none'
                  }
                >
                  <button
                    className="ent-sort"
                    type="button"
                    aria-label={`Sort by network rank, ${
                      sortField === 'network' && sortDirection === 'asc'
                        ? 'lowest rank first'
                        : 'highest rank first'
                    }`}
                    onClick={() => changeSort('network')}
                  >
                    <span>Network rank</span>
                    <span className="ent-sort-arrow" aria-hidden="true">
                      {sortField === 'network'
                        ? sortDirection === 'asc'
                          ? '↑'
                          : '↓'
                        : '↕'}
                    </span>
                  </button>
                </th>
              )}
              {showFollowerColumn && (
                <th
                  className="ent-followers-head"
                  aria-sort={
                    sortField === 'followers'
                      ? sortDirection === 'desc'
                        ? 'descending'
                        : 'ascending'
                      : 'none'
                  }
                >
                  <button
                    className="ent-sort"
                    type="button"
                    aria-label={`Sort by ${
                      kind === 'person' ? 'X followers' : 'combined X followers'
                    }, ${sortDirection === 'desc' ? 'ascending' : 'descending'}`}
                    onClick={() => changeSort('followers')}
                  >
                    <span>
                      {kind === 'person'
                        ? 'X followers'
                        : 'Combined X followers'}
                    </span>
                    <span className="ent-sort-arrow" aria-hidden="true">
                      {sortField === 'followers'
                        ? sortDirection === 'desc'
                          ? '↓'
                          : '↑'
                        : '↕'}
                    </span>
                  </button>
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
                  {showNetworkRankColumn && (
                    <td
                      className="ent-network-rank"
                      title={
                        entity.network_rank == null
                          ? 'No owned X account appears in the current network ranking.'
                          : `Best-ranked owned account${
                              entity.network_account_handle
                                ? `: @${entity.network_account_handle}`
                                : ''
                            }; ${fmt(entity.network_follow_count)} screened Registry sources follow it.`
                      }
                    >
                      {entity.network_rank == null
                        ? '—'
                        : `#${fmt(entity.network_rank)}`}
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
    </section>
  )
}
