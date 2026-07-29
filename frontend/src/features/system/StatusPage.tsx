import { useCallback, useEffect, useMemo, useState } from 'react'
import type {
  ArtifactDates,
  ArtifactLibrary,
  EventResponse,
  FeedDates,
  InsightDates,
  Registry,
} from '../../shared/api'
import { getJSON } from '../../shared/api'

type CheckState = 'available' | 'partial' | 'unavailable'

interface StatusData {
  registry: Registry | null
  eventDates: FeedDates | null
  latestEvents: EventResponse | null
  artifactDates: ArtifactDates | null
  artifacts: ArtifactLibrary | null
  investmentInsights: InsightDates | null
  engineeringInsights: InsightDates | null
  failures: string[]
  checkedAt: Date
}

interface StatusRow {
  name: string
  description: string
  state: CheckState
  stateLabel: string
  dataThrough: string | null
  lastUpdate: string | null
  coverage: string
}

const dayFormatter = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})

const timestampFormatter = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
  timeZoneName: 'short',
})

function formatDay(value: string | null | undefined): string | null {
  if (!value) return null
  return dayFormatter.format(new Date(`${value}T00:00:00Z`))
}

function formatTimestamp(value: string | null | undefined): string | null {
  if (!value) return null
  return timestampFormatter.format(new Date(value))
}

function formatNumber(value: number): string {
  return value.toLocaleString('en-US')
}

function countDatesInPublishedWindow(payload: FeedDates | null): number {
  if (!payload?.dates) return 0
  return payload.dates
    .filter((value) => (
      (!payload.date_from || value.day >= payload.date_from) &&
      (!payload.date_to || value.day <= payload.date_to)
    )).length
}

function insightTotals(payload: InsightDates | null) {
  return (payload?.dates ?? []).filter(
    (value) => value.content_kind === 'investment_agent',
  ).reduce(
    (total, value) => ({
      dates: total.dates + 1,
      insights: total.insights + value.item_count,
    }),
    { dates: 0, insights: 0 },
  )
}

async function settled<T>(label: string, request: Promise<T>) {
  try {
    return { value: await request, failure: null }
  } catch {
    return { value: null, failure: label }
  }
}

async function loadStatus(): Promise<StatusData> {
  const [registry, eventDates, artifactDates, artifacts, investment, engineering] = await Promise.all([
    settled('Registry', getJSON<Registry>('/api/registry?limit=1')),
    settled('Evidence dates', getJSON<FeedDates>('/api/events/dates')),
    settled('Artifact dates', getJSON<ArtifactDates>('/api/artifacts/dates')),
    settled('Artifact library', getJSON<ArtifactLibrary>('/api/artifacts?limit=1')),
    settled('Investment Insights', getJSON<InsightDates>('/api/insights/dates?audience=investment')),
    settled('AI Engineering Insights', getJSON<InsightDates>('/api/insights/dates?audience=ai_engineering')),
  ])

  const latestDay = eventDates.value?.latest_complete_date
  const latestEvents = latestDay
    ? await settled(
      'Audience routing',
      getJSON<EventResponse>(`/api/events?date=${latestDay}&include_evidence=false&limit=1`),
    )
    : { value: null, failure: 'Audience routing' }

  return {
    registry: registry.value,
    eventDates: eventDates.value,
    latestEvents: latestEvents.value,
    artifactDates: artifactDates.value,
    artifacts: artifacts.value,
    investmentInsights: investment.value,
    engineeringInsights: engineering.value,
    failures: [
      registry.failure,
      eventDates.failure,
      latestEvents.failure,
      artifactDates.failure,
      artifacts.failure,
      investment.failure,
      engineering.failure,
    ].filter((value): value is string => value !== null),
    checkedAt: new Date(),
  }
}

function StatusState({ state, label }: { state: CheckState; label: string }) {
  return (
    <span className={`system-state is-${state}`}>
      <i aria-hidden="true" />
      {label}
    </span>
  )
}

export default function Status() {
  const [data, setData] = useState<StatusData | null>(null)
  const [error, setError] = useState('')
  const [retryKey, setRetryKey] = useState(0)

  const refresh = useCallback(() => setRetryKey((value) => value + 1), [])

  useEffect(() => {
    let active = true
    setError('')
    loadStatus()
      .then((value) => {
        if (active) setData(value)
      })
      .catch((reason: unknown) => {
        if (active) setError(String(reason))
      })
    return () => { active = false }
  }, [retryKey])

  const rows = useMemo<StatusRow[]>(() => {
    if (!data) return []

    const publishedDayCount = countDatesInPublishedWindow(data.eventDates)
    const routing = data.latestEvents?.audience_routing_run
    const artifactCounts = data.artifacts?.catalog_fetch_state_counts
    const investment = insightTotals(data.investmentInsights)
    const engineering = insightTotals(data.engineeringInsights)
    const publishedDates = investment.dates + engineering.dates
    const publishedInsights = investment.insights + engineering.insights
    const insightsAvailable = Boolean(
      data.investmentInsights?.available && data.engineeringInsights?.available,
    )

    return [
      {
        name: 'Registry',
        description: 'Resolved identities and the screened network snapshot.',
        state: data.registry ? 'available' : 'unavailable',
        stateLabel: data.registry ? 'Available' : 'Unavailable',
        dataThrough: formatDay(data.registry?.network_context?.snapshot_completed_at?.slice(0, 10)),
        lastUpdate: formatTimestamp(data.registry?.network_context?.snapshot_completed_at),
        coverage: data.registry
          ? `${formatNumber(data.registry.total)} identities · ${formatNumber(data.registry.counts.rejected)} rejected`
          : 'Registry API did not respond',
      },
      {
        name: 'X collection',
        description: 'Complete UTC source days represented by the published evidence run.',
        state: data.eventDates?.available ? 'available' : 'unavailable',
        stateLabel: data.eventDates?.available ? 'Complete days' : 'Unavailable',
        dataThrough: formatDay(data.eventDates?.latest_complete_date),
        lastUpdate: null,
        coverage: data.eventDates?.available
          ? `${formatDay(data.eventDates.date_from)} → ${formatDay(data.eventDates.date_to)}`
          : (data.eventDates?.reason ?? 'Evidence date API did not respond'),
      },
      {
        name: 'Feed & Events',
        description: 'The currently published, exact structural evidence projection.',
        state: data.latestEvents?.available ? 'available' : 'unavailable',
        stateLabel: data.latestEvents?.available ? 'Published' : 'Unavailable',
        dataThrough: formatDay(data.eventDates?.latest_complete_date),
        lastUpdate: null,
        coverage: data.latestEvents?.available
          ? `${formatNumber(publishedDayCount)} complete UTC days · ${formatNumber(data.latestEvents.total ?? 0)} latest-day Events`
          : (data.latestEvents?.reason ?? 'Published Event API did not respond'),
      },
      {
        name: 'Artifacts',
        description: 'Canonical source documents disclosed by first-party Feed Events.',
        state: data.artifacts?.available
          ? ((artifactCounts?.retryable ?? 0) + (artifactCounts?.unavailable ?? 0) > 0 ? 'partial' : 'available')
          : 'unavailable',
        stateLabel: data.artifacts?.available
          ? ((artifactCounts?.retryable ?? 0) + (artifactCounts?.unavailable ?? 0) > 0 ? 'Available with gaps' : 'Available')
          : 'Unavailable',
        dataThrough: formatDay(data.artifactDates?.latest_date),
        lastUpdate: null,
        coverage: data.artifacts?.available && artifactCounts
          ? `${formatNumber(artifactCounts.ready)} ready · ${formatNumber(artifactCounts.retryable)} retryable · ${formatNumber(artifactCounts.unavailable)} unavailable`
          : (data.artifacts?.reason ?? 'Artifact API did not respond'),
      },
      {
        name: 'Audience routing',
        description: 'Independent Investment and AI Engineering relevance decisions.',
        state: routing
          ? (routing.completed_count === routing.expected_count ? 'available' : 'partial')
          : 'unavailable',
        stateLabel: routing
          ? (routing.completed_count === routing.expected_count ? 'Complete' : 'Partial')
          : 'Unavailable',
        dataThrough: formatDay(data.latestEvents?.date),
        lastUpdate: formatTimestamp(routing?.updated_at),
        coverage: routing
          ? `${formatNumber(routing.completed_count)} of ${formatNumber(routing.expected_count)} latest-day candidates`
          : 'No current routing run was exposed',
      },
      {
        name: 'Insights',
        description: 'Complete daily briefs published to the audience views.',
        state: insightsAvailable ? 'available' : 'unavailable',
        stateLabel: insightsAvailable ? 'Published' : 'Unavailable',
        dataThrough: formatDay(
          data.investmentInsights?.latest_date ?? data.engineeringInsights?.latest_date,
        ),
        lastUpdate: null,
        coverage: insightsAvailable
          ? `${formatNumber(publishedInsights)} published Insights · ${formatNumber(publishedDates)} audience-days`
          : 'One or both audience views did not respond',
      },
    ]
  }, [data])

  if (!data && !error) {
    return (
      <section className="system-view status-view" aria-labelledby="status-title" aria-busy="true">
        <h2 className="system-view-title" id="status-title">Current checkpoint</h2>
        <p className="page-sub">Reading the published product surfaces…</p>
        <div className="status-loading skeleton" />
      </section>
    )
  }

  if (error || !data) {
    return (
      <section className="system-view status-view" aria-labelledby="status-title">
        <h2 className="system-view-title" id="status-title">Current checkpoint</h2>
        <div className="status-error" role="alert">
          <strong>Status could not be read.</strong>
          <span>The product APIs did not return enough information for this view.</span>
          <button type="button" onClick={refresh}>Try again</button>
        </div>
      </section>
    )
  }

  const latestDay = formatDay(data.eventDates?.latest_complete_date)
  const overallState: CheckState = data.failures.length === 0 ? 'available' : 'partial'
  const overallLabel = data.failures.length === 0 ? 'Checkpoint available' : 'Partially available'

  return (
    <section className="system-view status-view" aria-labelledby="status-title">
      <div className="status-heading">
        <div>
          <h2 className="system-view-title" id="status-title">Current checkpoint</h2>
          <p className="page-sub">
            What the current product APIs can prove about publication, freshness,
            and coverage right now.
          </p>
        </div>
        <button className="status-refresh" type="button" onClick={refresh}>Check again</button>
      </div>

      <dl className="status-summary" aria-label="Checkpoint summary">
        <div>
          <dt>Published state</dt>
          <dd><StatusState state={overallState} label={overallLabel} /></dd>
        </div>
        <div>
          <dt>Evidence current through</dt>
          <dd className="mono">{latestDay ?? '—'}</dd>
        </div>
        <div>
          <dt>Observed</dt>
          <dd className="mono">{timestampFormatter.format(data.checkedAt)}</dd>
        </div>
        <div>
          <dt>Refresh model</dt>
          <dd>Operator-run</dd>
        </div>
      </dl>

      {data.failures.length > 0 && (
        <div className="status-notice" role="status">
          <strong>Some checks did not respond.</strong>
          <span>{data.failures.join(', ')}</span>
        </div>
      )}

      <div className="status-table-wrap">
        <table className="status-table">
          <thead>
            <tr>
              <th>Stage</th>
              <th>State</th>
              <th>Data through</th>
              <th>Last update</th>
              <th>Coverage</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.name}>
                <th scope="row">
                  <strong>{row.name}</strong>
                  <span>{row.description}</span>
                </th>
                <td><StatusState state={row.state} label={row.stateLabel} /></td>
                <td className="mono">{row.dataThrough ?? '—'}</td>
                <td className="mono">{row.lastUpdate ?? 'Not exposed'}</td>
                <td>{row.coverage}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="status-method mono">
        Checkpoint freshness is not a continuous SLA. This view reads the current
        product APIs; it does not infer host, disk, scheduler, or process health.
      </p>
    </section>
  )
}
