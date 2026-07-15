import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  getCachedJSON,
  type EngineeringInsightFields,
  type ExtractedInsightItem,
  type ExtractedInsightsResponse,
  type InsightAudience,
  type InsightDates,
  type InvestmentInsightFields,
} from '../api'
import DateNavigator from '../components/DateNavigator'
import CopyEnvelopeId from '../components/CopyEnvelopeId'
import {
  getDateWindowEndForSelection,
  getDateWindow,
  shiftDateWindow,
  type DateWindowDirection,
} from '../dateWindow'
import { decodeTextEntities } from '../textEntities'
import { useAuditDate } from '../auditDateStore'

const DEFAULT_AUDIENCE: InsightAudience = 'ai_engineering'
const AUDIENCE_ORDER: InsightAudience[] = ['ai_engineering', 'investment']
type DisplayItem = ExtractedInsightItem

const insightDay = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})

const AUDIENCE_COPY: Record<
  InsightAudience,
  {
    label: string
    noun: string
    switchDescription: string
    title: string
    subtitle: string
    dateLabel: string
    itemLabel: string
    emptyTitle: string
  }
> = {
  investment: {
    label: 'Investment thesis',
    noun: 'investment',
    switchDescription: 'Theses, exposures, and watchpoints',
    title: 'Investment intelligence',
    subtitle:
      'Position-relevant frontier AI changes for theses, diligence, exposures, and competitive risk.',
    dateLabel: 'Investment insight date',
    itemLabel: 'investment insights',
    emptyTitle: 'No useful investment insight was extracted today',
  },
  ai_engineering: {
    label: 'AI engineering',
    noun: 'AI engineering',
    switchDescription: 'Experiments, implementation, and reliability',
    title: 'AI engineering brief',
    subtitle:
      'Techniques, models, and tooling changes for experiments, implementation choices, and reliability work.',
    dateLabel: 'AI engineering insight date',
    itemLabel: 'AI engineering insights',
    emptyTitle: 'No useful engineering insight was extracted today',
  },
}

const CLAIM_POSTURE_LABELS: Record<ExtractedInsightItem['claim_posture'], string> = {
  directly_documented: 'Direct documentation',
  first_party_report: 'First-party report',
  third_party_observation: 'Third-party observation',
  opinion_or_forecast: 'Opinion or forecast',
}

function parseAudience(value: string | null): InsightAudience {
  return value === 'ai_engineering' || value === 'investment'
    ? value
    : DEFAULT_AUDIENCE
}

function sourceTypeLabel(sourceType: string) {
  if (sourceType === 'x_post') return 'X post'
  if (sourceType === 'artifact') return 'Primary artifact'
  return sourceType.replaceAll('_', ' ')
}

function displayInsightDay(day: string) {
  const parsed = new Date(`${day}T12:00:00Z`)
  return Number.isNaN(parsed.getTime()) ? day : insightDay.format(parsed)
}

function sourceLabel(item: DisplayItem) {
  const { author, title, source_type: sourceType } = item.citation
  if (author && title) return decodeTextEntities(`${author} · ${title}`)
  return decodeTextEntities(author || title || sourceTypeLabel(sourceType))
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

function AudienceAnalysis({
  audience,
  item,
  accessibleName,
}: {
  audience: InsightAudience
  item: DisplayItem
  accessibleName: string
}) {
  if (audience === 'investment') {
    const fields = item.audience_fields as InvestmentInsightFields
    return (
      <section
        className="insight-analysis"
        aria-label={`Investment analysis for ${accessibleName}`}
      >
        <div className="insight-analysis-primary">
          <h3 className="mono">Why it matters</h3>
          <p>{decodeTextEntities(item.why_it_matters)}</p>
        </div>
        <div className="insight-analysis-grid">
          <div>
            <h3 className="mono">Investment implication</h3>
            <p>{decodeTextEntities(fields.investment_implication)}</p>
          </div>
          <div>
            <h3 className="mono">What to watch</h3>
            <p>{decodeTextEntities(fields.what_to_watch)}</p>
          </div>
        </div>
      </section>
    )
  }

  const fields = item.audience_fields as EngineeringInsightFields
  return (
    <section
      className="insight-analysis"
      aria-label={`AI engineering analysis for ${accessibleName}`}
    >
      <div className="insight-analysis-primary">
        <h3 className="mono">Why it matters</h3>
        <p>{decodeTextEntities(item.why_it_matters)}</p>
      </div>
      <div className="insight-analysis-grid">
        <div>
          <h3 className="mono">Recommended action</h3>
          <p>{decodeTextEntities(fields.engineering_action)}</p>
        </div>
        <div>
          <h3 className="mono">Validation boundary</h3>
          <p>{decodeTextEntities(fields.validation_boundary)}</p>
        </div>
      </div>
    </section>
  )
}

function Citation({ item, accessibleName }: { item: DisplayItem; accessibleName: string }) {
  const envelopeUrl = `/evidence/feed?date=${item.day}&event=${encodeURIComponent(item.event_id)}`
  return (
    <blockquote className="insight-citation" cite={envelopeUrl}>
      <div className="insight-citation-head">
        <span className="mono">Exact source passage</span>
        <span className="insight-citation-actions">
          <CopyEnvelopeId envelopeId={item.event_id} />
          <Link
            to={envelopeUrl}
            aria-label={`Open the exact Feed envelope for ${accessibleName}`}
          >
            Open envelope ↗
          </Link>
        </span>
      </div>
      <p>“{decodeTextEntities(item.citation.quote)}”</p>
    </blockquote>
  )
}

function ItemHeader({ item, accessibleName, titleId }: {
  item: DisplayItem
  accessibleName: string
  titleId: string
}) {
  return (
    <header className="insight-head">
      <h2 id={titleId}>{decodeTextEntities(item.claim)}</h2>
      <div className="insight-provenance mono">
        <a
          href={item.citation.url}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open ${sourceLabel(item)} for ${accessibleName} in a new tab`}
        >
          {sourceLabel(item)}
        </a>
        <span>{sourceTypeLabel(item.citation.source_type)}</span>
        <span>{CLAIM_POSTURE_LABELS[item.claim_posture]}</span>
        <time dateTime={item.day}>
          {insightDay.format(new Date(`${item.day}T00:00:00Z`))}
        </time>
      </div>
    </header>
  )
}

function ExtractedInsightRow({ audience, item }: {
  audience: InsightAudience
  item: ExtractedInsightItem
}) {
  const feedRankLabel = item.feed_rank === null
    ? 'Feed rank unavailable'
    : `Feed rank ${item.feed_rank}`
  const accessibleName = `${feedRankLabel}: ${decodeTextEntities(item.claim)}`
  const titleId = `${audience}-extracted-${item.candidate_id}-title`
  return (
    <article className="insight-row" aria-labelledby={titleId}>
      <div className="insight-rank mono">
        <Link
          className="insight-feed-link"
          to={`/evidence/feed?date=${item.day}&event=${encodeURIComponent(item.event_id)}`}
          aria-label={`Open ${feedRankLabel.toLowerCase()} in its exact Feed envelope`}
          title="Open exact Feed envelope"
        >
          <strong>{item.feed_rank === null ? '—' : `#${item.feed_rank}`}</strong>
          <span>Feed rank ↗</span>
        </Link>
      </div>
      <div className="insight-body">
        <ItemHeader item={item} accessibleName={accessibleName} titleId={titleId} />
        <AudienceAnalysis audience={audience} item={item} accessibleName={accessibleName} />
        <Citation item={item} accessibleName={accessibleName} />
      </div>
    </article>
  )
}

export default function Insights() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { rememberDate } = useAuditDate()
  const audience = parseAudience(searchParams.get('audience'))
  const selectedDate = searchParams.get('date') ?? ''
  const [dates, setDates] = useState<InsightDates | null>(null)
  const [dateWindowEnd, setDateWindowEnd] = useState(0)
  const [dataView, setDataView] = useState<{
    viewKey: string
    payload: ExtractedInsightsResponse
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
  const selectedViewKey = `${audience}:${selectedDate}`
  const currentData = dataView?.viewKey === selectedViewKey && dataView.payload.audience === audience
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
    if (searchParams.get('audience') === audience && !searchParams.has('view')) return
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('audience', audience)
    nextParams.delete('view')
    setSearchParams(nextParams, { replace: true })
  }, [audience, searchParams, setSearchParams])

  useEffect(() => {
    const viewKey = `dates:${audience}`
    let live = true
    activeDatesViewRef.current = viewKey
    activeDataViewRef.current = ''
    setDates(null)
    setDataView(null)
    setDatesError(null)
    setDataError(null)
    getCachedJSON<InsightDates>(`/api/insights/extracted/dates?audience=${audience}`)
      .then((payload) => {
        if (!live || activeDatesViewRef.current !== viewKey) return
        setDates(payload)
        const linkedDate = searchParamsRef.current.get('date') ?? ''
        const nextDate = linkedDate || payload.latest_date || ''
        const selectedIndex = payload.dates.findIndex((value) => value.day === nextDate)
        setDateWindowEnd(
          getDateWindowEndForSelection(payload.dates.length, selectedIndex),
        )
        rememberDate(nextDate)
        const nextParams = new URLSearchParams(searchParamsRef.current)
        nextParams.set('audience', audience)
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
    const viewKey = `${audience}:${selectedDate}`
    let live = true
    activeDataViewRef.current = viewKey
    setDataView(null)
    setDataError(null)
    getCachedJSON<ExtractedInsightsResponse>(
      `/api/insights/extracted?audience=${audience}&date=${selectedDate}`,
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
  }, [audience, copy.noun, currentDates, dataRetryKey, selectedDate])

  const setView = (nextAudience: InsightAudience, nextDate: string) => {
    rememberDate(nextDate)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('audience', nextAudience)
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
            <span>{run.extracted_count.toLocaleString('en-US')} useful</span>
            <span>{run.complete_count.toLocaleString('en-US')} classified</span>
            <span>{run.candidate_count.toLocaleString('en-US')} Feed envelopes</span>
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
        <InsightState title={copy.emptyTitle} detail={currentData.reason || 'No useful item cleared this view.'} />
      )}

      {currentData?.available && items.length > 0 && (
        <section className="insight-list" aria-label={`${copy.label} insights`}>
          {items.map((item) => (
            <ExtractedInsightRow audience={audience} item={item} key={item.candidate_id} />
          ))}
        </section>
      )}
      {currentData?.available && items.length === 0 && (
        <InsightState title={copy.emptyTitle} detail="No citation-bound insight is available for this day." />
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
