import { useEffect, useMemo, useState } from 'react'
import {
  getJSON,
  type EventEvidence,
  type EventResponse,
  type FeedDates,
  type FeedItem,
  type FeedResponse,
  type SignalEvent,
} from '../api'

type Lane = 'all' | 'network' | 'firsthand'
type Sort = 'attention' | 'recent' | 'engagement'
type View = 'posts' | 'events'

const PAGE_SIZE = 40

const compact = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
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

const evidenceTypeLabel: Record<EventEvidence['post_type'], string> = {
  original: 'Original',
  quote: 'Quoted',
  retweet: 'Retweeted',
  reply: 'Replied',
}

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <span>
      <b>{fmt(value)}</b> {label}
    </span>
  )
}

function FeedRow({ item }: { item: FeedItem }) {
  const c = item.score_components
  const isLong = item.text.length > 680
  const rationale = [
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
      <div
        className="feed-rank mono"
        aria-label={`Attention score ${item.attention_score.toFixed(1)}`}
      >
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
              <span className="feed-lane feed-lane--network">amplified</span>
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

function EventRow({ item }: { item: SignalEvent }) {
  const representative = item.representative
  const isLong = representative.text.length > 680

  return (
    <article className="feed-row event-row">
      <div
        className="feed-rank mono"
        aria-label={`Peak attention score ${item.peak_attention_score.toFixed(1)}`}
      >
        <strong>{item.peak_attention_score.toFixed(1)}</strong>
        <span>peak attention</span>
      </div>

      <div className="feed-body">
        <header className="feed-byline">
          <div>
            <strong>
              {representative.author.entity_name ?? representative.author.name}
            </strong>
            <a
              href={`https://x.com/${representative.author.handle}`}
              target="_blank"
              rel="noreferrer"
            >
              @{representative.author.handle}
            </a>
          </div>
          <div className="feed-meta mono">
            <span className="feed-lane feed-lane--network">exact group</span>
            <time dateTime={item.latest_evidence_at}>
              {time.format(new Date(item.latest_evidence_at))}
            </time>
          </div>
        </header>

        {isLong ? (
          <details className="feed-long-post">
            <summary>
              <span className="feed-text">{representative.text.slice(0, 680)}…</span>
              <span className="feed-expand-label mono">Read representative post</span>
            </summary>
            <p className="feed-text">{representative.text}</p>
          </details>
        ) : (
          <p className="feed-text">
            {representative.text || <span className="muted">Post has no text.</span>}
          </p>
        )}

        <div className="feed-proof event-proof">
          <div className="feed-why">
            <span className="feed-proof-label">GROUPED BECAUSE</span>
            <span>{item.why_grouped.join(' · ')}</span>
          </div>
          <div className="event-group-stats mono">
            <span>{item.member_count} posts</span>
            <span>{item.author_count} authors</span>
            <span>{item.registry_account_count} Registry accounts</span>
            <span>{item.link_count} exact links</span>
          </div>
        </div>

        <details className="event-evidence">
          <summary className="mono">
            Show {item.member_count} evidence posts
            <span>Every post remains independently traceable</span>
          </summary>
          <div className="event-evidence-list">
            {item.evidence.map((evidence) => (
              <article
                className={`event-evidence-row${
                  evidence.post_type === 'retweet'
                    ? ' event-evidence-row--retweet'
                    : ''
                }`}
                key={evidence.post_id}
              >
                <div className="event-evidence-meta mono">
                  <strong>
                    {evidence.author.entity_name ?? evidence.author.name}
                  </strong>
                  <span>@{evidence.author.handle}</span>
                  <span>{evidenceTypeLabel[evidence.post_type]}</span>
                  <time dateTime={evidence.published_at}>
                    {time.format(new Date(evidence.published_at))}
                  </time>
                </div>
                <div>
                  {evidence.post_type === 'retweet' ? (
                    <p className="event-evidence-action">Retweeted the original post.</p>
                  ) : (
                    <p>{evidence.text || 'Post has no text.'}</p>
                  )}
                  <a href={evidence.url} target="_blank" rel="noreferrer">
                    Open {evidence.post_type === 'retweet' ? 'retweet' : 'evidence'} on X ↗
                  </a>
                </div>
              </article>
            ))}
          </div>
        </details>
      </div>
    </article>
  )
}

export default function Feed() {
  const [view, setView] = useState<View>('posts')
  const [dates, setDates] = useState<FeedDates | null>(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [lane, setLane] = useState<Lane>('all')
  const [sort, setSort] = useState<Sort>('attention')
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [data, setData] = useState<FeedResponse | null>(null)
  const [items, setItems] = useState<FeedItem[]>([])
  const [eventData, setEventData] = useState<EventResponse | null>(null)
  const [eventItems, setEventItems] = useState<SignalEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    getJSON<FeedDates>(view === 'events' ? '/api/events/dates' : '/api/feed/dates')
      .then((value) => {
        setDates(value)
        if (value.available && value.latest_complete_date) {
          setSelectedDate((current) =>
            value.dates?.some((date) => date.day === current)
              ? current
              : value.latest_complete_date ?? '',
          )
        }
      })
      .catch((reason) => setError(String(reason)))
      .finally(() => setLoading(false))
  }, [view])

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
    const request =
      view === 'events'
        ? getJSON<EventResponse>(`/api/events?${params}`).then((value) => {
            if (!live) return
            setEventData(value)
            setEventItems(value.items ?? [])
          })
        : getJSON<FeedResponse>(`/api/feed?${params}`).then((value) => {
            if (!live) return
            setData(value)
            setItems(value.items ?? [])
          })
    request
      .catch((reason) => live && setError(String(reason)))
      .finally(() => live && setLoading(false))
    return () => {
      live = false
    }
  }, [selectedDate, lane, sort, debouncedQuery, view])

  const availableDates = useMemo(() => dates?.dates ?? [], [dates])
  const hasNarrowedResults = lane !== 'all' || debouncedQuery.trim().length > 0

  const loadMore = () => {
    const currentTotal = view === 'events' ? eventData?.total : data?.total
    const currentLength = view === 'events' ? eventItems.length : items.length
    if (!currentTotal || currentLength >= currentTotal) return
    const params = new URLSearchParams({
      date: selectedDate,
      lane,
      sort,
      q: debouncedQuery,
      limit: String(PAGE_SIZE),
      offset: String(currentLength),
    })
    setLoading(true)
    const request =
      view === 'events'
        ? getJSON<EventResponse>(`/api/events?${params}`).then((value) =>
            setEventItems((current) => [...current, ...(value.items ?? [])]),
          )
        : getJSON<FeedResponse>(`/api/feed?${params}`).then((value) =>
            setItems((current) => [...current, ...(value.items ?? [])]),
          )
    request
      .catch((reason) => setError(String(reason)))
      .finally(() => setLoading(false))
  }

  const activeData = view === 'events' ? eventData : data
  const activeItems = view === 'events' ? eventItems : items

  if (error && !activeData) {
    return (
      <div className="page feed-page">
        <h1 className="page-title">What is the network paying attention to?</h1>
        <p className="error-note">{error}</p>
      </div>
    )
  }

  if (dates && !dates.available) {
    return (
      <div className="page feed-page">
        <h1 className="page-title">What is the network paying attention to?</h1>
        <p className="page-sub mono">{dates.reason}</p>
      </div>
    )
  }

  return (
    <div className="page feed-page">
      <h1 className="page-title">What is the network paying attention to?</h1>
      <p className="page-sub">
        Posts are the complete evidence ledger. Exact groups connect only
        provider-stated targets, reply parents, or conversation IDs — never
        inferred topics.
      </p>

      {data?.run && (
        <details className="method-note page-method mono">
          <summary>Method</summary>
          <p>
            <a href="/architecture#ranking-methods">ATTENTION-V1 scoring formula</a>
            {' '}·{' '}
            {data.run.source_post_count.toLocaleString('en-US')} direct posts ·{' '}
            {data.run.normalized_post_count.toLocaleString('en-US')} normalized ·{' '}
            {data.run.relation_count.toLocaleString('en-US')} relationships
          </p>
        </details>
      )}

      <section className="feed-viewbar" aria-label="Feed evidence view">
        <div className="seg">
          {([
            ['events', 'Exact groups'],
            ['posts', 'All posts'],
          ] as const).map(([value, label]) => (
            <button
              type="button"
              key={value}
              className={view === value ? 'is-active' : ''}
              onClick={() => setView(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      <section className="feed-calendar" aria-label="Available complete UTC days">
        <span className="feed-calendar-label mono">Complete UTC days</span>
        <div className="feed-days" role="group" aria-label="Feed date">
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
      </section>

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
        <div className="feed-sort" role="group" aria-label="Sort Feed">
          <span className="mono">SORT</span>
          <div className="seg">
            {([
              ['attention', 'Attention', 'Network attention'],
              ['recent', 'Recent', 'Most recent'],
              ['engagement', 'Engagement', 'Public engagement'],
            ] as const).map(([value, label, description]) => (
              <button
                type="button"
                key={value}
                className={sort === value ? 'is-active' : ''}
                onClick={() => setSort(value)}
                aria-label={description}
                aria-pressed={sort === value}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {hasNarrowedResults && (
        <div className="feed-summary mono">
          {(activeData?.total ?? 0).toLocaleString('en-US')}{' '}
          {view === 'events' ? 'matching exact groups' : 'matching evidence items'}
        </div>
      )}

      <section className="feed-list" aria-live="polite" aria-busy={loading}>
        {loading && activeItems.length === 0
          ? Array.from({ length: 5 }, (_, index) => (
              <div className="feed-skeleton skeleton" key={index} />
            ))
          : view === 'events'
            ? eventItems.map((item) => (
                <EventRow key={item.event_id} item={item} />
              ))
            : items.map((item) => (
                <FeedRow key={item.post_id} item={item} />
              ))}
        {!loading && activeItems.length === 0 && (
          <div className="registry-empty">
            {view === 'events'
              ? 'No exact structural groups match this date and filter. Every ungrouped post remains available in All posts.'
              : 'No evidence matches this date and filter. Try another lane or clear the search.'}
          </div>
        )}
      </section>

      {activeData?.total != null && activeItems.length < activeData.total && (
        <button className="load-more" type="button" onClick={loadMore} disabled={loading}>
          {loading
            ? 'Loading…'
            : `Load ${Math.min(PAGE_SIZE, activeData.total - activeItems.length)} more`}
        </button>
      )}
    </div>
  )
}
