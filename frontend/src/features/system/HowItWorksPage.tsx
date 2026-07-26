import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuditDatePath } from '../../shared/date/auditDateStore'
import HowNarrative from './HowNarrative'
import HowStory from './HowStory'
import {
  SHOWCASE_INSIGHTS,
  VIDEO_WALKTHROUGH_URL,
  createReviewRubric,
} from './howContent'

export default function HowItWorks() {
  const insightsPath = useAuditDatePath('/insights')
  const feedPath = useAuditDatePath('/evidence/feed')
  const artifactsPath = useAuditDatePath('/evidence/artifacts')
  const rubric = createReviewRubric({ insightsPath, feedPath, artifactsPath })

  useEffect(() => {
    const hash = window.location.hash.replace('#', '')
    if (!hash) return
    const id = hash === 'writing' ? 'how-read-title' : hash
    requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ block: 'start' })
    })
  }, [])

  return (
    <div className="page how-page">
      <header className="how-lead">
        <h1 className="page-title" id="how-title">
          How the signal is found
        </h1>
        <p>
          Frontier labs publish constantly. The system narrows that output
          through one inspectable funnel until only a cited brief for investors
          and one for AI engineers remain.
        </p>
        <p>
          The fastest way to understand the system is the video walkthrough.
          It shows the moving parts this page can only describe.
        </p>
        <p>
          <a
            className="how-beat-link"
            href={VIDEO_WALKTHROUGH_URL}
            target="_blank"
            rel="noreferrer"
          >
            Watch the video walkthrough &rarr;
          </a>
        </p>
      </header>

      <HowStory insightsPath={insightsPath} />
      <HowNarrative
        feedPath={feedPath}
        insightsPath={insightsPath}
      />

      <section className="how-showcase" aria-labelledby="how-showcase-title">
        <h3 id="how-showcase-title">Five Insights I would hand to the teams</h3>
        <p>
          These are five examples from the daily briefs. Each link opens the
          exact Insight with its sources and reasoning.
        </p>
        <ol>
          {SHOWCASE_INSIGHTS.map((insight) => (
            <li key={insight.to}>
              <Link to={insight.to}>{insight.title}</Link>
              <span className="mono">{insight.meta}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="how-map" aria-labelledby="how-map-title">
        <header className="how-map-head">
          <p className="how-beat-kicker mono">For the reviewer</p>
          <h3 id="how-map-title">The assignment, point by point</h3>
          <p>
            Each requirement in the brief maps to a stage of the funnel and a
            live surface where it can be inspected.
          </p>
        </header>
        <ul className="how-map-list">
          {rubric.map((row) => (
            <li key={row.name}>
              <span className="how-map-weight mono">{row.weight}</span>
              <div className="how-map-body">
                <h4>{row.name}</h4>
                <p>{row.text}</p>
              </div>
              <Link className="how-map-link" to={row.to}>
                {row.linkLabel} &rarr;
              </Link>
            </li>
          ))}
        </ul>
        <p className="how-map-note">
          The <Link to="/system/architecture">Architecture</Link> page keeps
          the reviewer-facing technical map concise. The complete prompts,
          design rationale, evaluation notes, run telemetry, and cost records
          travel with the{' '}
          <a href="https://github.com/AdithyanI/frontier-lab-intelligence">
            repository
          </a>.
        </p>
      </section>
    </div>
  )
}
