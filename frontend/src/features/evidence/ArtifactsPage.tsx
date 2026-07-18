import {
  Fragment,
  type SyntheticEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  getJSON,
  type ArtifactDates,
  type ArtifactFetchState,
  type ArtifactItem,
  type ArtifactLibrary,
} from '../../shared/api'
import DateNavigator from '../../shared/components/DateNavigator'
import CopyEventId from '../../shared/components/CopyEventId'
import {
  getDateWindowEndForSelection,
  getDateWindow,
  shiftDateWindow,
  type DateWindowDirection,
} from '../../shared/date/dateWindow'
import { useAuditDate } from '../../shared/date/auditDateStore'
import { readAuditDate, setAuditDateParam } from '../../shared/date/auditDate'

const PAGE_SIZE = 60

const observedAt = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})

const observedTimestamp = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  timeZone: 'UTC',
  timeZoneName: 'short',
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
  catalogued: 'Not extracted',
  fetching: 'Extracting',
  ready: 'Text ready',
  retryable: 'Retry needed',
  unavailable: 'Unavailable',
}

interface ContentStatus {
  label: string
  detail: string
}

function contentStatus(item: ArtifactItem): ContentStatus {
  if (item.fetch_state === 'ready') {
    return {
      label: fetchLabels.ready,
      detail: 'Usable text is available for downstream analysis.',
    }
  }
  if (item.fetch_state === 'fetching') {
    return {
      label: fetchLabels.fetching,
      detail: 'Text extraction is in progress.',
    }
  }
  if (item.fetch_state === 'retryable') {
    return {
      label: fetchLabels.retryable,
      detail: 'Text extraction failed temporarily and can be retried.',
    }
  }
  if (item.fetch_state === 'unavailable') {
    if (item.error_code === 'extraction_placeholder_content') {
      return {
        label: fetchLabels.unavailable,
        detail: 'The extracted text was unusable. The raw source was preserved for a later retry.',
      }
    }
    if (item.error_code === 'jina_thin_content') {
      return {
        label: fetchLabels.unavailable,
        detail: 'The source did not yield enough usable text.',
      }
    }
    return {
      label: fetchLabels.unavailable,
      detail: 'No usable text could be extracted from this source.',
    }
  }
  if (item.artifact_type === 'repository') {
    return {
      label: 'Not supported yet',
      detail: 'Repository text extraction is not supported yet.',
    }
  }
  if (item.artifact_type === 'video') {
    return {
      label: 'Not supported yet',
      detail: 'Video transcript extraction is not supported yet.',
    }
  }
  return {
    label: fetchLabels.catalogued,
    detail: 'The source is catalogued, but text has not been extracted yet.',
  }
}

interface ArtifactPageRequest {
  date: string
  query: string
  offset?: number
}

interface ArtifactPageOptions {
  refresh?: boolean
}

const artifactPageCache = new Map<string, ArtifactLibrary>()

function artifactPageKey({ date, query, offset = 0 }: ArtifactPageRequest) {
  return `${date}\u0000${query}\u0000${offset}`
}

function compareArtifactsByFeedRank(left: ArtifactItem, right: ArtifactItem) {
  const rankDifference = left.best_source_rank - right.best_source_rank
  if (rankDifference !== 0) return rankDifference
  const timeDifference = Date.parse(right.source_published_at)
    - Date.parse(left.source_published_at)
  if (timeDifference !== 0) return timeDifference
  return left.artifact_id.localeCompare(right.artifact_id)
}

function sortArtifactsByFeedRank(items: ArtifactItem[]) {
  return [...items].sort(compareArtifactsByFeedRank)
}

function normalizeArtifactPage(payload: ArtifactLibrary): ArtifactLibrary {
  return { ...payload, items: sortArtifactsByFeedRank(payload.items) }
}

function requestArtifactPage(
  request: ArtifactPageRequest,
  { refresh = false }: ArtifactPageOptions = {},
) {
  const key = artifactPageKey(request)
  const cached = artifactPageCache.get(key)
  if (cached && !refresh) return Promise.resolve(cached)
  const params = new URLSearchParams({
    date: request.date,
    q: request.query,
    limit: String(PAGE_SIZE),
    offset: String(request.offset ?? 0),
  })
  return getJSON<ArtifactLibrary>(`/api/artifacts?${params}`).then((payload) => {
    const normalized = normalizeArtifactPage(payload)
    artifactPageCache.set(key, normalized)
    return normalized
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

function artifactTypeLabel(type: ArtifactItem['artifact_type']) {
  if (type === 'x_article') return 'X Article'
  return type
}

function extractedContentLabel(item: ArtifactItem) {
  if (item.extractor_contract === 'jina-reader-markdown-v1') return 'Normalized Markdown'
  if (item.extractor_contract === 'pdf-pypdf-v1') return 'Extracted PDF text'
  if (item.extractor_contract === 'twitterapi-io-x-article-body-v1') {
    return 'Normalized X Article text'
  }
  if (item.extractor_contract === 'html-trafilatura-v1') return 'Extracted article text'
  return 'Normalized text'
}

interface ArtifactRowProps {
  item: ArtifactItem
  continuesRankGroup: boolean
  rankGroupSize: number
  rankIsContinuation: boolean
}

function ArtifactRow({
  item,
  continuesRankGroup,
  rankGroupSize,
  rankIsContinuation,
}: ArtifactRowProps) {
  const [extractedText, setExtractedText] = useState<string | null>(null)
  const [textState, setTextState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const sourcePublishedAt = item.source_published_at
  const feedDate = sourcePublishedAt.slice(0, 10)
  const textUrl = `/api/artifacts/${encodeURIComponent(item.artifact_id)}/text`
  const textCharCount = item.text_char_count
  const hasReadableText = item.fetch_state === 'ready' && textCharCount != null
  const status = contentStatus(item)
  const rowClassName = [
    'artifact-row',
    continuesRankGroup && 'artifact-row--rank-continues',
    rankIsContinuation && 'artifact-row--rank-continuation',
  ].filter(Boolean).join(' ')

  const loadExtractedText = (event: SyntheticEvent<HTMLDetailsElement>) => {
    if (!event.currentTarget.open || !hasReadableText || textState !== 'idle') return
    setTextState('loading')
    fetch(textUrl)
      .then((response) => {
        if (!response.ok) throw new Error(`Artifact text returned ${response.status}`)
        return response.text()
      })
      .then((text) => {
        setExtractedText(text)
        setTextState('ready')
      })
      .catch(() => setTextState('error'))
  }

  return (
    <details className={rowClassName}>
      <summary>
        <span
          className="artifact-rank mono"
          aria-hidden={rankIsContinuation || undefined}
          aria-label={rankIsContinuation
            ? undefined
            : rankGroupSize > 1
              ? `Feed rank ${item.best_source_rank}, shared by ${rankGroupSize} artifacts from one Feed Event`
              : `Feed rank ${item.best_source_rank}`}
        >
          {!rankIsContinuation && <strong>#{item.best_source_rank}</strong>}
        </span>
        <span className="artifact-identity">
          <strong>{displayTitle(item)}</strong>
          <span className="mono">{item.host.replace(/^www\./, '')}</span>
        </span>
        <span className="artifact-kind mono">{artifactTypeLabel(item.artifact_type)}</span>
        <span className="artifact-source">
          {sourceLabel(item.source_provider)}
          {item.day_observation_count > 1 && (
            <span className="mono">{item.day_observation_count} observations that day</span>
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
              {item.source_event_id ? (
                <>
                  <Link to={`/evidence/feed?date=${feedDate}&event_id=${encodeURIComponent(item.source_event_id)}`}>
                    Feed Event →
                  </Link>
                  <CopyEventId eventId={item.source_event_id} />
                </>
              ) : item.source_url ? (
                <a href={item.source_url} target="_blank" rel="noreferrer">
                  {sourceLabel(item.source_provider)} evidence ↗
                </a>
              ) : (
                sourceLabel(item.source_provider)
              )}
              <span>
                Source published {observedTimestamp.format(new Date(sourcePublishedAt))}
              </span>
              <span>
                First disclosed {observedAt.format(new Date(item.first_source_disclosed_at))}
              </span>
            </dd>
          </div>
          <div>
            <dt>Content status</dt>
            <dd>
              <span>{status.label}</span>
              <span>{status.detail}</span>
              {item.fetch_method && <span>{item.fetch_method}</span>}
              {item.text_char_count != null && (
                <span>{item.text_char_count.toLocaleString('en-US')} characters</span>
              )}
              {item.fetched_at && <span>{fetchedAt.format(new Date(item.fetched_at))}</span>}
            </dd>
          </div>
        </dl>
        {hasReadableText && (
          <details className="artifact-extracted" onToggle={loadExtractedText}>
            <summary>
              <div>
                <strong>Extracted content</strong>
                <p className="mono">
                  {extractedContentLabel(item)} · {textCharCount?.toLocaleString('en-US')} characters
                </p>
              </div>
            </summary>
            <div className="artifact-extracted-body">
              <a href={textUrl} target="_blank" rel="noreferrer">
                Open full text ↗
              </a>
              {textState === 'loading' && (
                <p className="artifact-extracted-state mono">Loading extracted content…</p>
              )}
              {textState === 'error' && (
                <p className="artifact-extracted-state mono">
                  Couldn’t load the extracted content. Open the full text to retry.
                </p>
              )}
              {textState === 'ready' && extractedText != null && (
                <pre>{extractedText}</pre>
              )}
            </div>
          </details>
        )}
      </div>
    </details>
  )
}

export default function Artifacts() {
  const [urlSearchParams, setUrlSearchParams] = useSearchParams()
  const { rememberDate } = useAuditDate()
  const initialSearchParams = useRef(new URLSearchParams(urlSearchParams))
  const initialLinkedDate = useRef(readAuditDate(initialSearchParams.current))
  const rememberDateRef = useRef(rememberDate)
  const setUrlSearchParamsRef = useRef(setUrlSearchParams)
  rememberDateRef.current = rememberDate
  setUrlSearchParamsRef.current = setUrlSearchParams
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
        if (payload.available && payload.latest_date) {
          const nextDate = initialLinkedDate.current || payload.latest_date
          const selectedIndex = payload.dates.findIndex((date) => date.day === nextDate)
          setDateWindowEnd(
            getDateWindowEndForSelection(payload.dates.length, selectedIndex),
          )
          setSelectedDate(nextDate)
          rememberDateRef.current(nextDate)
          setUrlSearchParamsRef.current(
            setAuditDateParam(initialSearchParams.current, nextDate),
            { replace: true },
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
    setError(null)
    if (cached) {
      setData(cached)
      setItems(cached.items)
      setLoading(false)
    } else {
      setLoading(true)
      setData(null)
      setItems([])
    }
    requestArtifactPage(request, { refresh: true })
      .then((payload) => {
        if (!live || activeViewKeyRef.current !== viewKey) return
        setData(payload)
        setItems(payload.items)
      })
      .catch(() => {
        if (live && activeViewKeyRef.current === viewKey && !cached) {
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

  const selectDate = (day: string) => {
    setSelectedDate(day)
    rememberDate(day)
    setUrlSearchParams(
      setAuditDateParam(urlSearchParams, day),
      { replace: true },
    )
  }

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
    if (nextDate) selectDate(nextDate.day)
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
    }, { refresh: true })
      .then((payload) => {
        if (activeViewKeyRef.current !== baseKey) return
        setItems((current) => sortArtifactsByFeedRank([...current, ...payload.items]))
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
    (data?.catalog_fetch_state_counts.retryable ?? 0)
    + (data?.catalog_fetch_state_counts.unavailable ?? 0)
  const artifactRankGroups = useMemo(() => {
    const groups: ArtifactItem[][] = []
    for (const item of items) {
      const previousGroup = groups.at(-1)
      const sharesExactEvent = Boolean(
        item.source_event_id
        && previousGroup?.[0].source_event_id === item.source_event_id,
      )
      if (sharesExactEvent && previousGroup) previousGroup.push(item)
      else groups.push([item])
    }
    return groups
  }, [items])

  return (
    <section
      className="evidence-view artifact-page"
      aria-labelledby="artifacts-title"
    >
      <header className="page-head">
        <h2 className="evidence-view-title" id="artifacts-title">
          Artifacts
        </h2>
        <p className="evidence-view-sub">
          Canonical source links disclosed by first-party Event evidence, by source date.
        </p>
        {data?.available && (
          <p className="page-method-line mono">
            <span>{data.catalog_total.toLocaleString('en-US')} canonical artifacts</span>
            <span>{data.catalog_fetch_state_counts.ready.toLocaleString('en-US')} text snapshots</span>
            {issueCount > 0 && <span>{issueCount} retrieval issues</span>}
          </p>
        )}
      </header>

      {dates?.available && (
        <section className="feed-calendar" aria-label="Available artifact source dates">
          <DateNavigator
            dates={visibleDates}
            selectedDate={selectedDate}
            onSelectDate={selectDate}
            canShowOlderDates={canShowOlderDates}
            canShowNewerDates={canShowNewerDates}
            onShowOlderDates={() => moveDateWindow('older')}
            onShowNewerDates={() => moveDateWindow('newer')}
            ariaLabel="Artifact source date"
            itemLabel="artifacts"
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
        <section className="artifact-index" aria-label="Artifacts">
          <div className="artifact-columns mono" aria-hidden="true">
            <span>Feed rank</span>
            <span>Artifact</span>
            <span>Type</span>
            <span>Found through</span>
            <span />
          </div>
          <div className="artifact-list">
            {artifactRankGroups.map((group) => (
              <Fragment key={group[0].source_event_id || group[0].artifact_id}>
                {group.map((item, index) => (
                  <ArtifactRow
                    item={item}
                    key={item.artifact_id}
                    continuesRankGroup={index < group.length - 1}
                    rankGroupSize={group.length}
                    rankIsContinuation={index > 0}
                  />
                ))}
              </Fragment>
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
    </section>
  )
}
