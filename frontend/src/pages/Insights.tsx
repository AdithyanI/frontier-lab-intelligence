import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  getCachedJSON,
  type EngineeringActionType,
  type EngineeringInsightFields,
  type ExtractedInsightItem,
  type ExtractedInsightsResponse,
  type InsightAudience,
  type InsightDates,
  type InsightItem,
  type InsightsResponse,
  type InvestmentInsightFields,
} from '../api'
import DateNavigator from '../components/DateNavigator'
import {
  getDateWindow,
  shiftDateWindow,
  type DateWindowDirection,
} from '../dateWindow'
import { decodeTextEntities } from '../textEntities'

const DEFAULT_AUDIENCE: InsightAudience = 'ai_engineering'
const AUDIENCE_ORDER: InsightAudience[] = ['ai_engineering', 'investment']
type InsightView = 'extracted' | 'reviewed'
const DEFAULT_VIEW: InsightView = 'extracted'
type DisplayItem = InsightItem | ExtractedInsightItem
type InsightPayload = InsightsResponse | ExtractedInsightsResponse

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

const DECISION_VALUE_LABELS: Record<string, string> = {
  thesis_or_model: 'Thesis or model',
  watchlist_or_exposure: 'Watchlist or exposure',
  diligence_question: 'Diligence question',
  execution_or_competitive_risk: 'Execution or competitive risk',
  experiment_or_benchmark: 'Experiment or benchmark',
  implementation_choice: 'Implementation choice',
  regression_or_reliability: 'Regression or reliability',
  research_or_tooling_watch: 'Research or tooling watch',
}

const ACTION_TYPE_LABELS: Record<EngineeringActionType, string> = {
  investigate: 'Investigate',
  reproduce: 'Reproduce',
  benchmark: 'Benchmark',
  prototype: 'Prototype',
  regression_test: 'Regression test',
  monitor: 'Monitor',
}

const CLAIM_POSTURE_LABELS: Record<InsightItem['claim_posture'], string> = {
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

function parseView(value: string | null): InsightView {
  return value === 'reviewed' ? 'reviewed' : DEFAULT_VIEW
}

function sourceTypeLabel(sourceType: string) {
  if (sourceType === 'x_post') return 'X post'
  if (sourceType === 'artifact') return 'Primary artifact'
  return sourceType.replaceAll('_', ' ')
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
        <Link
          to={envelopeUrl}
          aria-label={`Open the exact Feed envelope for ${accessibleName}`}
        >
          Open envelope ↗
        </Link>
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
  const accessibleName = `Feed rank ${item.feed_rank}: ${decodeTextEntities(item.claim)}`
  const titleId = `${audience}-extracted-${item.feed_rank}-title`
  return (
    <article className="insight-row" aria-labelledby={titleId}>
      <div className="insight-rank mono">
        <Link
          className="insight-feed-link"
          to={`/evidence/feed?date=${item.day}&event=${encodeURIComponent(item.event_id)}`}
          aria-label={`Open Feed rank ${item.feed_rank} in its exact Feed envelope`}
          title="Open exact Feed envelope"
        >
          <strong>#{item.feed_rank}</strong>
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

function InsightRow({ audience, item }: {
  audience: InsightAudience
  item: InsightItem
}) {
  const fields = audience === 'ai_engineering'
    ? (item.audience_fields as EngineeringInsightFields)
    : null
  const accessibleName = `editorial rank ${item.editorial_rank}: ${decodeTextEntities(item.claim)}`
  const titleId = `${audience}-insight-${item.editorial_rank}-title`
  return (
    <article className="insight-row" aria-labelledby={titleId}>
      <div
        className="insight-rank mono"
        aria-label={`Editorial rank ${item.editorial_rank}; Feed rank ${item.feed_rank}`}
      >
        <strong>#{item.editorial_rank}</strong>
        <span>Editorial rank</span>
        <Link
          className="insight-feed-rank insight-feed-rank--link"
          to={`/evidence/feed?date=${item.day}&event=${encodeURIComponent(item.event_id)}`}
          aria-label={`Open Feed rank ${item.feed_rank} in its exact Feed envelope`}
          title="Open exact Feed envelope"
        >
          Feed #{item.feed_rank} ↗
        </Link>
      </div>
      <div className="insight-body">
        <ItemHeader item={item} accessibleName={accessibleName} titleId={titleId} />
        <div className="insight-decision-line">
          <span className="mono">Decision value</span>
          <strong>{DECISION_VALUE_LABELS[item.decision_value] || item.decision_value}</strong>
          {fields && (
            <>
              <span className="mono">Action</span>
              <strong>{ACTION_TYPE_LABELS[fields.action_type]}</strong>
            </>
          )}
        </div>
        <AudienceAnalysis audience={audience} item={item} accessibleName={accessibleName} />
        <Citation item={item} accessibleName={accessibleName} />
      </div>
    </article>
  )
}

export default function Insights() {
  const [searchParams, setSearchParams] = useSearchParams()
  const audience = parseAudience(searchParams.get('audience'))
  const insightView = parseView(searchParams.get('view'))
  const selectedDate = searchParams.get('date') ?? ''
  const [dates, setDates] = useState<InsightDates | null>(null)
  const [dateWindowEnd, setDateWindowEnd] = useState(0)
  const [dataView, setDataView] = useState<{ viewKey: string; payload: InsightPayload } | null>(null)
  const [datesError, setDatesError] = useState<string | null>(null)
  const [dataError, setDataError] = useState<string | null>(null)
  const [datesRetryKey, setDatesRetryKey] = useState(0)
  const [dataRetryKey, setDataRetryKey] = useState(0)
  const activeDatesViewRef = useRef('')
  const activeDataViewRef = useRef('')
  const searchParamsRef = useRef(searchParams)
  searchParamsRef.current = searchParams

  const currentDates = dates?.audience === audience ? dates : null
  const selectedViewKey = `${insightView}:${audience}:${selectedDate}`
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
    if (
      searchParams.get('audience') === audience &&
      searchParams.get('view') === insightView
    ) return
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('audience', audience)
    nextParams.set('view', insightView)
    setSearchParams(nextParams, { replace: true })
  }, [audience, insightView, searchParams, setSearchParams])

  useEffect(() => {
    const viewKey = `dates:${insightView}:${audience}`
    let live = true
    activeDatesViewRef.current = viewKey
    activeDataViewRef.current = ''
    setDates(null)
    setDataView(null)
    setDatesError(null)
    setDataError(null)
    const endpoint = insightView === 'extracted'
      ? '/api/insights/extracted/dates'
      : '/api/insights/dates'

    getCachedJSON<InsightDates>(`${endpoint}?audience=${audience}`)
      .then((payload) => {
        if (!live || activeDatesViewRef.current !== viewKey) return
        setDates(payload)
        setDateWindowEnd(payload.dates.length)
        const linkedDate = searchParamsRef.current.get('date') ?? ''
        const nextDate = payload.dates.some((value) => value.day === linkedDate)
          ? linkedDate
          : payload.latest_date ?? ''
        const nextParams = new URLSearchParams(searchParamsRef.current)
        nextParams.set('audience', audience)
        nextParams.set('view', insightView)
        if (nextDate) nextParams.set('date', nextDate)
        else nextParams.delete('date')
        setSearchParams(nextParams, { replace: true })
      })
      .catch(() => {
        if (!live || activeDatesViewRef.current !== viewKey) return
        setDatesError(`Couldn’t load ${copy.noun} insight dates. Try the request again.`)
      })
    return () => { live = false }
  }, [audience, copy.noun, datesRetryKey, insightView, setSearchParams])

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
    const viewKey = `${insightView}:${audience}:${selectedDate}`
    let live = true
    activeDataViewRef.current = viewKey
    setDataView(null)
    setDataError(null)
    const endpoint = insightView === 'extracted' ? '/api/insights/extracted' : '/api/insights'
    getCachedJSON<InsightPayload>(`${endpoint}?audience=${audience}&date=${selectedDate}`)
      .then((payload) => {
        if (!live || activeDataViewRef.current !== viewKey) return
        setDataView({ viewKey, payload })
      })
      .catch(() => {
        if (!live || activeDataViewRef.current !== viewKey) return
        setDataError(`Couldn’t load the ${copy.noun} brief for this date. Try the request again.`)
      })
    return () => { live = false }
  }, [audience, copy.noun, currentDates, dataRetryKey, insightView, selectedDate])

  const setView = (
    nextAudience: InsightAudience,
    nextDate: string,
    nextInsightView: InsightView = insightView,
  ) => {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('audience', nextAudience)
    nextParams.set('view', nextInsightView)
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

  return (
    <div className="page insight-page">
      <header className="page-head insight-page-head">
        <h1 className="page-title">{copy.title}</h1>
        <p className="page-sub">{copy.subtitle}</p>
        {run && insightView === 'extracted' && 'complete_count' in run && (
          <p className="page-method-line mono">
            <span>{run.extracted_count.toLocaleString('en-US')} useful</span>
            <span>{run.complete_count.toLocaleString('en-US')} classified</span>
            <span>{run.candidate_count.toLocaleString('en-US')} Feed envelopes</span>
          </p>
        )}
        {run && insightView === 'reviewed' && 'selected_count' in run && (
          <p className="page-method-line mono">
            <span>{run.selected_count.toLocaleString('en-US')} selected</span>
            <span>{run.extracted_count.toLocaleString('en-US')} citation-bound</span>
            <span>{run.candidate_count.toLocaleString('en-US')} screened candidates</span>
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

      <div className="insight-view-switch" role="group" aria-label="Insight processing view">
        <button
          type="button"
          className={insightView === 'extracted' ? 'is-active' : ''}
          aria-pressed={insightView === 'extracted'}
          onClick={() => setView(audience, selectedDate, 'extracted')}
        >
          <span>Feed-ranked</span>
          <small>Useful extractions before editorial review</small>
        </button>
        <button
          type="button"
          className={insightView === 'reviewed' ? 'is-active' : ''}
          aria-pressed={insightView === 'reviewed'}
          onClick={() => setView(audience, selectedDate, 'reviewed')}
        >
          <span>Reviewed brief</span>
          <small>Selected and independently audited</small>
        </button>
      </div>
      <p className="insight-view-note mono">
        {insightView === 'extracted'
          ? 'Existing first-stage classifications · ordered by original Feed rank'
          : 'Editorial selection · independent audit · publication reconciliation'}
      </p>

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
      {currentData && !currentData.available && !dataError && (
        <InsightState title={copy.emptyTitle} detail={currentData.reason || 'No useful item cleared this view.'} />
      )}

      {currentData?.available && items.length > 0 && insightView === 'extracted' && (
        <section className="insight-list" aria-label={`${copy.label} insights`}>
          {(items as ExtractedInsightItem[]).map((item) => (
            <ExtractedInsightRow audience={audience} item={item} key={item.candidate_id} />
          ))}
        </section>
      )}
      {currentData?.available && items.length > 0 && insightView === 'reviewed' && (
        <section className="insight-list" aria-label={`${copy.label} insights`}>
          {(items as InsightItem[]).map((item) => (
            <InsightRow audience={audience} item={item} key={item.candidate_id} />
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
