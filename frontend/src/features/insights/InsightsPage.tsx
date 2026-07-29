import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  COMPANY_BET_DIRECTION_COPY,
  getCachedJSON,
  type BriefDeliveryChannel,
  type BriefDeliveryResult,
  type BriefDeliveryStatus,
  type InsightAudience,
  type InsightDates,
  type InsightStatus,
  type InsightsResponse,
  type InvestmentAgentConnection,
  type InvestmentAgentInsightsResponse,
  type InvestmentAgentItem,
  type InvestmentCompanyUniverse,
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

type ReportDownloadState = 'idle' | 'generating' | 'ready' | 'error'
type BriefDeliveryState = 'idle' | 'loading' | 'choose' | 'confirm' | 'sending' | 'sent' | 'error'

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

function isInvestmentAgentResponse(
  payload: InsightsResponse,
): payload is InvestmentAgentInsightsResponse {
  return payload.content_kind === 'investment_agent'
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

type InvestmentBetDisplay = {
  id: string
  title: string
  direction: 'upside' | 'downside'
}

type InvestmentBetIndex = Record<string, InvestmentBetDisplay>

function InvestmentAgentConnectionView({
  connection,
  companyNames,
  betIndex,
}: {
  connection: InvestmentAgentConnection
  companyNames: Record<string, string>
  betIndex: InvestmentBetIndex
}) {
  const companies = [...connection.companies].sort(
    (left, right) => Number(right.threshold_met) - Number(left.threshold_met),
  )
  return (
    <details className="investment-agent-mechanism">
      <summary>
        <span className="investment-agent-mechanism-identity">
          <span className="investment-agent-mechanism-tickers">
            {companies.map((company) => {
              const bet = betIndex[company.bet_id]
              return (
                <span className="investment-agent-bet-signal" key={company.ticker}>
                  <span
                    className="investment-agent-bet-direction"
                    data-direction={bet?.direction}
                  >
                    <span aria-hidden="true" />
                    {bet ? COMPANY_BET_DIRECTION_COPY[bet.direction] : 'Direction'}
                  </span>
                  <span className="mono">{company.ticker}</span>
                  {company.threshold_met && (
                    <span className="investment-agent-threshold is-met">
                      Review thesis
                    </span>
                  )}
                </span>
              )
            })}
          </span>
        </span>
        <span className="investment-agent-mechanism-causal">
          {decodeTextEntities(connection.mechanism)}
        </span>
      </summary>
      <div className="investment-agent-mechanism-detail">
        <ol className="investment-agent-exposures">
          {companies.map((company) => {
            const bet = betIndex[company.bet_id]
            return (
              <li key={company.ticker}>
                <div className="investment-agent-exposure-head">
                  <strong>{companyNames[company.ticker] ?? company.ticker}</strong>
                  <Link
                    className="mono"
                    to={`/bit-lens/companies?company=${encodeURIComponent(company.ticker)}`}
                  >
                    {company.ticker}
                  </Link>
                  <span
                    className={`investment-agent-threshold ${
                      company.threshold_met ? 'is-met' : 'is-early'
                    }`}
                  >
                    {company.threshold_met ? 'Review thesis' : 'Early signal'}
                  </span>
                </div>
                <div className="investment-agent-exposure-body">
                  <Link
                    className="investment-agent-bet-meta"
                    to={`/bit-lens/companies?company=${encodeURIComponent(
                      company.ticker,
                    )}&bet=${encodeURIComponent(company.bet_id)}`}
                  >
                    <span
                      className="investment-agent-bet-direction"
                      data-direction={bet?.direction}
                    >
                      <span aria-hidden="true" />
                      {bet ? COMPANY_BET_DIRECTION_COPY[bet.direction] : 'Direction'}
                    </span>
                    <span className="investment-agent-bet-id mono">
                      {company.bet_id}
                    </span>
                  </Link>
                  <div className="investment-agent-exposure-copy">
                    {bet?.title && (
                      <Link
                        className="investment-agent-bet-title"
                        to={`/bit-lens/companies?company=${encodeURIComponent(
                          company.ticker,
                        )}&bet=${encodeURIComponent(company.bet_id)}`}
                      >
                        {decodeTextEntities(bet.title)}
                      </Link>
                    )}
                    <p className="investment-agent-exposure-impact">
                      {decodeTextEntities(company.impact)}
                    </p>
                  </div>
                </div>
              </li>
            )
          })}
        </ol>
      </div>
    </details>
  )
}

function InvestmentAgentProcess({ item }: { item: InvestmentAgentItem }) {
  const retainedCount = new Set(
    item.connections.flatMap((connection) =>
      connection.companies.map((company) => company.ticker),
    ),
  ).size
  const rejectedCount = Math.max(0, item.telemetry.memo_count - retainedCount)
  return (
    <details className="investment-agent-process">
      <summary>
        <span>How the agent got here</span>
        <span className="mono">
          {item.telemetry.company_universe_count} screened → {item.telemetry.memo_count} memos opened
          {' '}→ {retainedCount} retained
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

function InvestmentAgentInsight({
  item,
  betIndex,
}: {
  item: InvestmentAgentItem
  betIndex: InvestmentBetIndex
}) {
  const titleId = `investment-agent-${item.development_id}-title`
  const feedPath = `/evidence/feed?date=${item.day}&event_id=${encodeURIComponent(item.development_id)}`
  const artifacts = item.provenance?.artifacts ?? []
  const sourceLinkCount = 1 + (item.provenance?.original_post?.url ? 1 : 0) + artifacts.length
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
          <h2 id={titleId}>{decodeTextEntities(item.headline)}</h2>
        </header>

        <div className="investment-agent-opening">
          <section>
            <h3 className="mono">What changed</h3>
            <p>{decodeTextEntities(item.what_changed)}</p>
          </section>
        </div>

        {item.connections.length > 0 ? (
          <section className="investment-agent-companies" aria-label="Company read-throughs">
            <header>
              <h3>How this reaches companies</h3>
            </header>
            {item.connections
              .filter((connection) => Array.isArray(connection?.companies))
              .map((connection) => (
                <InvestmentAgentConnectionView
                  connection={connection}
                  companyNames={item.company_names}
                  betIndex={betIndex}
                  key={`${connection.mechanism}:${connection.companies.map((company) => company.ticker).join(',')}`}
                />
              ))}
          </section>
        ) : (
          <section className="investment-agent-no-match">
            <h3>No company connection cleared the bar</h3>
            <p>{decodeTextEntities(item.no_match_reason || 'No decision-useful connection was established.')}</p>
          </section>
        )}

        <details className="investment-agent-sources">
          <summary>
            <span>Sources</span>
            <span className="mono">
              {sourceLinkCount} {sourceLinkCount === 1 ? 'link' : 'links'}
            </span>
          </summary>
          <nav className="investment-agent-sources-body" aria-label="Evidence links">
            <Link to={feedPath}>View Development in Feed ↗</Link>
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
                Open original post ↗
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
                {artifacts.length === 1 ? 'Read source artifact ↗' : `Read source artifact ${index + 1} ↗`}
              </a>
            ))}
            <CopyEventId eventId={item.development_id} label="Copy ID" />
          </nav>
        </details>

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
        <strong>{run.company_connection_count}</strong> company connections
      </span>
    </p>
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
  const [investmentBetIndex, setInvestmentBetIndex] = useState<InvestmentBetIndex>({})
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
  const investmentAgentData =
    currentData && isInvestmentAgentResponse(currentData) ? currentData : null

  useEffect(() => {
    if (audience !== 'investment' || Object.keys(investmentBetIndex).length > 0) return
    let active = true
    getCachedJSON<InvestmentCompanyUniverse>('/api/bit-lens/companies')
      .then((payload) => {
        if (!active) return
        const nextIndex: InvestmentBetIndex = {}
        payload.companies.forEach((company) => {
          company.research_memo?.bets.forEach((bet) => {
            nextIndex[bet.id] = {
              id: bet.id,
              title: bet.if,
              direction: bet.direction,
            }
          })
        })
        setInvestmentBetIndex(nextIndex)
      })
      .catch(() => {
        // The Insight remains readable using its stored ticker and bet ID.
      })
    return () => {
      active = false
    }
  }, [audience, investmentBetIndex])
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
          {investmentAgentData?.available && investmentAgentData.items.length > 0 && (
            <InvestmentAgentYield data={investmentAgentData} />
          )}
        </div>
        <DailyBriefActions
          audience={audience}
          day={selectedDate}
          available={Boolean(investmentAgentData?.available)}
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
        <InsightState title={copy.emptyTitle} detail={currentData.reason || 'No company-aware Investment decision is available.'} />
      )}

      {investmentAgentData?.available && investmentAgentData.items.length > 0 && (
        <section
          className="insight-list investment-agent-list"
          aria-label={`${copy.label} company-aware ${STATUS_COPY[status].label.toLowerCase()} insights`}
        >
          {investmentAgentData.items.map((item) => (
            <InvestmentAgentInsight
              item={item}
              betIndex={investmentBetIndex}
              key={item.run_id}
            />
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
