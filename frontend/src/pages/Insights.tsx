import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  getCachedJSON,
  type InsightDates,
  type InsightItem,
  type InsightsResponse,
} from '../api'
import DateNavigator from '../components/DateNavigator'
import {
  getDateWindow,
  shiftDateWindow,
  type DateWindowDirection,
} from '../dateWindow'

const insightDay = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})

function sourceTypeLabel(sourceType: string) {
  if (sourceType === 'x_post') return 'X post'
  if (sourceType === 'artifact') return 'Primary artifact'
  return sourceType.replaceAll('_', ' ')
}

function sourceLabel(item: InsightItem) {
  return item.citation.author || item.citation.title || sourceTypeLabel(item.citation.source_type)
}

function InsightRow({ item }: { item: InsightItem }) {
  return (
    <article className="insight-row">
      <div className="insight-rank mono" aria-label={`Feed rank ${item.current_rank}`}>
        <strong>#{item.current_rank}</strong>
        <span>Feed rank</span>
      </div>
      <div className="insight-body">
        <header className="insight-head">
          <h2>{item.claim}</h2>
          <div className="insight-provenance mono">
            <a href={item.citation.url} target="_blank" rel="noreferrer">
              {sourceLabel(item)}
            </a>
            <span>{sourceTypeLabel(item.citation.source_type)}</span>
            <time dateTime={item.day}>{insightDay.format(new Date(`${item.day}T00:00:00Z`))}</time>
          </div>
        </header>

        <blockquote className="insight-citation">
          <p>“{item.citation.quote}”</p>
          <cite>
            <a href={item.citation.url} target="_blank" rel="noreferrer">
              Open exact evidence ↗
            </a>
          </cite>
        </blockquote>

        <section className="insight-meaning" aria-label="Interpretation">
          <div className="insight-why">
            <h3 className="mono">Why it matters</h3>
            <p>{item.why_it_matters}</p>
          </div>
          <div className="insight-implications">
            <div>
              <h3 className="mono">Investment lens</h3>
              <p>{item.investment_implication}</p>
            </div>
            <div>
              <h3 className="mono">Engineering lens</h3>
              <p>{item.engineering_implication}</p>
            </div>
          </div>
        </section>
      </div>
    </article>
  )
}

export default function Insights() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialDate = useRef(searchParams.get('date') ?? '')
  const [dates, setDates] = useState<InsightDates | null>(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [dateWindowEnd, setDateWindowEnd] = useState(0)
  const [data, setData] = useState<InsightsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
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
    let live = true
    getCachedJSON<InsightDates>('/api/insights/dates')
      .then((payload) => {
        if (!live) return
        setDates(payload)
        setDateWindowEnd(payload.dates.length)
        if (payload.available && payload.latest_date) {
          const linkedDate = initialDate.current
          setSelectedDate(
            payload.dates.some((value) => value.day === linkedDate)
              ? linkedDate
              : payload.latest_date,
          )
        }
      })
      .catch(() => {
        if (live) setError('Couldn’t load available insight dates. Reload to try again.')
      })
    return () => {
      live = false
    }
  }, [])

  useEffect(() => {
    if (!selectedDate) return
    let live = true
    setError(null)
    setData(null)
    getCachedJSON<InsightsResponse>(`/api/insights?date=${selectedDate}`)
      .then((payload) => {
        if (live) setData(payload)
      })
      .catch(() => {
        if (live) setError('Couldn’t load cited insights for this date. Reload to try again.')
      })
    setSearchParams({ date: selectedDate }, { replace: true })
    return () => {
      live = false
    }
  }, [selectedDate, setSearchParams])

  const moveDateWindow = (direction: DateWindowDirection) => {
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

  const items = data?.items ?? []
  const run = data?.run

  return (
    <div className="page insight-page">
      <header className="page-head insight-page-head">
        <h1 className="page-title">Cited insights</h1>
        <p className="page-sub">
          Decision-ready claims from accepted evidence, each bound to an exact source passage.
        </p>
        {data?.available && run && (
          <p className="page-method-line mono">
            <span>{run.verified_count.toLocaleString('en-US')} verified</span>
            {run.failed_count > 0 && <span>{run.failed_count.toLocaleString('en-US')} failed verification</span>}
            <span>{run.model}</span>
            <span>{run.prompt_version}</span>
          </p>
        )}
      </header>

      {(!dates || dates.available) && (
        <section className="feed-calendar" aria-label="Available cited insight dates">
          <DateNavigator
            dates={visibleDates}
            selectedDate={selectedDate}
            onSelectDate={setSelectedDate}
            canShowOlderDates={canShowOlderDates}
            canShowNewerDates={canShowNewerDates}
            onShowOlderDates={() => moveDateWindow('older')}
            onShowNewerDates={() => moveDateWindow('newer')}
            ariaLabel="Cited insight date"
            itemLabel="verified insights"
            loading={dates === null}
          />
        </section>
      )}

      {error && <p className="insight-message mono">{error}</p>}
      {dates && !dates.available && (
        <p className="insight-message mono">{dates.reason || 'Cited insights are not available yet.'}</p>
      )}
      {data && !data.available && (
        <p className="insight-message mono">{data.reason || 'Cited insights are not available yet.'}</p>
      )}

      {data?.available && items.length > 0 && (
        <section className="insight-list" aria-label="Verified cited insights">
          {items.map((item) => <InsightRow item={item} key={item.event_id} />)}
        </section>
      )}

      {data?.available && items.length === 0 && (
        <p className="insight-empty mono">
          No verified insights were produced by this run. Failed or unverified claims are never shown here.
        </p>
      )}

      {!data && !error && (
        <div className="insight-loading" aria-label="Loading cited insights">
          <div className="skeleton" />
          <div className="skeleton" />
          <div className="skeleton" />
        </div>
      )}
    </div>
  )
}
