import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuditDatePath } from '../../shared/date/auditDateStore'
import HowNarrative from './HowNarrative'
import HowStory from './HowStory'
import {
  AccountIntake,
  ModelTable,
  SystemOverview,
} from '../architecture/ArchitecturePage'
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
    const revealHash = () => {
      const hash = window.location.hash.replace('#', '')
      if (!hash) return
      const id = hash === 'writing' ? 'how-read-title' : hash
      requestAnimationFrame(() => {
        const target = document.getElementById(id)
        if (target instanceof HTMLDetailsElement) target.open = true
        target?.scrollIntoView({ block: 'start' })
      })
    }

    revealHash()
    window.addEventListener('hashchange', revealHash)
    return () => window.removeEventListener('hashchange', revealHash)
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

      <nav className="how-contents" aria-label="On this page">
        <span className="mono">On this page</span>
        <a href="#universe">Visual walkthrough</a>
        <a href="#how-read-title">In words</a>
        <a href="#how-showcase-title">Example Insights</a>
        <a href="#how-map-title">Assignment map</a>
        <a href="#technical-appendix">Technical appendix</a>
      </nav>

      <HowStory insightsPath={insightsPath} />
      <HowNarrative
        feedPath={feedPath}
        insightsPath={insightsPath}
      />

      <section className="how-showcase" aria-labelledby="how-showcase-title">
        <h3 id="how-showcase-title">Six Insights I would hand to the teams</h3>
        <p>
          Three for the investment team, three for the engineering team. Each
          link opens the exact Insight with its sources and reasoning. The
          first two are the same Development, ranked first on the same day for
          both audiences, read two different ways.
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
          The complete prompts, design rationale, evaluation notes, run
          telemetry, and cost records travel with the{' '}
          <a href="https://github.com/AdithyanI/frontier-lab-intelligence">
            repository
          </a>.
        </p>
      </section>

      <details className="how-technical-appendix" id="technical-appendix">
        <summary>
          <span>
            <span className="how-beat-kicker mono">Appendix</span>
            <strong>Technical figures</strong>
          </span>
          <span className="mono">3 figures</span>
        </summary>
        <div className="how-technical-appendix-body">
          <section aria-labelledby="appendix-stack-title">
            <header>
              <h3 id="appendix-stack-title">The deployed system underneath it</h3>
              <p>
                One Python pipeline preserves evidence and model judgments in
                SQLite, then serves the same stored state through FastAPI and
                React.
              </p>
            </header>
            <div className="arch-canvas"><SystemOverview /></div>
          </section>

          <section aria-labelledby="appendix-models-title">
            <header>
              <h3 id="appendix-models-title">Current model boundaries</h3>
              <p>
                Every model call passes through the shared LiteLLM boundary;
                each audience keeps its own prompt, validation, and stored run.
              </p>
            </header>
            <div className="arch-canvas arch-canvas--methods"><ModelTable /></div>
          </section>

          <section aria-labelledby="appendix-intake-title">
            <header>
              <h3 id="appendix-intake-title">How an X account enters the Registry</h3>
              <p>
                A supplied profile is screened and resolved before collection,
                while every rejection keeps its reason.
              </p>
            </header>
            <div className="arch-canvas"><AccountIntake /></div>
          </section>
        </div>
      </details>
    </div>
  )
}
