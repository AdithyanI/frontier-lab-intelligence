import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import {
  getJSON,
  type EventEvidence,
  type EventResponse,
  type FeedDates,
  type FeedItem,
  type SignalEvent,
} from '../api'

type Sort = 'attention' | 'recent' | 'engagement'

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

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <span>
      <b>{fmt(value)}</b> {label}
    </span>
  )
}

function PostText({ item }: { item: Pick<FeedItem, 'text'> }) {
  const isLong = item.text.length > 680
  if (!isLong) {
    return (
      <p className="feed-text">
        {item.text || <span className="muted">Post has no text.</span>}
      </p>
    )
  }
  return (
    <details className="feed-long-post">
      <summary>
        <span className="feed-text">{item.text.slice(0, 680)}…</span>
        <span className="feed-expand-label mono">Read full post</span>
      </summary>
      <p className="feed-text">{item.text}</p>
    </details>
  )
}

function RelationshipPost({ item }: { item: EventEvidence }) {
  const label =
    item.relationship === 'reply'
      ? item.same_author_as_root
        ? 'Thread continuation'
        : 'Reply'
      : item.relationship === 'quote'
        ? 'Quote'
        : 'Related post'
  const style = {
    '--thread-depth': Math.max(1, item.depth),
  } as CSSProperties

  return (
    <article
      className={`event-relationship event-relationship--${item.relationship}${
        item.same_author_as_root ? ' event-relationship--continuation' : ''
      }`}
      style={style}
    >
      <header>
        <span className="event-relationship-kind mono">{label}</span>
        <strong>{item.author.entity_name ?? item.author.name}</strong>
        <span className="mono">@{item.author.handle}</span>
        <time className="mono" dateTime={item.published_at}>
          {time.format(new Date(item.published_at))}
        </time>
      </header>
      <p>{item.text || 'Post has no text.'}</p>
      <a className="mono" href={item.url} target="_blank" rel="noreferrer">
        Open {label.toLowerCase()} on X ↗
      </a>
    </article>
  )
}

function RetweetTrace({ items }: { items: EventEvidence[] }) {
  if (items.length === 0) return null
  const preview = items
    .slice(0, 3)
    .map((item) => item.author.entity_name ?? item.author.name)
    .join(', ')
  const remainder = items.length - 3

  return (
    <details className="event-retweets">
      <summary>
        <span className="event-relationship-kind mono">Retweeted by</span>
        <span>
          {preview}
          {remainder > 0 ? ` +${remainder} more` : ''}
        </span>
      </summary>
      <div className="event-retweet-links mono">
        {items.map((item) => (
          <a key={item.post_id} href={item.url} target="_blank" rel="noreferrer">
            {item.author.entity_name ?? item.author.name}
            <span>@{item.author.handle} · {time.format(new Date(item.published_at))}</span>
          </a>
        ))}
      </div>
    </details>
  )
}

function EventRow({ item }: { item: SignalEvent }) {
  const root = item.root
  const replies = item.evidence.filter((evidence) => evidence.relationship === 'reply')
  const continuations = replies.filter((evidence) => evidence.same_author_as_root)
  const externalReplies = replies.filter((evidence) => !evidence.same_author_as_root)
  const quotes = item.evidence.filter((evidence) => evidence.relationship === 'quote')
  const retweets = item.evidence.filter(
    (evidence) => evidence.relationship === 'retweet',
  )
  const related = item.evidence.filter(
    (evidence) => evidence.relationship === 'related',
  )
  const narrative = [...replies, ...quotes, ...related]
  const c = root.score_components
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
  const relationshipSummary = [
    continuations.length
      ? `${continuations.length} thread ${continuations.length === 1 ? 'continuation' : 'continuations'}`
      : null,
    externalReplies.length
      ? `${externalReplies.length} ${externalReplies.length === 1 ? 'reply' : 'replies'}`
      : null,
    quotes.length ? `${quotes.length} ${quotes.length === 1 ? 'quote' : 'quotes'}` : null,
    retweets.length
      ? `${retweets.length} ${retweets.length === 1 ? 'retweet' : 'retweets'}`
      : null,
    related.length
      ? `${related.length} linked ${related.length === 1 ? 'post' : 'posts'}`
      : null,
  ].filter(Boolean)

  return (
    <article className="feed-row event-row">
      <div
        className="feed-rank mono"
        aria-label={`Attention score ${item.peak_attention_score.toFixed(1)}`}
      >
        <strong>{item.peak_attention_score.toFixed(1)}</strong>
        <span>attention</span>
      </div>

      <div className="feed-body">
        <header className="feed-byline">
          <div>
            <strong>{root.author.entity_name ?? root.author.name}</strong>
            <a href={`https://x.com/${root.author.handle}`} target="_blank" rel="noreferrer">
              @{root.author.handle}
            </a>
          </div>
          <div className="feed-meta mono">
            {item.is_grouped && <span>{item.member_count} related</span>}
            {!item.is_grouped && root.post_type === 'quote' && <span>quote</span>}
            <time dateTime={root.published_at}>{time.format(new Date(root.published_at))}</time>
          </div>
        </header>

        <PostText item={root} />

        {root.context && !item.is_grouped && (
          <div className="feed-context mono">
            Quotes @{root.context.target_handle} · post {root.context.target_post_id}
          </div>
        )}

        <div className="feed-proof event-proof">
          <div className="feed-why">
            <span className="feed-proof-label">
              {item.is_grouped ? 'EXACT RELATION' : 'WHY HERE'}
            </span>
            <span>
              {item.is_grouped ? item.why_grouped.join(' · ') : rationale.join(' · ')}
            </span>
          </div>
        </div>

        {item.amplifiers.length > 0 && (
          <div className="feed-amplifiers" aria-label="Registry amplifiers">
            <span className="feed-proof-label">NETWORK ATTENTION</span>
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
            {item.amplifiers.length > 6 && <span>+{item.amplifiers.length - 6} more</span>}
          </div>
        )}

        {item.is_grouped && (
          <details className="event-evidence">
            <summary>
              <span>
                Follow {relationshipSummary.join(' · ') || `${item.member_count - 1} related posts`}
              </span>
              <span className="mono">{item.author_count} authors · exact links only</span>
            </summary>
            <div className="event-thread">
              {narrative.map((evidence) => (
                <RelationshipPost key={evidence.post_id} item={evidence} />
              ))}
              <RetweetTrace items={retweets} />
            </div>
          </details>
        )}

        <footer className="feed-footer mono">
          <div className="feed-metrics">
            <Metric label="likes" value={root.metrics.likes} />
            <Metric label="reposts" value={root.metrics.reposts} />
            <Metric label="replies" value={root.metrics.replies} />
            <Metric label="views" value={root.metrics.views} />
          </div>
          <a href={root.url} target="_blank" rel="noreferrer">
            Open root post on X ↗
          </a>
        </footer>
      </div>
    </article>
  )
}

export default function Feed() {
  const [dates, setDates] = useState<FeedDates | null>(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [sort, setSort] = useState<Sort>('attention')
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [data, setData] = useState<EventResponse | null>(null)
  const [items, setItems] = useState<SignalEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    getJSON<FeedDates>('/api/events/dates')
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
      lane: 'all',
      sort,
      q: debouncedQuery,
      limit: String(PAGE_SIZE),
      offset: '0',
    })
    getJSON<EventResponse>(`/api/events?${params}`)
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
  }, [selectedDate, sort, debouncedQuery])

  const availableDates = useMemo(() => dates?.dates ?? [], [dates])
  const hasSearch = debouncedQuery.trim().length > 0

  const loadMore = () => {
    if (!data?.total || items.length >= data.total) return
    const params = new URLSearchParams({
      date: selectedDate,
      lane: 'all',
      sort,
      q: debouncedQuery,
      limit: String(PAGE_SIZE),
      offset: String(items.length),
    })
    setLoading(true)
    getJSON<EventResponse>(`/api/events?${params}`)
      .then((value) => setItems((current) => [...current, ...(value.items ?? [])]))
      .catch((reason) => setError(String(reason)))
      .finally(() => setLoading(false))
  }

  if (error && !data) {
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
        One evidence stream. Exact X relationships connect a root post to its
        replies, quotes, and retweets; unrelated posts remain independently traceable.
      </p>

      {data?.run && (
        <details className="method-note page-method mono">
          <summary>Method</summary>
          <p>
            <a href="/architecture#ranking-methods">ATTENTION-V1 scoring formula</a>
            {' '}· {data.run.clustering_contract} · singleton posts retained
          </p>
        </details>
      )}

      <section className="feed-calendar" aria-label="Available complete UTC days">
        <span className="feed-calendar-label mono">Complete UTC days · evidence posts</span>
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

      {hasSearch && (
        <div className="feed-summary mono">
          {(data?.total ?? 0).toLocaleString('en-US')} matching Feed items
        </div>
      )}

      <section className="feed-list" aria-live="polite" aria-busy={loading}>
        {loading && items.length === 0
          ? Array.from({ length: 5 }, (_, index) => (
              <div className="feed-skeleton skeleton" key={index} />
            ))
          : items.map((item) => <EventRow key={item.event_id} item={item} />)}
        {!loading && items.length === 0 && (
          <div className="registry-empty">
            No evidence matches this date and search. Try another day or clear the search.
          </div>
        )}
      </section>

      {data?.total != null && items.length < data.total && (
        <button className="load-more" type="button" onClick={loadMore} disabled={loading}>
          {loading
            ? 'Loading…'
            : `Load ${Math.min(PAGE_SIZE, data.total - items.length)} more`}
        </button>
      )}
    </div>
  )
}
