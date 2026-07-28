import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  getCachedJSON,
  prefetchExactEvent,
  type BriefDeliveryChannel,
  type BriefDeliveryResult,
  type BriefDeliveryStatus,
  type EditorialAnalysis,
  type EditorialDeclinedItem,
  type EditorialInsightItem,
  type EditorialEventRole,
  type EditorialInsightsResponse,
  type EngineeringEditorialAnalysis,
  type InsightAudience,
  type InsightDates,
  type InsightItem,
  type InsightStatus,
  type InsightsResponse,
  type InvestmentAgentCompanyAssessment,
  type InvestmentAgentInsightsResponse,
  type InvestmentAgentItem,
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
  suppressed: { label: 'Suppressed', description: 'Suppressed during candidate evaluation' },
  all: { label: 'All', description: 'Every completed candidate evaluation' },
}

const DECLINED_SECTION_ID = 'insight-declined'

type ReportDownloadState = 'idle' | 'generating' | 'ready' | 'error'
type BriefDeliveryState = 'idle' | 'loading' | 'choose' | 'confirm' | 'sending' | 'sent' | 'error'

const INVESTMENT_IMPACT_COPY = {
  positive: { icon: '↗', label: 'Potential positive' },
  negative: { icon: '↘', label: 'Potential negative' },
  mixed: { icon: '↔', label: 'Mixed' },
  uncertain: { icon: '?', label: 'Direction unclear' },
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

function legacyInsightIdFromHash(hash: string) {
  return hash.match(/^#insight-([a-f0-9]{64})$/)?.[1] ?? ''
}

function displayInsightDay(day: string) {
  const parsed = new Date(`${day}T12:00:00Z`)
  return Number.isNaN(parsed.getTime()) ? day : insightDay.format(parsed)
}

function isEditorialResponse(payload: InsightsResponse): payload is EditorialInsightsResponse {
  return payload.content_kind === 'daily_editorial'
}

function isInvestmentAgentResponse(
  payload: InsightsResponse,
): payload is InvestmentAgentInsightsResponse {
  return payload.content_kind === 'investment_agent'
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

function reportFilename(response: Response, audience: InsightAudience, day: string) {
  const disposition = response.headers.get('content-disposition') ?? ''
  const match = disposition.match(/filename="?([^";]+)"?/i)
  if (match?.[1]) return match[1]
  const audienceSlug = audience === 'investment' ? 'investment' : 'ai-engineering'
  return `fli-daily-brief-${day}-${audienceSlug}.pdf`
}

function DailyBriefDownload({
  audience,
  day,
  available,
  loading,
}: {
  audience: InsightAudience
  day: string
  available: boolean
  loading: boolean
}) {
  const [state, setState] = useState<ReportDownloadState>('idle')
  const [error, setError] = useState('')
  const requestRef = useRef<AbortController | null>(null)
  const statusId = 'daily-brief-download-status'
  const audienceLabel = AUDIENCE_COPY[audience].label

  useEffect(() => {
    requestRef.current?.abort()
    requestRef.current = null
    setState('idle')
    setError('')
    return () => requestRef.current?.abort()
  }, [audience, day])

  const download = async () => {
    if (!available || !day || state === 'generating') return
    const controller = new AbortController()
    requestRef.current?.abort()
    requestRef.current = controller
    setState('generating')
    setError('')
    let objectUrl = ''
    try {
      const response = await fetch(
        `/api/insights/report.pdf?audience=${audience}&date=${encodeURIComponent(day)}`,
        { headers: { Accept: 'application/pdf' }, signal: controller.signal },
      )
      if (!response.ok) {
        const payload = await response.json().catch(() => null) as { detail?: string } | null
        throw new Error(payload?.detail || `The report request failed with status ${response.status}.`)
      }
      const blob = await response.blob()
      if (requestRef.current !== controller) return
      objectUrl = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = objectUrl
      anchor.download = reportFilename(response, audience, day)
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
      objectUrl = ''
      setState('ready')
    } catch (cause) {
      if (controller.signal.aborted) return
      setError(cause instanceof Error ? cause.message : 'The PDF could not be prepared.')
      setState('error')
    } finally {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      if (requestRef.current === controller) requestRef.current = null
    }
  }

  const disabled = !available || !day || loading || state === 'generating'
  const label = state === 'generating'
    ? 'Preparing PDF…'
    : state === 'ready'
      ? 'Download again'
      : 'Download PDF'
  const disabledReason = loading
    ? 'The daily brief is still loading.'
    : !available
      ? 'PDF export is available for complete kept daily briefs.'
      : ''

  return (
    <div className="insight-report-action">
      <button
        className="insight-report-button"
        data-state={state}
        type="button"
        onClick={download}
        disabled={disabled}
        aria-busy={state === 'generating'}
        aria-describedby={state === 'ready' || state === 'error' ? statusId : undefined}
        aria-label={`${label} for ${audienceLabel}, ${day}`}
        title={disabledReason || `Download the ${audienceLabel} brief for ${day}`}
      >
        <svg aria-hidden="true" viewBox="0 0 20 20">
          <path d="M10 2.5v10m0 0 3.5-3.5M10 12.5 6.5 9M3.5 16.5h13" />
        </svg>
        <span>{label}</span>
      </button>
      <span
        className={`insight-report-status insight-report-status--${state}`}
        id={statusId}
        role={state === 'error' ? 'alert' : 'status'}
        aria-live="polite"
      >
        {state === 'ready' ? 'PDF downloaded.' : error}
      </span>
    </div>
  )
}

function DailyBriefDelivery({
  audience,
  day,
  available,
  loading,
}: {
  audience: InsightAudience
  day: string
  available: boolean
  loading: boolean
}) {
  const [open, setOpen] = useState(false)
  const [state, setState] = useState<BriefDeliveryState>('idle')
  const [status, setStatus] = useState<BriefDeliveryStatus | null>(null)
  const [selected, setSelected] = useState<BriefDeliveryChannel | null>(null)
  const [result, setResult] = useState<BriefDeliveryResult | null>(null)
  const [error, setError] = useState('')
  const actionRef = useRef<HTMLDivElement | null>(null)
  const buttonRef = useRef<HTMLButtonElement | null>(null)
  const panelRef = useRef<HTMLDivElement | null>(null)
  const requestRef = useRef<AbortController | null>(null)
  const panelId = 'daily-brief-delivery-panel'

  useEffect(() => {
    requestRef.current?.abort()
    requestRef.current = null
    setOpen(false)
    setState('idle')
    setStatus(null)
    setSelected(null)
    setResult(null)
    setError('')
    return () => requestRef.current?.abort()
  }, [audience, day])

  useEffect(() => {
    if (!open) return
    panelRef.current?.focus()
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!actionRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setOpen(false)
      buttonRef.current?.focus()
    }
    document.addEventListener('pointerdown', closeOnOutsidePointer)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsidePointer)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [open])

  const loadStatus = async () => {
    if (!available || !day || loading) return
    if (open) {
      setOpen(false)
      return
    }
    const controller = new AbortController()
    requestRef.current?.abort()
    requestRef.current = controller
    setOpen(true)
    setState('loading')
    setSelected(null)
    setResult(null)
    setError('')
    try {
      const response = await fetch(
        `/api/insights/delivery?audience=${audience}&date=${encodeURIComponent(day)}`,
        { headers: { Accept: 'application/json' }, signal: controller.signal },
      )
      const payload = await response.json().catch(() => null) as BriefDeliveryStatus | { detail?: string } | null
      if (!response.ok || !payload || !('channels' in payload)) {
        const detail = payload && 'detail' in payload ? payload.detail : null
        throw new Error(detail || 'Delivery options could not be loaded.')
      }
      if (requestRef.current !== controller) return
      setStatus(payload)
      setState('choose')
    } catch (cause) {
      if (controller.signal.aborted) return
      setError(cause instanceof Error ? cause.message : 'Delivery options could not be loaded.')
      setState('error')
    } finally {
      if (requestRef.current === controller) requestRef.current = null
    }
  }

  const selectChannel = (channel: BriefDeliveryChannel) => {
    setSelected(channel)
    setError('')
    setState('confirm')
  }

  const send = async () => {
    if (!selected || !status || state === 'sending') return
    const controller = new AbortController()
    requestRef.current?.abort()
    requestRef.current = controller
    setState('sending')
    setError('')
    try {
      const response = await fetch('/api/insights/delivery', {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ audience, date: day, channel: selected }),
        signal: controller.signal,
      })
      const payload = await response.json().catch(() => null) as BriefDeliveryResult | { detail?: string } | null
      if (!response.ok || !payload || !('status' in payload) || payload.status !== 'sent') {
        const detail = payload && 'detail' in payload ? payload.detail : null
        throw new Error(detail || `Delivery failed with status ${response.status}.`)
      }
      if (requestRef.current !== controller) return
      setResult(payload)
      setState('sent')
    } catch (cause) {
      if (controller.signal.aborted) return
      setError(cause instanceof Error ? cause.message : 'The Daily Brief could not be sent.')
      setState('confirm')
    } finally {
      if (requestRef.current === controller) requestRef.current = null
    }
  }

  const disabled = !available || !day || loading
  const selectedStatus = status?.channels.find((channel) => channel.channel === selected)
  const close = () => {
    setOpen(false)
    buttonRef.current?.focus()
  }

  return (
    <div className="insight-delivery-action" ref={actionRef}>
      <button
        className="insight-delivery-button"
        type="button"
        onClick={loadStatus}
        disabled={disabled}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        title={disabled ? 'Send is available for complete kept daily briefs.' : 'Send this Daily Brief'}
        ref={buttonRef}
      >
        <svg aria-hidden="true" viewBox="0 0 20 20">
          <path d="m3 4 14 6-14 6 2.5-6L3 4Zm2.5 6H17" />
        </svg>
        <span>Send brief</span>
      </button>

      {open && (
        <div
          className="insight-delivery-panel"
          id={panelId}
          role="dialog"
          aria-label="Send Daily Brief"
          tabIndex={-1}
          ref={panelRef}
        >
          <div className="insight-delivery-panel-head">
            <div>
              <span className="mono">Daily brief delivery</span>
              <h2>{state === 'confirm' || state === 'sending' ? 'Confirm delivery' : state === 'sent' ? 'Brief sent' : 'Send this brief'}</h2>
            </div>
            <button type="button" onClick={close} aria-label="Close delivery panel">×</button>
          </div>

          {state === 'loading' && (
            <p className="insight-delivery-loading" role="status">Checking delivery channels…</p>
          )}

          {state === 'error' && (
            <div className="insight-delivery-message insight-delivery-message--error" role="alert">
              <p>{error}</p>
              <button type="button" onClick={loadStatus}>Try again</button>
            </div>
          )}

          {state === 'choose' && status && (
            <>
              <p className="insight-delivery-summary">
                {AUDIENCE_COPY[audience].label} · {displayInsightDay(day)} · {status.total_insight_count} Insights
              </p>
              <div className="insight-delivery-options">
                {status.channels.map((channel) => (
                  <button
                    type="button"
                    onClick={() => selectChannel(channel.channel)}
                    disabled={!channel.available}
                    key={channel.channel}
                  >
                    <span className="insight-delivery-option-mark" aria-hidden="true">
                      {channel.channel === 'slack' ? '#' : '@'}
                    </span>
                    <span>
                      <strong>{channel.label}</strong>
                      <small>{channel.destination}</small>
                    </span>
                    <em>
                      {channel.configured
                        ? channel.channel === 'slack'
                          ? `All ${status.total_insight_count} Insights + PDF link`
                          : `Top ${status.top_insight_count} + PDF attachment`
                        : 'Not configured'}
                    </em>
                  </button>
                ))}
              </div>
            </>
          )}

          {(state === 'confirm' || state === 'sending') && status && selectedStatus && (
            <div className="insight-delivery-confirm">
              {selected === 'slack' ? (
                <p>
                  Send all {status.total_insight_count} cited Insights, with each complete interpretation, to <strong>{selectedStatus.destination}</strong>.
                  The message will also link to the full brief and PDF.
                </p>
              ) : (
                <p>
                  Send the top {status.top_insight_count} cited Insights to <strong>{selectedStatus.destination}</strong>.
                  The complete PDF will be attached.
                </p>
              )}
              <dl>
                <div><dt>Audience</dt><dd>{AUDIENCE_COPY[audience].label}</dd></div>
                <div><dt>Date</dt><dd>{displayInsightDay(day)}</dd></div>
              </dl>
              {error && <p className="insight-delivery-inline-error" role="alert">{error}</p>}
              <div className="insight-delivery-confirm-actions">
                <button type="button" onClick={() => { setState('choose'); setError('') }} disabled={state === 'sending'}>Back</button>
                <button type="button" className="is-primary" onClick={send} disabled={state === 'sending'}>
                  {state === 'sending' ? 'Sending…' : selected === 'slack' ? 'Send to Slack' : 'Send email'}
                </button>
              </div>
            </div>
          )}

          {state === 'sent' && result && (
            <div className="insight-delivery-message insight-delivery-message--success" role="status">
              <span aria-hidden="true">✓</span>
              {result.channel === 'slack' ? (
                <p>
                  <strong>Slack notification sent.</strong>
                  {result.insight_count} complete Insights and links to the full brief and PDF were sent to {result.destination}.
                </p>
              ) : (
                <p>
                  <strong>Email sent.</strong>
                  {result.insight_count} Insights and the attached PDF were sent to {result.destination}.
                </p>
              )}
              <button type="button" onClick={close}>Done</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DailyBriefActions({
  audience,
  day,
  available,
  loading,
}: {
  audience: InsightAudience
  day: string
  available: boolean
  loading: boolean
}) {
  return (
    <div className="insight-brief-actions">
      <DailyBriefDelivery audience={audience} day={day} available={available} loading={loading} />
      <DailyBriefDownload audience={audience} day={day} available={available} loading={loading} />
    </div>
  )
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

function ExactEventLink({
  day,
  eventId,
  children,
  className,
  ariaLabel,
  title,
}: {
  day: string
  eventId: string
  children: ReactNode
  className?: string
  ariaLabel?: string
  title?: string
}) {
  const eventUrl = `/evidence/feed?date=${day}&event_id=${encodeURIComponent(eventId)}`
  const preload = () => prefetchExactEvent(day, eventId)

  return (
    <Link
      className={className}
      to={eventUrl}
      aria-label={ariaLabel}
      title={title}
      onPointerEnter={preload}
      onFocus={preload}
      onTouchStart={preload}
    >
      {children}
    </Link>
  )
}

function InsightRow({ item }: { item: InsightItem }) {
  const isKept = item.decision === 'surface'
  const feedRankLabel = `Feed rank ${item.feed_rank}`
  const title = item.title
  const accessibleName = `${feedRankLabel}: ${decodeTextEntities(title)}`
  const titleId = `${item.audience}-${item.candidate_id}-title`
  return (
    <article
      className={`insight-row insight-row--${isKept ? 'kept' : 'suppressed'}`}
      aria-labelledby={titleId}
    >
      <div className="insight-rank mono">
        <ExactEventLink
          day={item.day}
          eventId={item.event_id}
          className="insight-feed-link"
          ariaLabel={`Open ${feedRankLabel.toLowerCase()} in its exact Feed Event`}
          title="Open exact Feed Event"
        >
          <strong>#{item.feed_rank}</strong>
          <span>Feed rank ↗</span>
        </ExactEventLink>
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
            <ExactEventLink
              day={item.day}
              eventId={item.event_id}
              ariaLabel={`Open the exact Feed Event for ${accessibleName}`}
            >
              Open Event ↗
            </ExactEventLink>
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

const EDITORIAL_ROLE_COPY: Record<EditorialEventRole, string> = {
  primary: 'Primary',
  supporting: 'Supporting',
  context: 'Context',
  counterevidence: 'Counterevidence',
}

function EditorialSources({ item }: { item: EditorialInsightItem }) {
  const researchSources = item.citations.filter(
    (citation) => citation.kind !== 'event',
  )
  const titleId = `${item.insight_id}-sources`

  return (
    <section className="editorial-sources" aria-labelledby={titleId}>
      <h3 id={titleId}>Sources</h3>
      <div className="editorial-source-columns">
        <section aria-label="Original feed sources">
          <h4 className="mono">
            Original feed
            {item.events.length > 1 && (
              <span className="editorial-source-count"> · {item.events.length} Events merged</span>
            )}
          </h4>
          <ul className="editorial-source-list">
            {item.events.map((event) => {
              return (
                <li key={event.event_id}>
                  <div className="editorial-source-head">
                    <span
                      className={`editorial-source-role mono editorial-source-role--${event.role}`}
                    >
                      {EDITORIAL_ROLE_COPY[event.role] ?? event.role}
                    </span>
                    <ExactEventLink
                      day={item.day}
                      eventId={event.event_id}
                      className="editorial-source-title"
                    >
                      Feed #{event.feed_rank} ↗
                    </ExactEventLink>
                  </div>
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
    const referenceUrl = new URL(window.location.href)
    referenceUrl.searchParams.set('insight', item.insight_id)
    referenceUrl.hash = ''

    try {
      await navigator.clipboard.writeText(referenceUrl.toString())
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
      aria-label={`Copy link to ${decodeTextEntities(item.title)}`}
    >
      <span role="status" aria-live="polite">
        {copyStatus === 'copied'
          ? 'Link copied'
          : copyStatus === 'failed'
            ? 'Copy failed'
            : 'Copy link'}
      </span>
    </button>
  )
}

function EditorialInsightRow({ item }: { item: EditorialInsightItem }) {
  const titleId = `${item.insight_id}-title`
  const rankExplanationId = `${item.insight_id}-rank-explanation`
  const [rankExplanationOpen, setRankExplanationOpen] = useState(false)
  const investmentAnalysis = isInvestmentAnalysis(item.analysis) ? item.analysis : null
  const engineeringAnalysis = isEngineeringAnalysis(item.analysis) ? item.analysis : null
  const permalinkId = `insight-${item.insight_id}`

  return (
    <article
      className="insight-row editorial-insight-row"
      id={permalinkId}
      aria-labelledby={titleId}
    >
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

function DeclinedCandidates({
  items,
  reviewedCount,
  day,
  open,
  onToggle,
}: {
  items: EditorialDeclinedItem[]
  reviewedCount: number
  day: string
  open: boolean
  onToggle: () => void
}) {
  return (
    <section
      className="insight-declined"
      id={DECLINED_SECTION_ID}
      aria-label="Candidates declined in writing"
    >
      <button
        type="button"
        className="insight-declined-toggle"
        aria-expanded={open}
        onClick={onToggle}
      >
        <span className="insight-declined-title mono">Declined in writing</span>
        <span className="insight-declined-summary">
          {reviewedCount} candidates reviewed · {items.length} declined with a written reason
        </span>
        <span className="insight-declined-caret mono" aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <ul className="insight-declined-list">
          {items.map((item) => (
            <li className="insight-declined-row" key={item.event_id}>
              <div className="insight-declined-rank mono" aria-label={`Attention rank ${item.feed_rank}`}>
                #{item.feed_rank}
              </div>
              <div className="insight-declined-cell">
                <h4 className="mono">Event · root post</h4>
                <Link
                  className="insight-declined-author mono"
                  to={`/evidence/feed?date=${day}&event_id=${encodeURIComponent(item.event_id)}`}
                  aria-label={`Open the full event by ${item.author} on the evidence page`}
                >
                  {item.author} · open event ↗
                </Link>
                <p className="insight-declined-excerpt">“{decodeTextEntities(item.excerpt)}”</p>
              </div>
              <div className="insight-declined-cell">
                <h4 className="mono">Why declined</h4>
                <p className="insight-declined-reason">{decodeTextEntities(item.reason)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

const INVESTMENT_AGENT_DIRECTION = {
  positive: { icon: '↗', label: 'Potential positive' },
  negative: { icon: '↘', label: 'Potential negative' },
  mixed: { icon: '↔', label: 'Mixed' },
  unclear: { icon: '?', label: 'Direction unclear' },
} as const

function InvestmentAgentCompany({
  assessment,
  companyName,
  feedPath,
}: {
  assessment: InvestmentAgentCompanyAssessment
  companyName: string
  feedPath: string
}) {
  const direction = INVESTMENT_AGENT_DIRECTION[assessment.direction]
  return (
    <details className="investment-agent-company">
      <summary>
        <span className="investment-agent-company-identity">
          <strong>{companyName}</strong>
          <span className="mono">{assessment.ticker}</span>
        </span>
        <span
          className="investment-agent-direction"
          data-direction={assessment.direction}
        >
          <span aria-hidden="true">{direction.icon}</span>
          {direction.label}
        </span>
        <span className="investment-agent-company-summary">
          {decodeTextEntities(assessment.bottom_line)}
        </span>
      </summary>
      <div className="investment-agent-company-detail">
        <section>
          <h4 className="mono">Why this company</h4>
          <p>{decodeTextEntities(assessment.mechanism)}</p>
        </section>
        <section>
          <h4 className="mono">What could move</h4>
          <p>{decodeTextEntities(assessment.affected_driver)}</p>
        </section>
        <section>
          <h4 className="mono">What remains unproven</h4>
          <p>{decodeTextEntities(assessment.main_uncertainty)}</p>
        </section>
        <section>
          <h4 className="mono">What to check next</h4>
          <p>{decodeTextEntities(assessment.next_check)}</p>
        </section>
      </div>
      <div className="investment-agent-source-material">
        <span className="mono">Source material reviewed</span>
        <Link to={feedPath}>Development evidence ↗</Link>
        <Link to={`/bit-lens/companies?company=${encodeURIComponent(assessment.ticker)}`}>
          Company memo ↗
        </Link>
      </div>
    </details>
  )
}

function InvestmentAgentProcess({ item }: { item: InvestmentAgentItem }) {
  const rejectedCount = item.rejected_after_memo.length
  return (
    <details className="investment-agent-process">
      <summary>
        <span>How the agent got here</span>
        <span className="mono">
          {item.telemetry.company_universe_count} screened → {item.telemetry.memo_count} memos opened
          {' '}→ {item.company_assessments.length} retained
          {rejectedCount > 0 ? ` → ${rejectedCount} rejected` : ''}
        </span>
      </summary>
      <div className="investment-agent-process-body">
        <ol>
          {item.memo_calls.map((call) => (
            <li key={call.call_id}>
              <div className="investment-agent-process-company">
                <strong>{item.company_names[call.arguments.ticker] ?? call.arguments.ticker}</strong>
                <span className="mono">{call.arguments.ticker} · {call.arguments.connection_type}</span>
              </div>
              <div>
                <h4 className="mono">Why its memo was opened</h4>
                <p>{decodeTextEntities(call.arguments.why_memo_is_needed)}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </details>
  )
}

function InvestmentAgentInsight({ item }: { item: InvestmentAgentItem }) {
  const titleId = `investment-agent-${item.development_id}-title`
  const feedPath = `/evidence/feed?date=${item.day}&event_id=${encodeURIComponent(item.development_id)}`
  const artifacts = item.provenance?.artifacts ?? []
  return (
    <article
      className="insight-row investment-agent-row"
      id={`investment-agent-${item.development_id}`}
      aria-labelledby={titleId}
    >
      <div className="insight-rank investment-agent-rank mono">
        <Link to={feedPath}>
          <strong>#{item.daily_rank}</strong>
          <span>Feed rank ↗</span>
        </Link>
      </div>
      <div className="insight-body investment-agent-body">
        <header className="insight-head investment-agent-head">
          <h2 id={titleId}>{decodeTextEntities(item.investment_headline)}</h2>
          <nav className="investment-agent-provenance" aria-label="Evidence links">
            <Link to={feedPath}>Open in Feed ↗</Link>
            {item.provenance?.original_post?.url && (
              <a
                href={item.provenance.original_post.url}
                target="_blank"
                rel="noreferrer"
                title={
                  item.provenance.original_post.author
                    ? `Original post by ${item.provenance.original_post.author}`
                    : 'Original post'
                }
              >
                Original post ↗
              </a>
            )}
            {artifacts.map((artifact, index) => (
              <a
                href={artifact.url}
                key={artifact.artifact_id || artifact.url}
                target="_blank"
                rel="noreferrer"
                title={artifact.title}
              >
                {artifacts.length === 1 ? 'Source artifact ↗' : `Source artifact ${index + 1} ↗`}
              </a>
            ))}
          </nav>
        </header>

        <div className="investment-agent-opening">
          <section>
            <h3 className="mono">What changed</h3>
            <p>{decodeTextEntities(item.development_summary)}</p>
          </section>
          <section>
            <h3 className="mono">Portfolio read-through</h3>
            <p>{decodeTextEntities(item.portfolio_readthrough)}</p>
          </section>
        </div>

        {item.company_assessments.length > 0 ? (
          <section className="investment-agent-companies" aria-label="Company read-throughs">
            <header>
              <h3>Company read-throughs</h3>
            </header>
            {item.company_assessments.map((assessment) => (
              <InvestmentAgentCompany
                assessment={assessment}
                companyName={item.company_names[assessment.ticker] ?? assessment.ticker}
                feedPath={feedPath}
                key={assessment.ticker}
              />
            ))}
          </section>
        ) : (
          <section className="investment-agent-no-match">
            <h3>No company connection cleared the bar</h3>
            <p>{decodeTextEntities(item.no_match_reason || 'No decision-useful connection was established.')}</p>
          </section>
        )}

        {item.rejected_after_memo.length > 0 && (
          <section className="investment-agent-rejections">
            <h3>Opened, then rejected</h3>
            <ul>
              {item.rejected_after_memo.map((rejection) => (
                <li key={rejection.ticker}>
                  <strong>
                    {item.company_names[rejection.ticker] ?? rejection.ticker}
                    {' '}<span className="mono">{rejection.ticker}</span>
                  </strong>
                  <p>{decodeTextEntities(rejection.reason)}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        <InvestmentAgentProcess item={item} />
      </div>
    </article>
  )
}

function InvestmentAgentYield({
  data,
}: {
  data: InvestmentAgentInsightsResponse
}) {
  const run = data.run
  if (!run) return null
  return (
    <p className="insight-yield">
      <span className="insight-yield-part">
        <strong>{run.surfaced_development_count}</strong> Development surfaced
      </span>
      <span className="insight-yield-sep" aria-hidden="true">·</span>
      <span className="insight-yield-part">
        <strong>{run.company_assessment_count}</strong> company read-throughs
      </span>
      <span className="insight-yield-sep" aria-hidden="true">·</span>
      <span className="insight-yield-part">
        <strong>{run.rejected_company_count}</strong> rejected after memo review
      </span>
    </p>
  )
}

function InsightYield({
  keptCount,
  reviewedCount,
  declinedCount,
  onRevealDeclined,
}: {
  keptCount: number
  reviewedCount: number
  declinedCount: number
  onRevealDeclined: () => void
}) {
  return (
    <p className="insight-yield">
      <span className="insight-yield-part">
        <strong>{keptCount}</strong> published
      </span>
      <span className="insight-yield-sep" aria-hidden="true">·</span>
      <span className="insight-yield-part">
        <strong>{reviewedCount}</strong> candidates reviewed
      </span>
      {declinedCount > 0 && (
        <>
          <span className="insight-yield-sep" aria-hidden="true">·</span>
          <button
            type="button"
            className="insight-yield-part insight-yield-link"
            onClick={onRevealDeclined}
            aria-label={`Show the ${declinedCount} candidates declined in writing`}
          >
            <strong>{declinedCount}</strong> declined in writing
          </button>
        </>
      )}
    </p>
  )
}

export default function Insights() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { rememberDate } = useAuditDate()
  const audience = parseAudience(searchParams.get('audience'))
  const status = parseStatus(searchParams.get('status'))
  const selectedDate = searchParams.get('date') ?? ''
  const legacyInsightId = legacyInsightIdFromHash(window.location.hash)
  const selectedInsightId = searchParams.get('insight') ?? legacyInsightId
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
  const [declinedOpen, setDeclinedOpen] = useState(false)
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
  const investmentAgentData =
    currentData && isInvestmentAgentResponse(currentData) ? currentData : null
  const candidateData =
    currentData &&
    !isEditorialResponse(currentData) &&
    !isInvestmentAgentResponse(currentData)
      ? currentData
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
  const declinedItems = editorialData?.declined ?? []
  const reviewedCandidateCount =
    (editorialData?.run?.counts.included_candidates ?? 0) +
    (editorialData?.run?.counts.not_selected_candidates ?? 0)

  useEffect(() => {
    if (
      searchParams.get('audience') === audience &&
      searchParams.get('status') === status &&
      !searchParams.has('view') &&
      !legacyInsightId
    ) return
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('audience', audience)
    nextParams.set('status', status)
    nextParams.delete('view')
    if (!nextParams.has('insight') && legacyInsightId) {
      nextParams.set('insight', legacyInsightId)
    }
    setSearchParams(nextParams, { replace: true })
  }, [audience, legacyInsightId, searchParams, setSearchParams, status])

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
      !selectedDate ||
      (
        currentDates !== null &&
        (
          !currentDates.available ||
          !currentDates.dates.some((value) => value.day === selectedDate)
        )
      )
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

  useEffect(() => {
    if (!editorialData || !selectedInsightId) return
    const targetId = `insight-${selectedInsightId}`
    const target = document.getElementById(targetId)
    if (!target?.classList.contains('editorial-insight-row')) return
    window.requestAnimationFrame(() => target.scrollIntoView({ block: 'start' }))
  }, [editorialData, selectedInsightId])

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
    nextParams.delete('insight')
    if (nextDate) nextParams.set('date', nextDate)
    else nextParams.delete('date')
    setSearchParams(nextParams, { replace: true })
  }

  const revealDeclined = () => {
    setDeclinedOpen(true)
    window.requestAnimationFrame(() => {
      document
        .getElementById(DECLINED_SECTION_ID)
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
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
        <div className="insight-page-intro">
          <h1 className="page-title">{copy.title}</h1>
          <p className="page-sub">{copy.subtitle}</p>
          {editorialData?.available && editorialData.items.length > 0 && reviewedCandidateCount > 0 && (
            <InsightYield
              keptCount={editorialData.items.length}
              reviewedCount={reviewedCandidateCount}
              declinedCount={declinedItems.length}
              onRevealDeclined={revealDeclined}
            />
          )}
          {investmentAgentData?.available && investmentAgentData.items.length > 0 && (
            <InvestmentAgentYield data={investmentAgentData} />
          )}
        </div>
        <DailyBriefActions
          audience={audience}
          day={selectedDate}
          available={Boolean(editorialData?.available)}
          loading={datesLoading || dataLoading}
        />
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
        <section className="insight-list" aria-label={`${copy.label} ${STATUS_COPY[status].label.toLowerCase()} insights`}>
          {editorialData.items.map((item) => (
            <EditorialInsightRow item={item} key={item.insight_id} />
          ))}
        </section>
      )}
      {editorialData?.available && editorialData.date && declinedItems.length > 0 && (
        <DeclinedCandidates
          items={declinedItems}
          reviewedCount={reviewedCandidateCount}
          day={editorialData.date}
          open={declinedOpen}
          onToggle={() => setDeclinedOpen((value) => !value)}
        />
      )}
      {candidateData?.available && candidateData.items.length > 0 && (
        <section className="insight-list" aria-label={`${copy.label} ${STATUS_COPY[status].label.toLowerCase()} insights`}>
          {candidateData.items.map((item) => <InsightRow item={item} key={item.candidate_id} />)}
        </section>
      )}
      {investmentAgentData?.available && investmentAgentData.items.length > 0 && (
        <section
          className="insight-list investment-agent-list"
          aria-label={`${copy.label} company-aware ${STATUS_COPY[status].label.toLowerCase()} insights`}
        >
          {investmentAgentData.items.map((item) => (
            <InvestmentAgentInsight item={item} key={item.run_id} />
          ))}
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
