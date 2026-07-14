import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  getJSON,
  type EventEvidence,
  type EventResponse,
  type FeedDates,
  type FeedItem,
  type SignalEvent,
} from '../api'
import {
  getDateWindow,
  shiftDateWindow,
  type DateWindowDirection,
} from '../dateWindow'
import DateNavigator from '../components/DateNavigator'

type Sort = 'attention' | 'recent' | 'engagement'
type TriageFilter = 'all' | 'keep' | 'drop' | 'not_evaluated'

const PAGE_SIZE = 40
const shortDate = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC',
})
const triageSummaryLabels: Record<TriageFilter, string> = {
  all: 'matching',
  keep: 'kept',
  drop: 'dropped',
  not_evaluated: 'not evaluated',
}

interface EventPageRequest {
  date: string
  sort: Sort
  triageFilter: TriageFilter
  query: string
  eventId?: string
  offset?: number
}

const eventPageCache = new Map<string, EventResponse>()
const eventPageRequests = new Map<string, Promise<EventResponse>>()

function eventPageKey({
  date,
  sort,
  triageFilter,
  query,
  eventId,
  offset = 0,
}: EventPageRequest) {
  return `${date}\u0000${sort}\u0000${triageFilter}\u0000${query}\u0000${eventId ?? ''}\u0000${offset}`
}

function requestEventPage(request: EventPageRequest): Promise<EventResponse> {
  const key = eventPageKey(request)
  const cached = eventPageCache.get(key)
  if (cached) return Promise.resolve(cached)
  const inFlight = eventPageRequests.get(key)
  if (inFlight) return inFlight
  const params = new URLSearchParams({
    date: request.date,
    lane: 'all',
    sort: request.sort,
    triage: request.triageFilter,
    q: request.query,
    event_id: request.eventId ?? '',
    limit: String(PAGE_SIZE),
    offset: String(request.offset ?? 0),
  })
  const pending = getJSON<EventResponse>(`/api/events?${params}`)
    .then((value) => {
      eventPageCache.set(key, value)
      return value
    })
    .finally(() => eventPageRequests.delete(key))
  eventPageRequests.set(key, pending)
  return pending
}

const compact = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
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

interface FeedMenuOption<T extends string> {
  value: T
  label: string
  description: string
  count?: number
}

function FeedMenuSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: T
  options: readonly FeedMenuOption<T>[]
  onChange: (value: T) => void
}) {
  const detailsRef = useRef<HTMLDetailsElement>(null)
  const selected = options.find((option) => option.value === value) ?? options[0]

  useEffect(() => {
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!detailsRef.current?.contains(event.target as Node)) {
        detailsRef.current?.removeAttribute('open')
      }
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') detailsRef.current?.removeAttribute('open')
    }
    window.addEventListener('pointerdown', closeOnOutsideClick)
    window.addEventListener('keydown', closeOnEscape)
    return () => {
      window.removeEventListener('pointerdown', closeOnOutsideClick)
      window.removeEventListener('keydown', closeOnEscape)
    }
  }, [])

  return (
    <details className="feed-menu" ref={detailsRef}>
      <summary aria-label={`${label}: ${selected.description}`}>
        <span className="feed-menu-label mono">{label}</span>
        <span className="feed-menu-value">{selected.label}</span>
        {selected.count != null && (
          <span className="feed-menu-count mono">
            {selected.count.toLocaleString('en-US')}
          </span>
        )}
        <span className="feed-menu-caret" aria-hidden="true" />
      </summary>
      <div className="feed-menu-panel" role="menu" aria-label={label}>
        {options.map((option) => (
          <button
            type="button"
            key={option.value}
            className={option.value === value ? 'is-active' : ''}
            onClick={() => {
              onChange(option.value)
              detailsRef.current?.removeAttribute('open')
            }}
            role="menuitemradio"
            aria-checked={option.value === value}
            title={option.description}
          >
            <span>{option.label}</span>
            {option.count != null && (
              <span className="feed-menu-option-count mono">
                {option.count.toLocaleString('en-US')}
              </span>
            )}
          </button>
        ))}
      </div>
    </details>
  )
}

function TriageNote({ item }: { item: SignalEvent }) {
  if (!item.triage) return null
  const { decision, reason } = item.triage
  const decisionLabel = decision === 'keep' ? 'Kept for extraction' : 'Dropped before extraction'

  return (
    <details className={`event-triage event-triage--${decision}`}>
      <summary className="event-triage-heading mono">
        <span className="event-triage-decision">{decisionLabel}</span>
        <span className="event-triage-action">
          <span className="event-triage-view">View reason</span>
          <span className="event-triage-hide">Hide reason</span>
          <span className="event-triage-caret" aria-hidden="true" />
        </span>
      </summary>
      <p>{reason}</p>
    </details>
  )
}

function ScoreDisclosure({
  item,
  rank,
  total,
  date,
  formula,
  open,
  onToggle,
  onClose,
}: {
  item: SignalEvent
  rank: number
  total: number
  date: string
  formula: EventResponse['score_formula']
  open: boolean
  onToggle: () => void
  onClose: () => void
}) {
  const disclosureRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const headingId = useId()
  const panelId = useId()
  const basis = item.daily_score_basis
  const components = basis.score_components
  const networkWeight = formula?.network_attention_weight ?? 0.55
  const originatorWeight = formula?.originator_support_weight ?? 0.25
  const engagementWeight = formula?.public_engagement_weight ?? 0.20
  const rows = [
    {
      label: 'Tracked amplification',
      raw: `${components.registry_amplifiers.toLocaleString('en-US')} tracked ${components.registry_amplifiers === 1 ? 'entity' : 'entities'}`,
      percentile: components.network_attention_percentile,
      weight: networkWeight,
    },
    {
      label: 'Author network support',
      raw: `${components.originator_network_support.toLocaleString('en-US')} Registry entities follow the author`,
      percentile: components.originator_support_percentile,
      weight: originatorWeight,
    },
    {
      label: 'Public engagement',
      raw: `${components.public_interactions.toLocaleString('en-US')} likes, replies, reposts, and quotes`,
      percentile: components.public_engagement_percentile,
      weight: engagementWeight,
    },
  ]

  useEffect(() => {
    if (!open) return
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!disclosureRef.current?.contains(event.target as Node)) onClose()
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      onClose()
      triggerRef.current?.focus()
    }
    const outsideClickTimer = window.setTimeout(() => {
      window.addEventListener('pointerdown', closeOnOutsideClick)
    }, 0)
    window.addEventListener('keydown', closeOnEscape)
    return () => {
      window.clearTimeout(outsideClickTimer)
      window.removeEventListener('pointerdown', closeOnOutsideClick)
      window.removeEventListener('keydown', closeOnEscape)
    }
  }, [open, onClose])

  return (
    <div className="feed-score-disclosure" ref={disclosureRef}>
      <button
        ref={triggerRef}
        type="button"
        className="feed-rank mono"
        aria-label={`Daily rank ${rank} of ${total}. Open daily score explanation.`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={onToggle}
      >
        <strong>#{rank}</strong>
      </button>
      {open && (
        <div
          className="feed-score-popover"
          id={panelId}
          role="dialog"
          aria-labelledby={headingId}
        >
          <div className="feed-score-popover-head">
            <div>
              <h3 id={headingId}>Daily rank #{rank} of {total.toLocaleString('en-US')}</h3>
              <p className="mono">
                Daily score {basis.attention_score.toFixed(1)} ·{' '}
                {shortDate.format(new Date(`${date}T12:00:00Z`))}
              </p>
            </div>
            <button
              type="button"
              className="feed-score-close"
              aria-label="Close score explanation"
              onClick={() => {
                onClose()
                triggerRef.current?.focus()
              }}
            >
              ×
            </button>
          </div>
          {basis.post_id !== item.presentation_root_post_id && (
            <p className="feed-score-source">
              This evidence group uses its highest-scoring member: @{basis.author.handle}.
            </p>
          )}
          <div className="feed-score-components">
            {rows.map((row) => (
              <div className="feed-score-component" key={row.label}>
                <div className="feed-score-component-head">
                  <strong>{row.label}</strong>
                  <span className="mono">{Math.round(row.weight * 100)}%</span>
                </div>
                <p>{row.raw}</p>
                <p className="mono">
                  Higher than {(row.percentile * 100).toFixed(1)}% of that day&rsquo;s
                  scored posts · {(row.percentile * row.weight * 100).toFixed(1)} points
                </p>
              </div>
            ))}
          </div>
          <p className="feed-score-limit">
            The daily score prioritizes what to inspect. It is not importance, truth,
            quality, or the percentage of the network that engaged. Scores from different
            days are not directly comparable.
          </p>
        </div>
      )}
    </div>
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
        {item.parent_missing && (
          <span className="event-parent-missing mono">Parent not captured</span>
        )}
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

function EventEvidenceDetails({
  item,
  relationshipSummary,
}: {
  item: SignalEvent
  relationshipSummary: string[]
}) {
  const [open, setOpen] = useState(false)
  const narrative = item.evidence.filter((evidence) => evidence.relationship !== 'retweet')
  const retweets = item.evidence.filter((evidence) => evidence.relationship === 'retweet')
  const currentNarrative = narrative.filter((evidence) => evidence.is_new_on_day)
  const priorNarrative = narrative.filter((evidence) => !evidence.is_new_on_day)
  const currentRetweets = retweets.filter((evidence) => evidence.is_new_on_day)
  const priorRetweets = retweets.filter((evidence) => !evidence.is_new_on_day)
  const priorCount = priorNarrative.length + priorRetweets.length
  return (
    <details
      className="event-evidence"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>
        <span>
          Follow {relationshipSummary.join(' · ') || `${item.member_count - 1} related posts`}
        </span>
        <span className="mono">
          {item.author_count} {item.author_count === 1 ? 'author' : 'authors'}
        </span>
      </summary>
      {open && (
        <div className="event-thread">
          {item.is_continuation && (
            <div className="event-thread-section mono">Added on this day</div>
          )}
          {currentNarrative.map((evidence) => (
            <RelationshipPost key={evidence.post_id} item={evidence} />
          ))}
          <RetweetTrace items={currentRetweets} />
          {priorCount > 0 && (
            <details className="event-prior-context">
              <summary className="mono">
                Show earlier context · {priorCount} {priorCount === 1 ? 'post' : 'posts'}
              </summary>
              <div>
                {priorNarrative.map((evidence) => (
                  <RelationshipPost key={evidence.post_id} item={evidence} />
                ))}
                <RetweetTrace items={priorRetweets} />
              </div>
            </details>
          )}
        </div>
      )}
    </details>
  )
}

function EventRow({
  item,
  rank,
  total,
  date,
  formula,
  scoreOpen,
  onToggleScore,
  onCloseScore,
  focused,
}: {
  item: SignalEvent
  rank: number
  total: number
  date: string
  formula: EventResponse['score_formula']
  scoreOpen: boolean
  onToggleScore: () => void
  onCloseScore: () => void
  focused: boolean
}) {
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
  ].filter((part): part is string => part !== null)

  return (
    <article
      className={`feed-row event-row${focused ? ' event-row--focused' : ''}`}
      id={`event-${item.event_id}`}
    >
      <ScoreDisclosure
        item={item}
        rank={rank}
        total={total}
        date={date}
        formula={formula}
        open={scoreOpen}
        onToggle={onToggleScore}
        onClose={onCloseScore}
      />

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

        {item.is_continuation && item.previous_activity_day && (
          <div className="event-continuation-note mono">
            <span>
              Continued from {shortDate.format(new Date(`${item.previous_activity_day}T12:00:00Z`))}
            </span>
            <span>
              {item.day_member_count} new {item.day_member_count === 1 ? 'post' : 'posts'} today
            </span>
          </div>
        )}

        <TriageNote item={item} />

        {item.is_grouped && (
          <EventEvidenceDetails
            item={item}
            relationshipSummary={relationshipSummary}
          />
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
  const [urlSearchParams, setUrlSearchParams] = useSearchParams()
  const initialLinkedDate = useRef(urlSearchParams.get('date') ?? '')
  const [targetEventId, setTargetEventId] = useState(
    () => urlSearchParams.get('event') ?? '',
  )
  const [dates, setDates] = useState<FeedDates | null>(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [sort, setSort] = useState<Sort>('attention')
  const [triageFilter, setTriageFilter] = useState<TriageFilter>('keep')
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [data, setData] = useState<EventResponse | null>(null)
  const [items, setItems] = useState<SignalEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [openScoreEventId, setOpenScoreEventId] = useState<string | null>(null)
  const [dateWindowEnd, setDateWindowEnd] = useState(0)
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
    getJSON<FeedDates>('/api/events/dates')
      .then((value) => {
        setDates(value)
        setDateWindowEnd(value.dates?.length ?? 0)
        if (value.available && value.latest_complete_date) {
          setSelectedDate((current) => {
            if (value.dates?.some((date) => date.day === current)) return current
            if (value.dates?.some((date) => date.day === initialLinkedDate.current)) {
              return initialLinkedDate.current
            }
            return value.latest_complete_date ?? ''
          })
        }
      })
      .catch(() => setError('Couldn’t load available Feed dates. Reload to try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query), 180)
    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (!selectedDate) return
    let live = true
    const request = {
      date: selectedDate,
      sort,
      triageFilter,
      query: debouncedQuery,
      eventId: targetEventId,
      offset: 0,
    }
    const viewKey = eventPageKey(request)
    activeViewKeyRef.current = viewKey
    setOpenScoreEventId(null)
    const cached = eventPageCache.get(viewKey)
    if (cached) {
      setData(cached)
      setItems(cached.items ?? [])
      setLoading(false)
      setError('')
      return
    }
    setLoading(true)
    setError('')
    setData(null)
    setItems([])
    requestEventPage(request)
      .then((value) => {
        if (!live || activeViewKeyRef.current !== viewKey) return
        setData(value)
        setItems(value.items ?? [])
      })
      .catch(() => {
        if (live && activeViewKeyRef.current === viewKey) {
          setError('Couldn’t load this Feed view. Change the filter or reload to try again.')
        }
      })
      .finally(() => {
        if (live && activeViewKeyRef.current === viewKey) setLoading(false)
      })
    return () => {
      live = false
    }
  }, [selectedDate, sort, triageFilter, debouncedQuery, targetEventId])

  useEffect(() => {
    if (!selectedDate || sort !== 'attention' || debouncedQuery || targetEventId) return
    let cancelled = false
    const timer = window.setTimeout(async () => {
      for (const value of visibleDates) {
        if (cancelled || value.day === selectedDate) continue
        try {
          await requestEventPage({
            date: value.day,
            sort: 'attention',
            triageFilter,
            query: '',
            offset: 0,
          })
        } catch {
          // Prefetch is opportunistic; foreground requests still surface errors.
        }
      }
    }, 350)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [visibleDates, selectedDate, sort, triageFilter, debouncedQuery, targetEventId])

  useEffect(() => {
    if (!targetEventId || !items.some((item) => item.event_id === targetEventId)) return
    document.getElementById(`event-${targetEventId}`)?.scrollIntoView({ block: 'start' })
  }, [items, targetEventId])

  const clearTargetEvent = () => {
    if (!targetEventId) return
    setTargetEventId('')
    setUrlSearchParams({}, { replace: true })
  }

  const hasSearch = debouncedQuery.trim().length > 0

  const moveDateWindow = (direction: DateWindowDirection) => {
    clearTargetEvent()
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
    if (!data?.total || items.length >= data.total) return
    const viewKey = eventPageKey({
      date: selectedDate,
      sort,
      triageFilter,
      query: debouncedQuery,
      offset: 0,
    })
    if (activeViewKeyRef.current !== viewKey) return
    setLoading(true)
    setError('')
    requestEventPage({
      date: selectedDate,
      sort,
      triageFilter,
      query: debouncedQuery,
      offset: items.length,
    })
      .then((value) => {
        if (activeViewKeyRef.current !== viewKey) return
        setItems((current) => [...current, ...(value.items ?? [])])
      })
      .catch(() => {
        if (activeViewKeyRef.current === viewKey) {
          setError('Couldn’t load more Feed items. Try again.')
        }
      })
      .finally(() => {
        if (activeViewKeyRef.current === viewKey) setLoading(false)
      })
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
      <header className="page-head">
        <h1 className="page-title">What is the network paying attention to?</h1>
        <p className="page-sub">
          Each day&rsquo;s posts from tracked labs and people, ranked by who in
          the network amplified them — not by raw engagement.
        </p>
        <p className="page-method-line mono">
          <a href="/architecture#ranking-methods">How scoring works ↗</a>
        </p>
      </header>

      <section className="feed-calendar" aria-label="Available complete UTC days">
        <DateNavigator
          dates={visibleDates}
          selectedDate={selectedDate}
          onSelectDate={(day) => {
            clearTargetEvent()
            setSelectedDate(day)
          }}
          canShowOlderDates={canShowOlderDates}
          canShowNewerDates={canShowNewerDates}
          onShowOlderDates={() => moveDateWindow('older')}
          onShowNewerDates={() => moveDateWindow('newer')}
          ariaLabel="Feed date"
          loading={dates === null}
        />
      </section>

      <div className="feed-tools">
        <input
          className="search feed-search"
          type="search"
          value={query}
          onChange={(event) => {
            clearTargetEvent()
            setQuery(event.target.value)
          }}
          placeholder="Search author, handle, or post…"
          aria-label="Search Feed"
        />
        <div className="feed-controls">
          <FeedMenuSelect
            label="AUDIT"
            value={triageFilter}
            onChange={(value) => {
              clearTargetEvent()
              setTriageFilter(value)
            }}
            options={([
              ['keep', 'Kept', 'Kept for extraction'],
              ['drop', 'Dropped', 'Dropped before extraction'],
              ['not_evaluated', 'Not evaluated', 'Not evaluated by triage'],
              ['all', 'All', 'All evidence'],
            ] as const).map(([value, label, description]) => ({
              value,
              label,
              description,
              count: data?.triage_counts?.[value],
            }))}
          />
          <FeedMenuSelect
            label="SORT"
            value={sort}
            onChange={(value) => {
              clearTargetEvent()
              setSort(value)
            }}
            options={[
              { value: 'attention', label: 'Score', description: 'Daily score' },
              { value: 'recent', label: 'Recent', description: 'Most recent' },
              { value: 'engagement', label: 'Engagement', description: 'Public engagement' },
            ]}
          />
        </div>
      </div>

      {hasSearch && (
        <div className="feed-summary mono">
          {(data?.total ?? 0).toLocaleString('en-US')}{' '}
          {triageSummaryLabels[triageFilter]} Feed items
        </div>
      )}

      {error && data && (
        <p className="error-note feed-error" role="alert">{error}</p>
      )}

      <section className="feed-list" aria-live="polite" aria-busy={loading}>
        {loading && items.length === 0
          ? Array.from({ length: 5 }, (_, index) => (
              <div className="feed-skeleton skeleton" key={index} />
            ))
          : items.map((item) => (
              <EventRow
                key={item.event_id}
                item={item}
                rank={item.daily_rank}
                total={data?.daily_rank_total ?? data?.triage_counts?.all ?? items.length}
                date={selectedDate}
                formula={data?.score_formula}
                scoreOpen={openScoreEventId === item.event_id}
                onToggleScore={() =>
                  setOpenScoreEventId((current) =>
                    current === item.event_id ? null : item.event_id,
                  )
                }
                onCloseScore={() => setOpenScoreEventId(null)}
                focused={targetEventId === item.event_id}
              />
            ))}
        {!loading && items.length === 0 && (
          <div className="registry-empty">
            No evidence matches these audit filters. Try another day or clear the filters.
          </div>
        )}
      </section>

      {!targetEventId && data?.total != null && items.length < data.total && (
        <button className="load-more" type="button" onClick={loadMore} disabled={loading}>
          {loading
            ? 'Loading…'
            : `Load ${Math.min(PAGE_SIZE, data.total - items.length)} more`}
        </button>
      )}
    </div>
  )
}
