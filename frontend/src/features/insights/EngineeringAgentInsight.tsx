import { Link } from 'react-router-dom'

import CopyEventId from '../../shared/components/CopyEventId'
import { decodeTextEntities } from '../../shared/textEntities'
import type {
  EngineeringAgentInsightsResponse,
  EngineeringAgentItem,
} from '../../shared/api/insights'

export function EngineeringAgentInsight({ item }: { item: EngineeringAgentItem }) {
  const titleId = `engineering-agent-${item.development_id}-title`
  const feedPath = `/evidence/feed?date=${item.day}&event_id=${encodeURIComponent(item.development_id)}`
  const artifacts = item.provenance?.artifacts ?? []
  const sourceLinkCount = 1 + (item.provenance?.original_post?.url ? 1 : 0) + artifacts.length
  return (
    <article
      className="insight-row engineering-agent-row"
      id={`engineering-agent-${item.development_id}`}
      tabIndex={-1}
      aria-labelledby={titleId}
    >
      <div className="insight-rank engineering-agent-rank mono">
        <Link to={feedPath}>
          <strong>#{item.daily_rank}</strong>
          <span>Feed rank ↗</span>
        </Link>
      </div>
      <div className="insight-body engineering-agent-body">
        <header className="insight-head engineering-agent-head">
          <h2 id={titleId}>{decodeTextEntities(item.headline)}</h2>
        </header>

        <section className="engineering-agent-opening">
          <h3 className="mono">What changed</h3>
          <p>{decodeTextEntities(item.what_changed)}</p>
        </section>

        {item.lands.length > 0 ? (
          <section className="engineering-agent-lands" aria-label="Where this lands">
            <header>
              <h3>Where this lands</h3>
            </header>
            <ol>
              {item.lands.map((landing) => (
                <li key={landing.surface_id}>
                  <Link
                    className="engineering-agent-surface"
                    to={`/bit-lens/aion?surface=${encodeURIComponent(landing.surface_id)}`}
                  >
                    <span className="engineering-agent-surface-id mono">
                      {landing.surface_id}
                    </span>
                    <span className="engineering-agent-surface-name">
                      {landing.surface_name}
                    </span>
                  </Link>
                  <p className="engineering-agent-why">
                    {decodeTextEntities(landing.why)}
                  </p>
                </li>
              ))}
            </ol>
          </section>
        ) : (
          <section className="engineering-agent-no-match">
            <h3>No surface cleared the bar</h3>
            <p>
              {decodeTextEntities(
                item.no_match_reason || 'No engineering-useful landing was established.',
              )}
            </p>
          </section>
        )}

        <details className="engineering-agent-sources">
          <summary>
            <span>Sources</span>
            <span className="mono">
              {sourceLinkCount} {sourceLinkCount === 1 ? 'link' : 'links'}
            </span>
          </summary>
          <nav className="engineering-agent-sources-body" aria-label="Evidence links">
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
                {artifacts.length === 1
                  ? 'Read source artifact ↗'
                  : `Read source artifact ${index + 1} ↗`}
              </a>
            ))}
            <CopyEventId eventId={item.development_id} label="Copy ID" />
          </nav>
        </details>
      </div>
    </article>
  )
}

export function EngineeringAgentYield({
  data,
}: {
  data: EngineeringAgentInsightsResponse
}) {
  const run = data.run
  if (!run) return null
  return (
    <p className="insight-yield">
      <span className="insight-yield-part">
        <strong>{run.surfaced_development_count}</strong> of {run.development_count}{' '}
        Developments surfaced
      </span>
      <span className="insight-yield-sep" aria-hidden="true">·</span>
      <span className="insight-yield-part">
        <strong>{run.surface_landing_count}</strong> surface landings
      </span>
    </p>
  )
}
