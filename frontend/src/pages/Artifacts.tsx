import { useEffect, useState } from 'react'
import {
  getJSON,
  type ArtifactFetchState,
  type ArtifactItem,
  type ArtifactLibrary,
} from '../api'

const PAGE_SIZE = 60

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
          {observedAt.format(new Date(latestObservationAt))}
        </time>
        <span className="artifact-identity">
          <strong>{displayTitle(item)}</strong>
          <span className="mono">{item.host.replace(/^www\./, '')}</span>
        </span>
        <span className="artifact-kind mono">{item.artifact_kind}</span>
        <span className="artifact-source">
          {sourceLabel(item.source_provider)}
          {item.observation_count > 1 && (
            <span className="mono">{item.observation_count} observations</span>
          )}
        </span>
        <span className={`artifact-state artifact-state--${item.fetch_state}`}>
          {fetchLabels[item.fetch_state]}
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
                First seen {observedAt.format(new Date(item.first_seen_at))}
              </span>
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
              {item.fetched_at && (
                <span>{fetchedAt.format(new Date(item.fetched_at))}</span>
              )}
              {item.error_code && <span>{item.error_code.replaceAll('_', ' ')}</span>}
            </dd>
          </div>
        </dl>
      </div>
    </details>
  )
}

export default function Artifacts() {
  const [data, setData] = useState<ArtifactLibrary | null>(null)
  const [items, setItems] = useState<ArtifactItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getJSON<ArtifactLibrary>(`/api/artifacts?limit=${PAGE_SIZE}`)
      .then((payload) => {
        setData(payload)
        setItems(payload.items)
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : 'Artifacts are unavailable.'),
      )
      .finally(() => setLoading(false))
  }, [])

  const loadMore = () => {
    if (!data) return
    setLoading(true)
    getJSON<ArtifactLibrary>(
      `/api/artifacts?limit=${PAGE_SIZE}&offset=${items.length}`,
    )
      .then((payload) => setItems((current) => [...current, ...payload.items]))
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : 'More artifacts are unavailable.'),
      )
      .finally(() => setLoading(false))
  }

  const issueCount =
    (data?.counts?.retryable ?? 0) + (data?.counts?.unavailable ?? 0)

  return (
    <div className="page artifact-page">
      <header className="page-head">
        <h1 className="page-title">Primary artifacts</h1>
        <p className="page-sub">
          Durable source links selected from kept Feed evidence, newest first.
        </p>
        {data?.available && (
          <p className="page-method-line mono">
            <span>{data.total.toLocaleString('en-US')} canonical artifacts</span>
            <span>{(data.counts?.ready ?? 0).toLocaleString('en-US')} text snapshots</span>
            {issueCount > 0 && <span>{issueCount} retrieval issues</span>}
          </p>
        )}
      </header>

      {error && <p className="artifact-message mono">{error}</p>}
      {data && !data.available && (
        <p className="artifact-message mono">{data.reason}</p>
      )}

      {data?.available && (
        <section className="artifact-index" aria-label="Primary artifacts">
          <div className="artifact-columns mono" aria-hidden="true">
            <span>Observed</span>
            <span>Artifact</span>
            <span>Type</span>
            <span>Found through</span>
            <span>Retrieval</span>
            <span />
          </div>
          <div className="artifact-list">
            {items.map((item) => (
              <ArtifactRow item={item} key={item.artifact_id} />
            ))}
          </div>
          {items.length < data.total && (
            <button
              className="load-more"
              type="button"
              onClick={loadMore}
              disabled={loading}
            >
              {loading ? 'Loading…' : `Load ${Math.min(PAGE_SIZE, data.total - items.length)} more`}
            </button>
          )}
        </section>
      )}

      {!data && !error && (
        <div className="artifact-loading skeleton" aria-label="Loading artifacts" />
      )}
    </div>
  )
}
