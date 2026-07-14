import { useEffect, useMemo, useRef, useState } from 'react'
import {
  getJSON,
  type ArtifactDates,
  type ArtifactFetchState,
  type ArtifactItem,
  type ArtifactLibrary,
} from '../api'
import DateNavigator from '../components/DateNavigator'
import {
  getDateWindow,
  shiftDateWindow,
  type DateWindowDirection,
} from '../dateWindow'

const PAGE_SIZE = 60

const sourceTime = new Intl.DateTimeFormat('en-US', {
  hour: 'numeric',
  minute: '2-digit',
  timeZone: 'UTC',
  timeZoneName: 'short',
})

const observedAt = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})

const fetchedAt = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  timeZone: 'UTC',
  timeZoneName: 'short',
})

const fetchLabels: Record<ArtifactFetchState, string> = {
  catalogued: 'Catalogued',
  fetching: 'Fetching',
  ready: 'Ready',
  retryable: 'Retryable',
  unavailable: 'Unavailable',
}

interface ArtifactPageRequest {
  date: string
  query: string
  offset?: number
}

const artifactPageCache = new Map<string, ArtifactLibrary>()

function artifactPageKey({ date, query, offset = 0 }: ArtifactPageRequest) {
  return `${date}\u0000${query}\u0000${offset}`
}

function requestArtifactPage(request: ArtifactPageRequest) {
  const key = artifactPageKey(request)
  const cached = artifactPageCache.get(key)
  if (cached) return Promise.resolve(cached)
  const params = new URLSearchParams({
    date: request.date,
    q: request.query,
    limit: String(PAGE_SIZE),
    offset: String(request.offset ?? 0),
  })
  return getJSON<ArtifactLibrary>(`/api/artifacts?${params}`).then((payload) => {
    artifactPageCache.set(key, payload)
    return payload
  })
}

function displayTitle(item: ArtifactItem) {
  if (item.title?.trim()) return item.title.trim()
  try {
    const url = new URL(item.canonical_url)
    const path = decodeURIComponent(url.pathname).replace(/\/$/, '')
    return `${url.hostname.replace(/^www\./, '')}${path}`
  } catch {
    return item.canonical_url
  }
}

function sourceLabel(provider: string | null) {
  if (provider === 'twitterapi_io') return 'X'
  return provider || 'Feed'
}

function ArtifactRow({ item }: { item: ArtifactItem }) {
  const latestObservationAt = item.last_source_published_at || item.last_seen_at

  return (
    <details className="artifact-row">
      <summary>
        <time className="artifact-date mono" dateTime={latestObservationAt}>
          {sourceTime.format(new Date(latestObservationAt))}
        </time>
        <span className="artifact-identity">
          <strong>{displayTitle(item)}</strong>
          <span className="mono">{item.host.replace(/^www\./, '')}</span>
        </span>
        <span className="artifact-kind mono">{item.artifact_kind}</span>
        <span className="artifact-source">
          {sourceLabel(item.source_provider)}
          {item.observation_count > 1 && (
            <span className="mono">{item.observation_count} observations that day</span>
          )}
        </span>
        <span className="artifact-caret" aria-hidden="true" />
      </summary>
      <div className="artifact-provenance">
        <dl>
          <div>
            <dt>Canonical artifact</dt>
            <dd>
              <a href={item.canonical_url} target="_blank" rel="noreferrer">
                {item.canonical_url} ↗
              </a>
            </dd>
          </div>
          <div>
            <dt>Observed in</dt>
            <dd>
              {item.source_url ? (
                <a href={item.source_url} target="_blank" rel="noreferrer">
                  {sourceLabel(item.source_provider)} evidence ↗
                </a>
              ) : (
                sourceLabel(item.source_provider)
              )}
              <span>
                Source published {observedAt.format(new Date(latestObservationAt))}
              </span>
              <span>Catalogued {observedAt.format(new Date(item.first_seen_at))}</span>
            </dd>
          </div>
          <div>
            <dt>Retrieval</dt>
            <dd>
              <span>{fetchLabels[item.fetch_state]}</span>
              {item.fetch_method && <span>{item.fetch_method}</span>}
              {item.text_char_count != null && (
                <span>{item.text_char_count.toLocaleString('en-US')} characters</span>
              )}
              {item.fetched_at && <span>{fetchedAt.format(new Date(item.fetched_at))}</span>}
              {item.error_code && <span>{item.error_code.replaceAll('_', ' ')}</span>}
            </dd>
          </div>
        </dl>
      </div>
    </details>
  )
}

export default function Artifacts() {
  const [dates, setDates] = useState<ArtifactDates | null>(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [dateWindowEnd, setDateWindowEnd] = useState(0)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [data, setData] = useState<ArtifactLibrary | null>(null)
  const [items, setItems] = useState<ArtifactItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const activeViewKeyRef = useRef('')
  const availableDates = useMemo(() => dates?.dates ?? [], [dates])
  const dateWindow = useMemo(
    () => getDateWindow(dateWindowEnd, availableDates.length),
    [dateWindowEnd, availableDates.length],
  )
  const visibleDates = useMemo(
    () => availableDates.slice(dateWindow.start, dateWindow.end),
    [availableDates, dateWindow],
  )
  const canShowOlderDates = dateWindow.start > 0
  const canShowNewerDates = dateWindow.end < availableDates.length

  useEffect(() => {
    setLoading(true)
    getJSON<ArtifactDates>('/api/artifacts/dates')
      .then((payload) => {
        setDates(payload)
        setDateWindowEnd(payload.dates?.length ?? 0)
        if (payload.available && payload.latest_date) {
          setSelectedDate((current) =>
            payload.dates?.some((date) => date.day === current)
              ? current
              : payload.latest_date ?? '',
          )
        }
      })
      .catch(() => setError('Couldn’t load available artifact dates. Reload to try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query), 180)
    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (!selectedDate) return
    let live = true
    const request = { date: selectedDate, query: debouncedQuery, offset: 0 }
    const viewKey = artifactPageKey(request)
    activeViewKeyRef.current = viewKey
    const cached = artifactPageCache.get(viewKey)
    if (cached) {
      setData(cached)
      setItems(cached.items)
      setLoading(false)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    setData(null)
    setItems([])
    requestArtifactPage(request)
      .then((payload) => {
        if (!live || activeViewKeyRef.current !== viewKey) return
        setData(payload)
        setItems(payload.items)
      })
      .catch(() => {
        if (live && activeViewKeyRef.current === viewKey) {
          setError('Couldn’t load artifacts for this date. Change the date or reload.')
        }
      })
      .finally(() => {
        if (live && activeViewKeyRef.current === viewKey) setLoading(false)
      })
    return () => {
      live = false
    }
  }, [selectedDate, debouncedQuery])

  useEffect(() => {
    if (!selectedDate || debouncedQuery) return
    let cancelled = false
    const timer = window.setTimeout(async () => {
      for (const value of visibleDates) {
        if (cancelled || value.day === selectedDate) continue
        try {
          await requestArtifactPage({ date: value.day, query: '', offset: 0 })
        } catch {
          // Prefetch is opportunistic; foreground requests surface errors.
        }
      }
    }, 350)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [visibleDates, selectedDate, debouncedQuery])

  const moveDateWindow = (direction: DateWindowDirection) => {
    const selectedIndex = availableDates.findIndex(
      (value) => value.day === selectedDate,
    )
    const nextWindow = shiftDateWindow(
      dateWindow.end,
      availableDates.length,
      selectedIndex,
      direction,
    )
    if (nextWindow.end === dateWindow.end) return
    setDateWindowEnd(nextWindow.end)
    const nextDate = availableDates[nextWindow.selectedIndex]
    if (nextDate) setSelectedDate(nextDate.day)
  }

  const loadMore = () => {
    if (!data || items.length >= data.matching_total) return
    const baseKey = artifactPageKey({
      date: selectedDate,
      query: debouncedQuery,
      offset: 0,
    })
    if (activeViewKeyRef.current !== baseKey) return
    setLoading(true)
    setError(null)
    requestArtifactPage({
      date: selectedDate,
      query: debouncedQuery,
      offset: items.length,
    })
      .then((payload) => {
        if (activeViewKeyRef.current !== baseKey) return
        setItems((current) => [...current, ...payload.items])
      })
      .catch(() => {
        if (activeViewKeyRef.current === baseKey) {
          setError('Couldn’t load more artifacts. Try again.')
        }
      })
      .finally(() => {
        if (activeViewKeyRef.current === baseKey) setLoading(false)
      })
  }

  const issueCount =
    (data?.counts?.retryable ?? 0) + (data?.counts?.unavailable ?? 0)

  return (
    <div className="page artifact-page">
      <header className="page-head">
        <h1 className="page-title">Primary artifacts</h1>
        <p className="page-sub">
          Durable source links selected from kept Feed evidence, by source date.
        </p>
        {data?.available && (
          <p className="page-method-line mono">
            <span>{data.total.toLocaleString('en-US')} canonical artifacts</span>
            <span>{(data.counts?.ready ?? 0).toLocaleString('en-US')} text snapshots</span>
            {issueCount > 0 && <span>{issueCount} retrieval issues</span>}
          </p>
        )}
      </header>

      {dates?.available && (
        <section className="feed-calendar" aria-label="Available artifact source dates">
          <DateNavigator
            dates={visibleDates}
            selectedDate={selectedDate}
            onSelectDate={setSelectedDate}
            canShowOlderDates={canShowOlderDates}
            canShowNewerDates={canShowNewerDates}
            onShowOlderDates={() => moveDateWindow('older')}
            onShowNewerDates={() => moveDateWindow('newer')}
            ariaLabel="Artifact source date"
          />
        </section>
      )}

      {dates?.available && (
        <div className="artifact-tools">
          <input
            className="search artifact-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search title, host, or URL…"
            aria-label="Search artifacts"
          />
        </div>
      )}

      {error && <p className="artifact-message mono">{error}</p>}
      {dates && !dates.available && (
        <p className="artifact-message mono">{dates.reason}</p>
      )}
      {data && !data.available && (
        <p className="artifact-message mono">{data.reason}</p>
      )}

      {data?.available && (
        <section className="artifact-index" aria-label="Primary artifacts">
          <div className="artifact-columns mono" aria-hidden="true">
            <span>Source time</span>
            <span>Artifact</span>
            <span>Type</span>
            <span>Found through</span>
            <span />
          </div>
          <div className="artifact-list">
            {items.map((item) => (
              <ArtifactRow item={item} key={item.artifact_id} />
            ))}
          </div>
          {items.length === 0 && (
            <p className="artifact-empty mono">
              {debouncedQuery
                ? 'No artifacts match this search on the selected source date.'
                : 'No artifacts were observed on this source date.'}
            </p>
          )}
          {items.length < data.matching_total && (
            <button
              className="load-more"
              type="button"
              onClick={loadMore}
              disabled={loading}
            >
              {loading
                ? 'Loading…'
                : `Load ${Math.min(PAGE_SIZE, data.matching_total - items.length)} more`}
            </button>
          )}
        </section>
      )}

      {!data && !error && dates?.available && (
        <div className="artifact-loading skeleton" aria-label="Loading artifacts" />
      )}
      {!dates && !error && loading && (
        <div className="artifact-loading skeleton" aria-label="Loading artifact dates" />
      )}
    </div>
  )
}
