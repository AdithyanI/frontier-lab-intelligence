import { useEffect, useMemo, useState } from 'react'
import {
  getJSON,
  type FeedDates,
  type FeedItem,
  type FeedResponse,
} from '../api'

type Lane = 'all' | 'network' | 'firsthand'
type Sort = 'attention' | 'recent' | 'engagement'

const PAGE_SIZE = 40

const compact = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
})

const fullDate = new Intl.DateTimeFormat('en-US', {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})

const shortDate = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC',
})

const time = new Intl.DateTimeFormat('en-US', {
  hour: 'numeric',
  minute: '2-digit',
  timeZone: 'UTC',
  timeZoneName: 'short',
})

const fmt = (value: number | null | undefined) =>
  value == null ? '—' : compact.format(value)

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <span>
      <b>{fmt(value)}</b> {label}
    </span>
  )
}

function FeedRow({ item, rank }: { item: FeedItem; rank: number }) {
  const c = item.score_components
  const isLong = item.text.length > 680
  const rationale = [
    item.observed_directly ? 'first-hand' : null,
    c.registry_amplifiers
      ? `${c.registry_amplifiers} Registry amplifier${c.registry_amplifiers === 1 ? '' : 's'}`
      : null,
    c.high_support_amplifiers
      ? `${c.high_support_amplifiers} high-support`
      : null,
    c.originator_network_rank
      ? `originator network rank #${c.originator_network_rank.toLocaleString('en-US')}`
      : null,
  ].filter(Boolean)

  return (
    <article className="feed-row">
      <div className="feed-rank mono" aria-label={`Rank ${rank}`}>
        <span className="feed-rank-no">{rank}</span>
        <strong>{item.attention_score.toFixed(1)}</strong>
        <span>attention</span>
      </div>

      <div className="feed-body">
        <header className="feed-byline">
          <div>
            <strong>{item.author.entity_name ?? item.author.name}</strong>
            <a href={`https://x.com/${item.author.handle}`} target="_blank" rel="noreferrer">
              @{item.author.handle}
            </a>
          </div>
          <div className="feed-meta mono">
            {item.observed_directly && (
              <span className="feed-lane feed-lane--firsthand">first-hand</span>
            )}
            {item.amplifiers.length > 0 && (
              <span className="feed-lane feed-lane--network">network attention</span>
            )}
            {item.post_type === 'quote' && <span>quote</span>}
            <time dateTime={item.published_at}>{time.format(new Date(item.published_at))}</time>
          </div>
        </header>

        {isLong ? (
          <details className="feed-long-post">
            <summary>
              <span className="feed-text">{item.text.slice(0, 680)}…</span>
              <span className="feed-expand-label mono">Read full post</span>
            </summary>
            <p className="feed-text">{item.text}</p>
          </details>
        ) : (
          <p className="feed-text">{item.text || <span className="muted">Post has no text.</span>}</p>
        )}

        {item.context && (
          <div className="feed-context mono">
            Quotes @{item.context.target_handle} · post {item.context.target_post_id}
          </div>
        )}

        <div className="feed-proof">
          <div className="feed-why">
            <span className="feed-proof-label">WHY HERE</span>
            <span>{rationale.join(' · ')}</span>
          </div>
          {item.amplifiers.length > 0 && (
            <div className="feed-amplifiers" aria-label="Registry amplifiers">
              {item.amplifiers.slice(0, 6).map((amplifier) => (
                <a
                  key={amplifier.entity_id}
                  href={amplifier.source_url}
                  target="_blank"
                  rel="noreferrer"
                  title={`${amplifier.relation_type} · ${amplifier.network_support} network support`}
                >
                  {amplifier.entity_name}
                </a>
              ))}
              {item.amplifiers.length > 6 && (
                <span>+{item.amplifiers.length - 6} more</span>
              )}
            </div>
          )}
        </div>

        <footer className="feed-footer mono">
          <div className="feed-metrics">
            <Metric label="likes" value={item.metrics.likes} />
            <Metric label="reposts" value={item.metrics.reposts} />
            <Metric label="replies" value={item.metrics.replies} />
            <Metric label="views" value={item.metrics.views} />
          </div>
          <a href={item.url} target="_blank" rel="noreferrer">
            Open evidence on X ↗
          </a>
        </footer>
      </div>
    </article>
  )
}

export default function Feed() {
  const [dates, setDates] = useState<FeedDates | null>(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [lane, setLane] = useState<Lane>('all')
  const [sort, setSort] = useState<Sort>('attention')
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [data, setData] = useState<FeedResponse | null>(null)
  const [items, setItems] = useState<FeedItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getJSON<FeedDates>('/api/feed/dates')
      .then((value) => {
        setDates(value)
        if (value.available && value.latest_complete_date) {
          setSelectedDate(value.latest_complete_date)
        }
      })
      .catch((reason) => setError(String(reason)))
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query), 180)
    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (!selectedDate) return
    let live = true
    setLoading(true)
    setError('')
    const params = new URLSearchParams({
      date: selectedDate,
      lane,
      sort,
      q: debouncedQuery,
      limit: String(PAGE_SIZE),
      offset: '0',
    })
    getJSON<FeedResponse>(`/api/feed?${params}`)
      .then((value) => {
        if (!live) return
        setData(value)
        setItems(value.items ?? [])
      })
      .catch((reason) => live && setError(String(reason)))
      .finally(() => live && setLoading(false))
    return () => {
      live = false
    }
  }, [selectedDate, lane, sort, debouncedQuery])

  const availableDates = useMemo(() => dates?.dates ?? [], [dates])
  const selectedIndex = availableDates.findIndex((value) => value.day === selectedDate)

  const loadMore = () => {
    if (!data?.total || items.length >= data.total) return
    const params = new URLSearchParams({
      date: selectedDate,
      lane,
      sort,
      q: debouncedQuery,
      limit: String(PAGE_SIZE),
      offset: String(items.length),
    })
    setLoading(true)
    getJSON<FeedResponse>(`/api/feed?${params}`)
      .then((value) => setItems((current) => [...current, ...(value.items ?? [])]))
      .catch((reason) => setError(String(reason)))
      .finally(() => setLoading(false))
  }

  if (error && !data) {
    return (
      <div className="page feed-page">
        <div className="page-kicker">FEED · STORED X EVIDENCE</div>
        <h1 className="page-title">What is the network paying attention to?</h1>
        <p className="error-note">{error}</p>
      </div>
    )
  }

  if (dates && !dates.available) {
    return (
      <div className="page feed-page">
        <div className="page-kicker">FEED · STORED X EVIDENCE</div>
        <h1 className="page-title">What is the network paying attention to?</h1>
        <p className="page-sub mono">{dates.reason}</p>
      </div>
    )
  }

  return (
    <div className="page feed-page">
      <div className="page-kicker">FEED · STORED X EVIDENCE · ATTENTION-V1</div>
      <h1 className="page-title">What is the network paying attention to?</h1>
      <p className="page-sub">
        A deduplicated audit trail of first-hand posts and links amplified by the
        active Registry. The score orders evidence; it does not judge quality or
        generate an insight.
      </p>

      {data?.run && (
        <div className="feed-stats mono">
          <span>{data.run.source_post_count.toLocaleString('en-US')} direct posts</span>
          <span>{data.run.normalized_post_count.toLocaleString('en-US')} normalized</span>
          <span>{data.run.relation_count.toLocaleString('en-US')} relationships</span>
          <span>{availableDates.length} complete days</span>
        </div>
      )}

      <section className="feed-datebar" aria-label="Feed date">
        <button
          type="button"
          aria-label="Previous date"
          disabled={selectedIndex <= 0}
          onClick={() => setSelectedDate(availableDates[selectedIndex - 1].day)}
        >
          ←
        </button>
        <div>
          <span className="mono">COMPLETE UTC DAY</span>
          <strong>{selectedDate ? fullDate.format(new Date(`${selectedDate}T12:00:00Z`)) : 'Loading…'}</strong>
        </div>
        <button
          type="button"
          aria-label="Next date"
          disabled={selectedIndex < 0 || selectedIndex >= availableDates.length - 1}
          onClick={() => setSelectedDate(availableDates[selectedIndex + 1].day)}
        >
          →
        </button>
      </section>

      <div className="feed-days" role="group" aria-label="Available complete dates">
        {availableDates.map((value) => (
          <button
            type="button"
            key={value.day}
            className={value.day === selectedDate ? 'is-active' : ''}
            onClick={() => setSelectedDate(value.day)}
          >
            <span>{shortDate.format(new Date(`${value.day}T12:00:00Z`))}</span>
            <span className="mono">{value.item_count.toLocaleString('en-US')}</span>
          </button>
        ))}
      </div>

      <div className="feed-tools">
        <input
          className="search feed-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search author, handle, or post…"
          aria-label="Search Feed"
        />
        <div className="seg" aria-label="Feed lane">
          {([
            ['all', 'All evidence'],
            ['network', 'Amplified'],
            ['firsthand', 'First-hand'],
          ] as const).map(([value, label]) => (
            <button
              type="button"
              key={value}
              className={lane === value ? 'is-active' : ''}
              onClick={() => setLane(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <label className="feed-sort">
          <span className="mono">SORT</span>
          <select value={sort} onChange={(event) => setSort(event.target.value as Sort)}>
            <option value="attention">Network attention</option>
            <option value="recent">Most recent</option>
            <option value="engagement">Public engagement</option>
          </select>
        </label>
      </div>

      <div className="feed-summary mono">
        <span>{(data?.total ?? 0).toLocaleString('en-US')} matching evidence items</span>
        <span>55% network attention · 25% originator support · 20% public engagement</span>
      </div>

      <section className="feed-list" aria-live="polite" aria-busy={loading}>
        {loading && items.length === 0
          ? Array.from({ length: 5 }, (_, index) => (
              <div className="feed-skeleton skeleton" key={index} />
            ))
          : items.map((item, index) => (
              <FeedRow key={item.post_id} item={item} rank={index + 1} />
            ))}
        {!loading && items.length === 0 && (
          <div className="registry-empty">
            No evidence matches this date and filter. Try another lane or clear the search.
          </div>
        )}
      </section>

      {data?.total != null && items.length < data.total && (
        <button className="load-more" type="button" onClick={loadMore} disabled={loading}>
          {loading ? 'Loading…' : `Load ${Math.min(PAGE_SIZE, data.total - items.length)} more`}
        </button>
      )}
    </div>
  )
}
