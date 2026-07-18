import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  getCachedJSON,
  type EditorialAnalysis,
  type EditorialInsightItem,
  type EditorialInsightsResponse,
  type EngineeringEditorialAnalysis,
  type InsightAudience,
  type InsightDates,
  type InsightItem,
  type InsightStatus,
  type InsightsResponse,
  type InvestmentEditorialAnalysis,
  type InvestmentImpactDirection,
} from '../../shared/api'
import CopyEventId from '../../shared/components/CopyEventId'
import DateNavigator from '../../shared/components/DateNavigator'
import {
  getDateWindowEndForSelection,
  getDateWindow,
  shiftDateWindow,
  type DateWindowDirection,
} from '../../shared/date/dateWindow'
import { decodeTextEntities } from '../../shared/textEntities'
import { useAuditDate } from '../../shared/date/auditDateStore'

const DEFAULT_AUDIENCE: InsightAudience = 'investment'
const DEFAULT_STATUS: InsightStatus = 'kept'
const AUDIENCE_ORDER: InsightAudience[] = ['investment', 'ai_engineering']

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

const INVESTMENT_IMPACT_COPY = {
  positive: { icon: '↗', label: 'Positive' },
  negative: { icon: '↘', label: 'Negative' },
  mixed: { icon: '↔', label: 'Mixed' },
  uncertain: { icon: '?', label: 'Uncertain' },
} satisfies Record<InvestmentImpactDirection, { icon: string; label: string }>

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

function isEditorialResponse(payload: InsightsResponse): payload is EditorialInsightsResponse {
  return payload.content_kind === 'daily_editorial'
}

function isInvestmentAnalysis(
  analysis: EditorialAnalysis,
): analysis is InvestmentEditorialAnalysis {
  return 'key_uncertainty' in analysis
}

function isEngineeringAnalysis(
  analysis: EditorialAnalysis,
): analysis is EngineeringEditorialAnalysis {
  return 'decision_rule' in analysis
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
            <CopyEventId eventId={item.event_id} />
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
          aria-label={`${isKept ? 'Why it matters' : 'Why suppressed'}: ${accessibleName}`}
        >
          <h3 className="mono">{isKept ? 'Why it matters' : 'Why suppressed'}</h3>
          <p>{decodeTextEntities(item.decision_reason)}</p>
        </section>

        {isKept && item.action && (
          <section className="insight-analysis" aria-label={`${item.action_label} for ${accessibleName}`}>
            <h3 className="mono">{item.action_label}</h3>
            <p>{decodeTextEntities(item.action)}</p>
          </section>
        )}
      </div>
    </article>
  )
}

function EditorialList({ items }: { items: string[] }) {
  return (
    <ul className="editorial-text-list">
      {items.map((item, index) => (
        <li key={`${index}-${item}`}>{decodeTextEntities(item)}</li>
      ))}
    </ul>
  )
}

function InvestmentDecision({
  analysis,
  nextStep,
}: {
  analysis: InvestmentEditorialAnalysis
  nextStep: string
}) {
  const portfolioEntities = analysis.affected_entities.filter(
    (entity) => entity.scope === 'portfolio',
  )
  const outsideEntities = analysis.affected_entities.filter(
    (entity) => entity.scope === 'outside_portfolio',
  )

  const entityList = (
    entities: InvestmentEditorialAnalysis['affected_entities'],
    label: string | null,
  ) => (
    <div className={`editorial-entities${label ? '' : ' editorial-entities--unlabelled'}`}>
      {label && <h4 className="mono">{label}</h4>}
      <ul>
        {entities.map((entity) => {
          const impact = INVESTMENT_IMPACT_COPY[entity.impact]
          return (
            <li key={`${entity.scope}-${entity.name}`}>
              <strong className="editorial-entity-name">
                {decodeTextEntities(entity.name)}
              </strong>
              <span className={`editorial-entity-impact editorial-entity-impact--${entity.impact}`}>
                <span className="editorial-entity-impact-icon" aria-hidden="true">
                  {impact.icon}
                </span>
                <span>{impact.label}</span>
              </span>
              <p>{decodeTextEntities(entity.mechanism)}</p>
            </li>
          )
        })}
      </ul>
    </div>
  )

  const hasBothEntityScopes = portfolioEntities.length > 0 && outsideEntities.length > 0

  return (
    <>
      {analysis.affected_entities.length > 0 && (
        <section className="editorial-section editorial-decision" aria-label="Company read-through">
          <h3>Company read-through</h3>
          {portfolioEntities.length > 0 && entityList(
            portfolioEntities,
            hasBothEntityScopes ? 'Portfolio companies' : null,
          )}
          {outsideEntities.length > 0 && entityList(outsideEntities, 'Outside the disclosed portfolio')}
        </section>
      )}
      <section className="editorial-section editorial-watch" aria-label="What would confirm or challenge this">
        <h3>What would confirm or challenge this</h3>
        <div className="editorial-validation-grid">
          <div>
            <h4 className="mono">Key uncertainty</h4>
            <p>{decodeTextEntities(analysis.key_uncertainty)}</p>
          </div>
          <div>
            <h4 className="mono">Signals</h4>
            <EditorialList items={analysis.watchpoints} />
          </div>
          <div>
            <h4 className="mono">Next diligence step</h4>
            <p>{decodeTextEntities(nextStep)}</p>
          </div>
        </div>
      </section>
    </>
  )
}

function EngineeringDecision({
  analysis,
  nextStep,
}: {
  analysis: EngineeringEditorialAnalysis
  nextStep: string
}) {
  return (
    <section className="editorial-section editorial-decision" aria-label="What to do next">
      <h3>What to do next</h3>
      <div className="editorial-decision-grid">
        <div>
          <h4 className="mono">Next step</h4>
          <p>{decodeTextEntities(nextStep)}</p>
        </div>
        <div>
          <h4 className="mono">Decision rule</h4>
          <p>{decodeTextEntities(analysis.decision_rule)}</p>
        </div>
      </div>
    </section>
  )
}

function EditorialSources({ item }: { item: EditorialInsightItem }) {
  const researchSources = item.citations.filter((citation) => citation.kind !== 'event')
  const titleId = `${item.insight_id}-sources`

  return (
    <section className="editorial-sources" aria-labelledby={titleId}>
      <h3 id={titleId}>Sources</h3>
      <div className="editorial-source-columns">
        <section aria-label="Original feed sources">
          <h4 className="mono">Original feed</h4>
          <ul className="editorial-source-list">
            {item.events.map((event) => {
              const envelopeUrl = `/evidence/feed?date=${item.day}&event=${encodeURIComponent(event.event_id)}`
              return (
                <li key={event.event_id}>
                  <Link className="editorial-source-title" to={envelopeUrl}>
                    Feed #{event.feed_rank} ↗
                  </Link>
                  <p>{decodeTextEntities(event.reason)}</p>
                </li>
              )
            })}
          </ul>
        </section>
        <section aria-label="Artifacts and research context">
          <h4 className="mono">Artifacts &amp; context</h4>
          <ul className="editorial-source-list">
            {researchSources.map((citation) => (
              <li key={citation.citation_id}>
                <a className="editorial-source-title" href={citation.url} target="_blank" rel="noreferrer">
                  {decodeTextEntities(citation.title)} ↗
                </a>
                <p>{decodeTextEntities(citation.supports)}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  )
}

function CopyInsightReference({ item }: { item: EditorialInsightItem }) {
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>('idle')

  const copyReference = async () => {
    const reference = [
      `Insight: ${item.day}`,
      AUDIENCE_COPY[item.audience].label,
      `Brief #${item.rank}`,
      `“${decodeTextEntities(item.title)}”`,
      `ID: ${item.insight_id}`,
    ].join(' · ')

    try {
      await navigator.clipboard.writeText(reference)
      setCopyStatus('copied')
    } catch {
      setCopyStatus('failed')
    }
  }

  return (
    <button
      className="editorial-copy-reference mono"
      type="button"
      onClick={copyReference}
      aria-label={`Copy reference for ${decodeTextEntities(item.title)}`}
    >
      {copyStatus === 'copied'
        ? 'Copied'
        : copyStatus === 'failed'
          ? 'Copy failed'
          : 'Copy reference'}
    </button>
  )
}

function EditorialInsightRow({ item }: { item: EditorialInsightItem }) {
  const titleId = `${item.insight_id}-title`
  const rankExplanationId = `${item.insight_id}-rank-explanation`
  const [rankExplanationOpen, setRankExplanationOpen] = useState(false)
  const investmentAnalysis = isInvestmentAnalysis(item.analysis) ? item.analysis : null
  const engineeringAnalysis = isEngineeringAnalysis(item.analysis) ? item.analysis : null

  return (
    <article className="insight-row editorial-insight-row" aria-labelledby={titleId}>
      <div className="insight-rank editorial-rank mono">
        <button
          type="button"
          aria-controls={rankExplanationId}
          aria-expanded={rankExplanationOpen}
          aria-label={`${rankExplanationOpen ? 'Hide' : 'Explain'} brief rank ${item.rank}`}
          onClick={() => setRankExplanationOpen((open) => !open)}
        >
          <strong>#{item.rank}</strong>
          <span>
            Brief rank
            <i aria-hidden="true">i</i>
          </span>
        </button>
      </div>
      <div className="insight-body editorial-insight-body">
        <header className="insight-head editorial-insight-head">
          <h2 id={titleId}>{decodeTextEntities(item.title)}</h2>
          <CopyInsightReference item={item} />
        </header>

        <div
          className="editorial-rank-explanation"
          id={rankExplanationId}
          role="region"
          aria-label={`Why brief rank ${item.rank}`}
          hidden={!rankExplanationOpen}
        >
          <p>
            <strong>Why #{item.rank}:</strong>{' '}
            {decodeTextEntities(item.rank_rationale)}
          </p>
          <p className="mono">
            Ranked across this audience’s full daily brief by decision consequence,
            evidence strength, time sensitivity, actionability, and novelty. It is not
            Feed rank, confidence, popularity, or similarity.
          </p>
        </div>

        <div className="editorial-opening">
          <section>
            <h3 className="mono">What changed</h3>
            <p>{decodeTextEntities(item.what_changed)}</p>
          </section>
          <section>
            <h3 className="mono">
              {investmentAnalysis ? 'Investment interpretation' : 'Engineering interpretation'}
            </h3>
            <p>{decodeTextEntities(item.interpretation)}</p>
          </section>
        </div>

        {investmentAnalysis && (
          <InvestmentDecision analysis={investmentAnalysis} nextStep={item.next_step} />
        )}
        {engineeringAnalysis && (
          <EngineeringDecision analysis={engineeringAnalysis} nextStep={item.next_step} />
        )}

        <EditorialSources item={item} />
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
  const editorialData = currentData && isEditorialResponse(currentData) ? currentData : null
  const candidateData = currentData && !isEditorialResponse(currentData) ? currentData : null
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
        <InsightState title={copy.emptyTitle} detail={currentData.reason || 'No editorial decision is available.'} />
      )}

      {editorialData?.available && editorialData.items.length > 0 && (
        <>
          {audience === 'investment' && editorialData.portfolio_reference && (
            <p className="editorial-portfolio-note">
              Portfolio impact uses BIT Global Technology Leaders’ complete audited 2025
              disclosure. “Outside the disclosed portfolio” is analyst mapping, not a known
              BIT holding or recommendation.{' '}
              <a href={editorialData.portfolio_reference.source_url} target="_blank" rel="noreferrer">
                Portfolio source ↗
              </a>
            </p>
          )}
          <section className="insight-list" aria-label={`${copy.label} ${STATUS_COPY[status].label.toLowerCase()} insights`}>
            {editorialData.items.map((item) => (
              <EditorialInsightRow item={item} key={item.insight_id} />
            ))}
          </section>
        </>
      )}
      {candidateData?.available && candidateData.items.length > 0 && (
        <section className="insight-list" aria-label={`${copy.label} ${STATUS_COPY[status].label.toLowerCase()} insights`}>
          {candidateData.items.map((item) => <InsightRow item={item} key={item.candidate_id} />)}
        </section>
      )}
      {currentData?.available && currentData.items.length === 0 && (
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
