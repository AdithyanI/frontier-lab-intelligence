import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  getCachedJSON,
  type InsightAudience,
  type InsightDates,
  type InsightItem,
  type InsightStatus,
  type InsightsResponse,
} from '../api'
import CopyEnvelopeId from '../components/CopyEnvelopeId'
import DateNavigator from '../components/DateNavigator'
import {
  getDateWindowEndForSelection,
  getDateWindow,
  shiftDateWindow,
  type DateWindowDirection,
} from '../dateWindow'
import { decodeTextEntities } from '../textEntities'
import { useAuditDate } from '../auditDateStore'

const DEFAULT_AUDIENCE: InsightAudience = 'ai_engineering'
const DEFAULT_STATUS: InsightStatus = 'kept'
const AUDIENCE_ORDER: InsightAudience[] = ['ai_engineering', 'investment']
const STATUS_ORDER: InsightStatus[] = ['kept', 'suppressed', 'all']

const insightDay = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})

const AUDIENCE_COPY = {
  investment: {
    label: 'Investment thesis',
    noun: 'investment',
    switchDescription: 'Theses, exposures, and watchpoints',
    title: 'Investment intelligence',
    subtitle:
      'Position-relevant frontier AI changes for theses, diligence, exposures, and competitive risk.',
    dateLabel: 'Investment insight date',
    itemLabel: 'kept investment insights',
    emptyTitle: 'No useful investment insight was kept today',
  },
  ai_engineering: {
    label: 'AI engineering',
    noun: 'AI engineering',
    switchDescription: 'Experiments, implementation, and reliability',
    title: 'AI engineering brief',
    subtitle:
      'Techniques, models, and tooling changes for experiments, implementation choices, and reliability work.',
    dateLabel: 'AI engineering insight date',
    itemLabel: 'kept AI engineering insights',
    emptyTitle: 'No useful engineering insight was kept today',
  },
} satisfies Record<InsightAudience, {
  label: string
  noun: string
  switchDescription: string
  title: string
  subtitle: string
  dateLabel: string
  itemLabel: string
  emptyTitle: string
}>

const STATUS_COPY: Record<InsightStatus, { label: string; description: string }> = {
  kept: { label: 'Kept', description: 'Published audience Insights' },
  suppressed: { label: 'Suppressed', description: 'Rejected at the final editorial gate' },
  all: { label: 'All', description: 'Every completed editorial decision' },
}

function parseAudience(value: string | null): InsightAudience {
  return value === 'ai_engineering' || value === 'investment'
    ? value
    : DEFAULT_AUDIENCE
}

function parseStatus(value: string | null): InsightStatus {
  return value === 'kept' || value === 'suppressed' || value === 'all'
    ? value
    : DEFAULT_STATUS
}

function displayInsightDay(day: string) {
  const parsed = new Date(`${day}T12:00:00Z`)
  return Number.isNaN(parsed.getTime()) ? day : insightDay.format(parsed)
}

function InsightState({
  title,
  detail,
  kind = 'empty',
  onRetry,
  retryLabel,
}: {
  title: string
  detail: string
  kind?: 'empty' | 'error'
  onRetry?: () => void
  retryLabel?: string
}) {
  return (
    <section
      className={`insight-state insight-state--${kind}`}
      role={kind === 'error' ? 'alert' : 'status'}
    >
      <h2>{title}</h2>
      <p>{detail}</p>
      {onRetry && (
        <button
          className="insight-state-action"
          type="button"
          onClick={onRetry}
          aria-label={retryLabel}
        >
          Try again
        </button>
      )}
    </section>
  )
}

function InsightStatusMenu({
  value,
  counts,
  onChange,
}: {
  value: InsightStatus
  counts?: Record<InsightStatus, number>
  onChange: (value: InsightStatus) => void
}) {
  const detailsRef = useRef<HTMLDetailsElement>(null)
  const selected = STATUS_COPY[value]

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
      <summary aria-label={`STATUS: ${selected.description}`}>
        <span className="feed-menu-label mono">STATUS</span>
        <span className="feed-menu-value">{selected.label}</span>
        {counts && <span className="feed-menu-count mono">{counts[value]}</span>}
        <span className="feed-menu-caret" aria-hidden="true" />
      </summary>
      <div className="feed-menu-panel" role="menu" aria-label="Insight status">
        {STATUS_ORDER.map((status) => (
          <button
            type="button"
            className={status === value ? 'is-active' : ''}
            role="menuitemradio"
            aria-checked={status === value}
            title={STATUS_COPY[status].description}
            onClick={() => {
              onChange(status)
              detailsRef.current?.removeAttribute('open')
            }}
            key={status}
          >
            <span>{STATUS_COPY[status].label}</span>
            {counts && (
              <span className="feed-menu-option-count mono">{counts[status]}</span>
            )}
          </button>
        ))}
      </div>
    </details>
  )
}

function InsightRow({ item }: { item: InsightItem }) {
  const isKept = item.decision === 'surface'
  const feedRankLabel = `Feed rank ${item.feed_rank}`
  const title = item.title
  const accessibleName = `${feedRankLabel}: ${decodeTextEntities(title)}`
  const titleId = `${item.audience}-${item.candidate_id}-title`
  const envelopeUrl = `/evidence/feed?date=${item.day}&event=${encodeURIComponent(item.event_id)}`

  return (
    <article
      className={`insight-row insight-row--${isKept ? 'kept' : 'suppressed'}`}
      aria-labelledby={titleId}
    >
      <div className="insight-rank mono">
        <Link
          className="insight-feed-link"
          to={envelopeUrl}
          aria-label={`Open ${feedRankLabel.toLowerCase()} in its exact Feed envelope`}
          title="Open exact Feed envelope"
        >
          <strong>#{item.feed_rank}</strong>
          <span>Feed rank ↗</span>
        </Link>
      </div>
      <div className="insight-body">
        <header className="insight-head">
          <div className={`insight-decision-mark insight-decision-mark--${isKept ? 'kept' : 'suppressed'} mono`}>
            {isKept ? 'Kept' : 'Suppressed'}
          </div>
          <h2 id={titleId}>{decodeTextEntities(title)}</h2>
          <div className="insight-provenance mono">
            <time dateTime={item.day}>{displayInsightDay(item.day)}</time>
            <span>{item.model}</span>
            <span>{item.prompt_version}</span>
            <CopyEnvelopeId envelopeId={item.event_id} />
            <Link
              to={envelopeUrl}
              aria-label={`Open the exact Feed envelope for ${accessibleName}`}
            >
              Open envelope ↗
            </Link>
            {item.root_source_url && (
              <a
                href={item.root_source_url}
                target="_blank"
                rel="noreferrer"
                aria-label={`Open the original source post for ${accessibleName}`}
              >
                Open source ↗
              </a>
            )}
            {item.artifacts.map((artifact, index) => (
              <a
                href={artifact.url}
                target="_blank"
                rel="noreferrer"
                title={decodeTextEntities(artifact.title)}
                aria-label={`Read artifact: ${decodeTextEntities(artifact.title)}`}
                key={artifact.url}
              >
                {item.artifacts.length === 1 ? 'Read artifact ↗' : `Read artifact ${index + 1} ↗`}
              </a>
            ))}
          </div>
        </header>

        {isKept && item.summary && (
          <section className="insight-summary" aria-label={`Summary for ${accessibleName}`}>
            <h3 className="mono">Summary</h3>
            <p>{decodeTextEntities(item.summary)}</p>
          </section>
        )}

        <section
          className={`insight-decision-reason insight-decision-reason--${isKept ? 'kept' : 'suppressed'}`}
          aria-label={`${isKept ? 'Why kept' : 'Why suppressed'}: ${accessibleName}`}
        >
          <h3 className="mono">{isKept ? 'Why kept' : 'Why suppressed'}</h3>
          <p>{decodeTextEntities(item.decision_reason)}</p>
        </section>

        {isKept && item.next_step && (
          <section className="insight-analysis" aria-label={`Next step for ${accessibleName}`}>
            <h3 className="mono">Next step</h3>
            <p>{decodeTextEntities(item.next_step)}</p>
          </section>
        )}
      </div>
    </article>
  )
}

export default function Insights() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { rememberDate } = useAuditDate()
  const audience = parseAudience(searchParams.get('audience'))
  const status = parseStatus(searchParams.get('status'))
  const selectedDate = searchParams.get('date') ?? ''
  const [dates, setDates] = useState<InsightDates | null>(null)
  const [dateWindowEnd, setDateWindowEnd] = useState(0)
  const [dataView, setDataView] = useState<{
    viewKey: string
    payload: InsightsResponse
  } | null>(null)
  const [datesError, setDatesError] = useState<string | null>(null)
  const [dataError, setDataError] = useState<string | null>(null)
  const [datesRetryKey, setDatesRetryKey] = useState(0)
  const [dataRetryKey, setDataRetryKey] = useState(0)
  const activeDatesViewRef = useRef('')
  const activeDataViewRef = useRef('')
  const searchParamsRef = useRef(searchParams)
  searchParamsRef.current = searchParams

  const currentDates = dates?.audience === audience ? dates : null
  const selectedViewKey = `${audience}:${selectedDate}:${status}`
  const currentData = dataView?.viewKey === selectedViewKey &&
      dataView.payload.audience === audience && dataView.payload.status === status
    ? dataView.payload
    : null
  const availableDates = useMemo(() => currentDates?.dates ?? [], [currentDates])
  const dateWindow = useMemo(
    () => getDateWindow(dateWindowEnd, availableDates.length),
    [dateWindowEnd, availableDates.length],
  )
  const visibleDates = useMemo(
    () => availableDates.slice(dateWindow.start, dateWindow.end),
    [availableDates, dateWindow],
  )
  const copy = AUDIENCE_COPY[audience]

  useEffect(() => {
    if (
      searchParams.get('audience') === audience &&
      searchParams.get('status') === status &&
      !searchParams.has('view')
    ) return
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('audience', audience)
    nextParams.set('status', status)
    nextParams.delete('view')
    setSearchParams(nextParams, { replace: true })
  }, [audience, searchParams, setSearchParams, status])

  useEffect(() => {
    const viewKey = `dates:${audience}`
    let live = true
    activeDatesViewRef.current = viewKey
    activeDataViewRef.current = ''
    setDates(null)
    setDataView(null)
    setDatesError(null)
    setDataError(null)
    getCachedJSON<InsightDates>(`/api/insights/dates?audience=${audience}`)
      .then((payload) => {
        if (!live || activeDatesViewRef.current !== viewKey) return
        setDates(payload)
        const linkedDate = searchParamsRef.current.get('date') ?? ''
        const nextDate = linkedDate || payload.latest_date || ''
        const selectedIndex = payload.dates.findIndex((value) => value.day === nextDate)
        setDateWindowEnd(getDateWindowEndForSelection(payload.dates.length, selectedIndex))
        rememberDate(nextDate)
        const nextParams = new URLSearchParams(searchParamsRef.current)
        nextParams.set('audience', audience)
        nextParams.set('status', parseStatus(nextParams.get('status')))
        nextParams.delete('view')
        if (nextDate) nextParams.set('date', nextDate)
        else nextParams.delete('date')
        setSearchParams(nextParams, { replace: true })
      })
      .catch(() => {
        if (!live || activeDatesViewRef.current !== viewKey) return
        setDatesError(`Couldn’t load ${copy.noun} insight dates. Try the request again.`)
      })
    return () => { live = false }
  }, [audience, copy.noun, datesRetryKey, rememberDate, setSearchParams])

  useEffect(() => {
    if (
      !currentDates?.available ||
      !selectedDate ||
      !currentDates.dates.some((value) => value.day === selectedDate)
    ) {
      activeDataViewRef.current = ''
      setDataView(null)
      return
    }
    const viewKey = `${audience}:${selectedDate}:${status}`
    let live = true
    activeDataViewRef.current = viewKey
    setDataView(null)
    setDataError(null)
    getCachedJSON<InsightsResponse>(
      `/api/insights?audience=${audience}&date=${selectedDate}&status=${status}`,
    )
      .then((payload) => {
        if (!live || activeDataViewRef.current !== viewKey) return
        setDataView({ viewKey, payload })
      })
      .catch(() => {
        if (!live || activeDataViewRef.current !== viewKey) return
        setDataError(`Couldn’t load the ${copy.noun} brief for this date. Try the request again.`)
      })
    return () => { live = false }
  }, [audience, copy.noun, currentDates, dataRetryKey, selectedDate, status])

  const setView = (
    nextAudience: InsightAudience,
    nextDate: string,
    nextStatus: InsightStatus = status,
  ) => {
    rememberDate(nextDate)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('audience', nextAudience)
    nextParams.set('status', nextStatus)
    nextParams.delete('view')
    if (nextDate) nextParams.set('date', nextDate)
    else nextParams.delete('date')
    setSearchParams(nextParams, { replace: true })
  }

  const moveDateWindow = (direction: DateWindowDirection) => {
    const selectedIndex = availableDates.findIndex((value) => value.day === selectedDate)
    const nextWindow = shiftDateWindow(
      dateWindow.end,
      availableDates.length,
      selectedIndex,
      direction,
    )
    if (nextWindow.end === dateWindow.end) return
    setDateWindowEnd(nextWindow.end)
    const nextDate = availableDates[nextWindow.selectedIndex]
    if (nextDate) setView(audience, nextDate.day)
  }

  const items = currentData?.items ?? []
  const run = currentData?.run
  const datesLoading = currentDates === null && datesError === null
  const dataLoading = currentDates?.available === true &&
    currentDates.dates.some((value) => value.day === selectedDate) &&
    currentData === null && dataError === null
  const selectedDateUnavailable = currentDates?.available === true &&
    selectedDate !== '' &&
    !currentDates.dates.some((value) => value.day === selectedDate)

  return (
    <div className="page insight-page">
      <header className="page-head insight-page-head">
        <h1 className="page-title">{copy.title}</h1>
        <p className="page-sub">{copy.subtitle}</p>
        {run && (
          <p className="page-method-line mono">
            <span>{run.surfaced_count.toLocaleString('en-US')} kept</span>
            <span>{run.suppressed_count.toLocaleString('en-US')} suppressed</span>
            <span>{run.complete_count.toLocaleString('en-US')} classified</span>
            <span>{run.model}</span>
          </p>
        )}
      </header>

      <div className="insight-audience-switch" role="group" aria-label="Insight audience">
        {AUDIENCE_ORDER.map((value) => (
          <button
            type="button"
            className={value === audience ? 'is-active' : ''}
            aria-pressed={value === audience}
            onClick={() => setView(value, selectedDate)}
            key={value}
          >
            <span>{AUDIENCE_COPY[value].label}</span>
            <small>{AUDIENCE_COPY[value].switchDescription}</small>
          </button>
        ))}
      </div>

      {!datesError && (!currentDates || currentDates.available) && (
        <section className="feed-calendar insight-calendar" aria-label={`Available ${copy.itemLabel} dates`}>
          <DateNavigator
            dates={visibleDates}
            selectedDate={selectedDate}
            onSelectDate={(day) => setView(audience, day)}
            canShowOlderDates={dateWindow.start > 0}
            canShowNewerDates={dateWindow.end < availableDates.length}
            onShowOlderDates={() => moveDateWindow('older')}
            onShowNewerDates={() => moveDateWindow('newer')}
            ariaLabel={copy.dateLabel}
            itemLabel={copy.itemLabel}
            loading={datesLoading}
          />
        </section>
      )}

      {currentDates?.available && (
        <div className="insight-tools">
          <p className="mono">Day pills count kept Insights. Audit every decision here.</p>
          <div className="feed-controls">
            <InsightStatusMenu
              value={status}
              counts={run?.counts}
              onChange={(nextStatus) => setView(audience, selectedDate, nextStatus)}
            />
          </div>
        </div>
      )}

      {datesError && (
        <InsightState
          title="Insight dates are unavailable"
          detail={datesError}
          kind="error"
          onRetry={() => { setDatesError(null); setDatesRetryKey((value) => value + 1) }}
          retryLabel={`Retry loading ${copy.itemLabel} dates`}
        />
      )}
      {dataError && (
        <InsightState
          title="This brief did not load"
          detail={dataError}
          kind="error"
          onRetry={() => { setDataError(null); setDataRetryKey((value) => value + 1) }}
          retryLabel={`Retry loading the ${copy.noun} brief for this date`}
        />
      )}
      {currentDates && !currentDates.available && !datesError && (
        <InsightState
          title={`No ${copy.itemLabel} are available yet`}
          detail={currentDates.reason || 'No classified audience insight days exist yet.'}
        />
      )}
      {selectedDateUnavailable && !datesError && (
        <InsightState
          title={copy.emptyTitle}
          detail={`No ${copy.itemLabel} are available for ${displayInsightDay(selectedDate)}.`}
        />
      )}
      {currentData && !currentData.available && !dataError && (
        <InsightState title={copy.emptyTitle} detail={currentData.reason || 'No editorial decision is available.'} />
      )}

      {currentData?.available && items.length > 0 && (
        <section className="insight-list" aria-label={`${copy.label} ${STATUS_COPY[status].label.toLowerCase()} insights`}>
          {items.map((item) => <InsightRow item={item} key={item.candidate_id} />)}
        </section>
      )}
      {currentData?.available && items.length === 0 && (
        <InsightState
          title={status === 'kept' ? copy.emptyTitle : `No ${STATUS_COPY[status].label.toLowerCase()} decisions today`}
          detail={currentData.reason || 'No completed decision matches this status.'}
        />
      )}
      {dataLoading && (
        <div className="insight-loading" aria-label={`Loading ${copy.itemLabel}`} aria-busy="true">
          <div className="skeleton" />
          <div className="skeleton" />
          <div className="skeleton" />
        </div>
      )}
    </div>
  )
}
