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
  getCachedJSON,
  eventPageUrl,
  type EventEvidence,
  type EventResponse,
  type FeedDates,
  type FeedItem,
  type FeedEvent,
} from '../../shared/api'
import {
  getDateWindowEndForSelection,
  getDateWindow,
  shiftDateWindow,
  type DateWindowDirection,
} from '../../shared/date/dateWindow'
import DateNavigator from '../../shared/components/DateNavigator'
import CopyEventId from '../../shared/components/CopyEventId'
import { useAuditDate } from '../../shared/date/auditDateStore'
import { readAuditDate, setAuditDateParam } from '../../shared/date/auditDate'
import {
  initialFeedRoutingFilter,
  type FeedRoutingFilter,
} from './feedState'

type Sort = 'rank' | 'recent' | 'engagement'
type RoutingFilter = FeedRoutingFilter

const PAGE_SIZE = 20
const shortDate = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC',
})
const routingSummaryLabels: Record<RoutingFilter, string> = {
  all: 'all',
  relevant: 'relevant',
  not_relevant: 'not-relevant',
  not_evaluated: 'not-evaluated',
}
interface EventPageRequest {
  date: string
  sort: Sort
  routingFilter: RoutingFilter
  query: string
  eventId?: string
  offset?: number
}

const eventPageCache = new Map<string, EventResponse>()
const eventPageRequests = new Map<string, Promise<EventResponse>>()
const eventEvidenceCache = new Map<string, EventEvidence[]>()
const eventEvidenceRequests = new Map<string, Promise<EventEvidence[]>>()

function eventPageKey({
  date,
  sort,
  routingFilter,
  query,
  eventId,
  offset = 0,
}: EventPageRequest) {
  return `${date}\u0000${sort}\u0000${routingFilter}\u0000${query}\u0000${eventId ?? ''}\u0000${offset}`
}

function requestEventPage(request: EventPageRequest): Promise<EventResponse> {
  const key = eventPageKey(request)
  const cached = eventPageCache.get(key)
  if (cached) return Promise.resolve(cached)
  const inFlight = eventPageRequests.get(key)
  if (inFlight) return inFlight
  const pending = getCachedJSON<EventResponse>(
    eventPageUrl({ ...request, limit: PAGE_SIZE }),
  )
    .then((value) => {
      eventPageCache.set(key, value)
      return value
    })
    .finally(() => eventPageRequests.delete(key))
  eventPageRequests.set(key, pending)
  return pending
}

function requestEventEvidence(date: string, eventId: string): Promise<EventEvidence[]> {
  const key = `${date}\u0000${eventId}`
  const cached = eventEvidenceCache.get(key)
  if (cached) return Promise.resolve(cached)
  const inFlight = eventEvidenceRequests.get(key)
  if (inFlight) return inFlight
  const params = new URLSearchParams({
    date,
    lane: 'all',
    sort: 'rank',
    routing: 'all',
    q: '',
    event_id: eventId,
    include_evidence: 'true',
    limit: '1',
    offset: '0',
  })
  const pending = getJSON<EventResponse>(`/api/events?${params}`)
    .then((value) => {
      const evidence = value.items?.[0]?.evidence ?? []
      eventEvidenceCache.set(key, evidence)
      return evidence
    })
    .finally(() => eventEvidenceRequests.delete(key))
  eventEvidenceRequests.set(key, pending)
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
      <div className="feed-menu-panel" role="group" aria-label={label}>
        {options.map((option) => (
          <button
            type="button"
            key={option.value}
            className={option.value === value ? 'is-active' : ''}
            onClick={() => {
              onChange(option.value)
              detailsRef.current?.removeAttribute('open')
            }}
            aria-pressed={option.value === value}
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

function RoutingNote({ item }: { item: FeedEvent }) {
  const routing = item.audience_routing
  if (!routing) return null
  const routedToNeither =
    !routing.ai_engineering.relevant && !routing.investment.relevant

  return (
    <details className="event-routing">
      <summary className="event-routing-heading mono">
        <span className="event-routing-status">
          <span className="sr-only">Audience routing. </span>
          <span className="event-audience-marks">
            {routing.ai_engineering.relevant && (
              <>
                <span className="event-audience-mark" aria-hidden="true">ENG</span>
                <span className="sr-only">Relevant to AI Engineering. </span>
              </>
            )}
            {routing.investment.relevant && (
              <>
                <span className="event-audience-mark" aria-hidden="true">INV</span>
                <span className="sr-only">Relevant to Investment. </span>
              </>
            )}
            {routedToNeither && (
              <span className="event-routing-neither">Neither audience</span>
            )}
          </span>
        </span>
        <span className="event-routing-action">
          <span className="event-routing-view">View reasons</span>
          <span className="event-routing-hide">Hide reasons</span>
          <span className="event-routing-caret" aria-hidden="true" />
        </span>
      </summary>
      <div className="event-routing-reasons">
        <div className="event-routing-reason">
          <span className="event-routing-reason-label mono">
            AI Engineering · {routing.ai_engineering.relevant ? 'Relevant' : 'Not relevant'}
          </span>
          <p>{routing.ai_engineering.reason}</p>
        </div>
        <div className="event-routing-reason">
          <span className="event-routing-reason-label mono">
            Investment · {routing.investment.relevant ? 'Relevant' : 'Not relevant'}
          </span>
          <p>{routing.investment.reason}</p>
        </div>
      </div>
    </details>
  )
}

function RankDisclosure({
  item,
  rank,
  total,
  date,
  open,
  onToggle,
  onClose,
}: {
  item: FeedEvent
  rank: number
  total: number
  date: string
  open: boolean
  onToggle: () => void
  onClose: () => void
}) {
  const disclosureRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const headingId = useId()
  const panelId = useId()
  const components = item.rank_components
  const voterNames = components.voters
    .slice(0, 5)
    .map((voter) => voter.entity_name || `@${voter.handle}`)
    .join(', ')
  const rows = [
    {
      layer: 1,
      label: 'Trusted votes',
      raw: `${components.trusted_votes.toLocaleString('en-US')} distinct trusted ${components.trusted_votes === 1 ? 'entity' : 'entities'}`,
      detail: voterNames
        ? `One vote per Registry entity across the complete Event; source entity excluded after union. ${voterNames}`
        : 'One vote per Registry entity across the complete Event; source entity excluded after union. No trusted voter observed.',
    },
    {
      layer: 2,
      label: 'Who voted',
      raw: `Average network position ${components.mean_voter_position.toFixed(6)}`,
      detail:
        'Mean entity percentile: the share of other ranked Registry entities with lower network support. Ties share one value.',
    },
    {
      layer: 3,
      label: 'Source author standing',
      raw: `Network position ${components.author_position.toFixed(6)}`,
      detail: 'The same tie-aware entity percentile, used only when the first two layers tie',
    },
    {
      layer: 4,
      label: 'Public engagement',
      raw: `${components.public_interactions.toLocaleString('en-US')} likes, replies, reposts, and quotes`,
      detail: 'Highest one-post total among same-day Event members',
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
    <div className="feed-rank-disclosure" ref={disclosureRef}>
      <button
        ref={triggerRef}
        type="button"
        className="feed-rank mono"
        aria-label={`Daily rank ${rank} of ${total}. Open rank explanation.`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={onToggle}
      >
        <strong>#{rank}</strong>
      </button>
      {open && (
        <div
          className="feed-rank-popover"
          id={panelId}
          role="dialog"
          aria-labelledby={headingId}
        >
          <div className="feed-rank-popover-head">
            <div>
              <h3 id={headingId}>Daily rank #{rank} of {total.toLocaleString('en-US')}</h3>
              <p className="mono">
                {components.version} · {shortDate.format(new Date(`${date}T12:00:00Z`))}
              </p>
            </div>
            <button
              type="button"
              className="feed-rank-close"
              aria-label="Close rank explanation"
              onClick={() => {
                onClose()
                triggerRef.current?.focus()
              }}
            >
              ×
            </button>
          </div>
          <div className="feed-rank-components">
            {rows.map((row) => (
              <div className="feed-rank-component" key={row.label}>
                <div className="feed-rank-component-head">
                  <strong>{row.layer}. {row.label}</strong>
                  {components.decided_at_layer === row.layer && (
                    <span className="mono">decided the adjacent tie</span>
                  )}
                </div>
                <p>{row.raw}</p>
                <p className="mono">{row.detail}</p>
              </div>
            ))}
          </div>
          {components.decided_at_layer === 5 && (
            <p className="feed-rank-source">
              All four substantive layers tied; Event ID supplied deterministic order.
            </p>
          )}
          <p className="feed-rank-limit">
            The daily rank prioritizes what to inspect. It is not importance, truth,
            quality, or the percentage of the network that engaged. Ranks from different
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
        ? 'Author reply'
        : 'Reply'
      : item.relationship === 'quote'
        ? item.same_author_as_root
          ? 'Author quote'
          : 'Quote'
        : item.same_author_as_root
          ? 'Author update'
          : 'Related post'
  const style = {
    '--thread-depth': Math.max(1, item.depth),
  } as CSSProperties

  return (
    <article
      className={`event-relationship event-relationship--${item.relationship}`}
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
  date,
  relationshipSummary,
}: {
  item: FeedEvent
  date: string
  relationshipSummary: string[]
}) {
  const [open, setOpen] = useState(false)
  const [evidence, setEvidence] = useState(item.evidence)
  const [evidenceLoaded, setEvidenceLoaded] = useState(item.evidence.length > 0)
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const [evidenceError, setEvidenceError] = useState('')
  const narrative = evidence.filter((value) => value.relationship !== 'retweet')
  const retweets = evidence.filter((value) => value.relationship === 'retweet')
  return (
    <details
      className="event-evidence"
      onToggle={(event) => {
        const nextOpen = event.currentTarget.open
        setOpen(nextOpen)
        if (!nextOpen || evidenceLoaded || evidenceLoading) return
        setEvidenceLoading(true)
        setEvidenceError('')
        requestEventEvidence(date, item.event_id)
          .then((value) => {
            setEvidence(value)
            setEvidenceLoaded(true)
          })
          .catch(() => setEvidenceError('Couldn’t load the related evidence. Close and retry.'))
          .finally(() => setEvidenceLoading(false))
      }}
    >
      <summary>
        <span>
          View activity · {relationshipSummary.join(' · ') || `${item.member_count - 1} related posts`}
        </span>
        <span className="mono">
          {item.author_count} {item.author_count === 1 ? 'author' : 'authors'}
        </span>
      </summary>
      {open && (
        <div className="event-thread">
          {evidenceLoading && <p className="mono muted">Loading evidence…</p>}
          {evidenceError && <p className="error-note">{evidenceError}</p>}
          {narrative.map((evidence) => (
            <RelationshipPost key={evidence.post_id} item={evidence} />
          ))}
          <RetweetTrace items={retweets} />
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
  rankOpen,
  onToggleRank,
  onCloseRank,
  focused,
}: {
  item: FeedEvent
  rank: number
  total: number
  date: string
  rankOpen: boolean
  onToggleRank: () => void
  onCloseRank: () => void
  focused: boolean
}) {
  const root = item.root
  const counts = item.relationship_counts
  const relationshipSummary = [
    counts.author_updates
      ? `${counts.author_updates} author ${counts.author_updates === 1 ? 'update' : 'updates'}`
      : null,
    counts.replies
      ? `${counts.replies} ${counts.replies === 1 ? 'reply' : 'replies'}`
      : null,
    counts.quotes ? `${counts.quotes} ${counts.quotes === 1 ? 'quote' : 'quotes'}` : null,
    counts.retweets
      ? `${counts.retweets} ${counts.retweets === 1 ? 'retweet' : 'retweets'}`
      : null,
    counts.related
      ? `${counts.related} linked ${counts.related === 1 ? 'post' : 'posts'}`
      : null,
  ].filter((part): part is string => part !== null)

  return (
    <article
      className={`feed-row event-row${focused ? ' event-row--focused' : ''}`}
      id={`event-${item.event_id}`}
    >
      <RankDisclosure
        item={item}
        rank={rank}
        total={total}
        date={date}
        open={rankOpen}
        onToggle={onToggleRank}
        onClose={onCloseRank}
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
            {item.is_grouped && (
              <span>{item.member_count - 1} related {item.member_count === 2 ? 'post' : 'posts'}</span>
            )}
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

        {item.is_grouped && (
          <EventEvidenceDetails
            item={item}
            date={date}
            relationshipSummary={relationshipSummary}
          />
        )}

        <RoutingNote item={item} />

        <footer className="feed-footer mono">
          <div className="feed-metrics">
            <Metric label="likes" value={root.metrics.likes} />
            <Metric label="reposts" value={root.metrics.reposts} />
            <Metric label="replies" value={root.metrics.replies} />
            <Metric label="views" value={root.metrics.views} />
          </div>
          <div className="feed-footer-actions">
            <CopyEventId eventId={item.event_id} />
            <a href={root.url} target="_blank" rel="noreferrer">
              Open root post on X ↗
            </a>
          </div>
        </footer>
      </div>
    </article>
  )
}

export default function Feed() {
  const [urlSearchParams, setUrlSearchParams] = useSearchParams()
  const { rememberDate } = useAuditDate()
  const initialSearchParams = useRef(new URLSearchParams(urlSearchParams))
  const initialLinkedDate = useRef(readAuditDate(initialSearchParams.current))
  const rememberDateRef = useRef(rememberDate)
  const setUrlSearchParamsRef = useRef(setUrlSearchParams)
  rememberDateRef.current = rememberDate
  setUrlSearchParamsRef.current = setUrlSearchParams
  const [targetEventId, setTargetEventId] = useState(
    () => urlSearchParams.get('event_id') ?? '',
  )
  const [dates, setDates] = useState<FeedDates | null>(null)
  const [selectedDate, setSelectedDate] = useState(
    () => initialLinkedDate.current,
  )
  const [sort, setSort] = useState<Sort>('rank')
  const [routingFilter, setRoutingFilter] = useState<RoutingFilter>(() =>
    initialFeedRoutingFilter(initialSearchParams.current),
  )
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [data, setData] = useState<EventResponse | null>(null)
  const [items, setItems] = useState<FeedEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [openRankEventId, setOpenRankEventId] = useState<string | null>(null)
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
    getCachedJSON<FeedDates>('/api/events/dates')
      .then((value) => {
        setDates(value)
        if (value.available && value.latest_complete_date) {
          const feedDates = value.dates ?? []
          const nextDate = initialLinkedDate.current || value.latest_complete_date
          const selectedIndex = feedDates.findIndex((date) => date.day === nextDate)
          setDateWindowEnd(
            getDateWindowEndForSelection(feedDates.length, selectedIndex),
          )
          setSelectedDate(nextDate)
          rememberDateRef.current(nextDate)
          setUrlSearchParamsRef.current(
            setAuditDateParam(initialSearchParams.current, nextDate),
            { replace: true },
          )
        }
      })
      .catch(() => setError('Couldn’t load available Feed dates. Reload to try again.'))
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
      routingFilter,
      query: debouncedQuery,
      eventId: targetEventId,
      offset: 0,
    }
    const viewKey = eventPageKey(request)
    activeViewKeyRef.current = viewKey
    setOpenRankEventId(null)
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
  }, [selectedDate, sort, routingFilter, debouncedQuery, targetEventId])

  useEffect(() => {
    if (!targetEventId || !items.some((item) => item.event_id === targetEventId)) return
    document.getElementById(`event-${targetEventId}`)?.scrollIntoView({ block: 'start' })
  }, [items, targetEventId])

  const selectDate = (day: string) => {
    setTargetEventId('')
    setSelectedDate(day)
    rememberDate(day)
    setUrlSearchParams(
      setAuditDateParam(urlSearchParams, day, ['event_id']),
      { replace: true },
    )
  }

  const clearTargetEvent = () => {
    if (!targetEventId) return
    setTargetEventId('')
    const nextParams = new URLSearchParams(urlSearchParams)
    nextParams.delete('event_id')
    setUrlSearchParams(nextParams, { replace: true })
  }

  const hasSearch = debouncedQuery.trim().length > 0
  const selectedDateIsAvailable = availableDates.some(
    (value) => value.day === selectedDate,
  )
  const selectedDateLabel = (() => {
    const parsed = new Date(`${selectedDate}T12:00:00Z`)
    return Number.isNaN(parsed.getTime()) ? selectedDate : shortDate.format(parsed)
  })()

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
    if (nextDate) selectDate(nextDate.day)
  }

  const loadMore = () => {
    if (!data?.total || items.length >= data.total) return
    const viewKey = eventPageKey({
      date: selectedDate,
      sort,
      routingFilter,
      query: debouncedQuery,
      offset: 0,
    })
    if (activeViewKeyRef.current !== viewKey) return
    setLoading(true)
    setError('')
    requestEventPage({
      date: selectedDate,
      sort,
      routingFilter,
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
      <section className="evidence-view feed-page" aria-labelledby="feed-title">
        <h2 className="evidence-view-title" id="feed-title">
          What is the network paying attention to?
        </h2>
        <p className="page-sub mono">{dates.reason}</p>
      </section>
    )
  }

  return (
    <section className="evidence-view feed-page" aria-labelledby="feed-title">
      <header className="page-head">
        <h2 className="evidence-view-title" id="feed-title">
          What is the network paying attention to?
        </h2>
        <p className="evidence-view-sub">
          Complete Events ordered first by distinct trusted Registry entities
          that quoted or reposted any Event member. Mean voter position,
          source-author position, and maximum same-day one-post public
          interactions break ties in that order.
        </p>
        <p className="page-method-line mono">
          <a href="/system/architecture#ranking-methods">How ranking works ↗</a>
        </p>
      </header>

      <section className="feed-calendar" aria-label="Available complete UTC days">
        <DateNavigator
          dates={visibleDates}
          selectedDate={selectedDate}
          onSelectDate={selectDate}
          canShowOlderDates={canShowOlderDates}
          canShowNewerDates={canShowNewerDates}
          onShowOlderDates={() => moveDateWindow('older')}
          onShowNewerDates={() => moveDateWindow('newer')}
          ariaLabel="Feed date"
          itemLabel="Events"
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
            label="STATUS"
            value={routingFilter}
            onChange={(value) => {
              clearTargetEvent()
              setRoutingFilter(value)
            }}
            options={[
              { value: 'all', label: 'All', description: 'All Events', count: data?.routing_counts?.all },
              { value: 'relevant', label: 'Relevant', description: 'AI Engineering or Investment', count: data?.routing_counts?.relevant },
              { value: 'not_relevant', label: 'Not relevant', description: 'Evaluated, but relevant to neither audience', count: data?.routing_counts?.not_relevant },
              { value: 'not_evaluated', label: 'Not evaluated', description: 'Outside the current cohort, stale, or unavailable', count: data?.routing_counts?.not_evaluated },
            ]}
          />
          <FeedMenuSelect
            label="SORT"
            value={sort}
            onChange={(value) => {
              clearTargetEvent()
              setSort(value)
            }}
            options={[
              { value: 'rank', label: 'Rank', description: 'Daily Event rank' },
              { value: 'recent', label: 'Recent', description: 'Most recent' },
              { value: 'engagement', label: 'Engagement', description: 'Public engagement' },
            ]}
          />
        </div>
      </div>

      {hasSearch && (
        <div className="feed-summary mono">
          {(data?.total ?? 0).toLocaleString('en-US')}{' '}
          {routingSummaryLabels[routingFilter]} Events
        </div>
      )}

      {error && data && (
        <p className="error-note feed-error" role="alert">{error}</p>
      )}

      <section className="feed-list" aria-live="polite" aria-busy={loading}>
        {loading && items.length === 0
          ? Array.from({ length: targetEventId ? 1 : 5 }, (_, index) => (
              <div className="feed-skeleton skeleton" key={index} />
            ))
          : items.map((item) => (
              <EventRow
                key={item.event_id}
                item={item}
                rank={item.daily_rank}
                total={data?.daily_rank_total ?? items.length}
                date={selectedDate}
                rankOpen={openRankEventId === item.event_id}
                onToggleRank={() =>
                  setOpenRankEventId((current) =>
                    current === item.event_id ? null : item.event_id,
                  )
                }
                onCloseRank={() => setOpenRankEventId(null)}
                focused={targetEventId === item.event_id}
              />
            ))}
        {!loading && items.length === 0 && (
          <div className="registry-empty">
            {selectedDate && !selectedDateIsAvailable
              ? `No complete Feed view is available for ${selectedDateLabel}. This audit date remains preserved across views.`
              : targetEventId
                ? `This exact Feed Event is not available for ${selectedDateLabel}. Check the date or Event ID.`
              : 'No evidence matches this search. Try another day or clear the search.'}
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
    </section>
  )
}
