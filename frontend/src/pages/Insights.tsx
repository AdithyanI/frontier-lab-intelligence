import { useEffect, useState } from 'react'
import { getCachedJSON, type InsightItem, type InsightsResponse } from '../api'

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
  const [data, setData] = useState<InsightsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    getCachedJSON<InsightsResponse>('/api/insights')
      .then((payload) => {
        if (live) setData(payload)
      })
      .catch(() => {
        if (live) setError('Couldn’t load cited insights. Reload to try again.')
      })
    return () => {
      live = false
    }
  }, [])

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
            <span>{insightDay.format(new Date(`${run.day}T00:00:00Z`))}</span>
            <span>{run.model}</span>
            <span>{run.prompt_version}</span>
          </p>
        )}
      </header>

      {error && <p className="insight-message mono">{error}</p>}
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
