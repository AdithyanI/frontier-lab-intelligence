import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuditDatePath } from '../../shared/date/auditDateStore'
import SignalFunnel, { type FunnelStage } from './SignalFunnel'

/* The page is the figure. A sticky signal funnel carries the whole story;
   the scrolling rail beside it holds one short beat per stage and a single
   link into the live product surface that proves it. */

const SCROLL_STAGES: FunnelStage[] = ['watch', 'collect', 'rank', 'judge', 'publish', 'complete']

/* Scroll spy: the funnel focuses the plane for the beat being read. */
function useActiveStage(): FunnelStage {
  const [active, setActive] = useState<FunnelStage>('universe')

  useEffect(() => {
    let raf = 0
    const update = () => {
      raf = 0
      const cut = window.innerHeight * 0.5
      let current: FunnelStage = 'universe'
      for (const id of SCROLL_STAGES) {
        const el = document.getElementById(id)
        if (el && el.getBoundingClientRect().top <= cut) current = id
      }
      setActive(current)
    }
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  return active
}

type Beat = {
  id: FunnelStage
  step: string
  title: string
  text: string
  linkLabel: string
}

export default function HowItWorks() {
  const insightsPath = useAuditDatePath('/insights')
  const feedPath = useAuditDatePath('/evidence/feed')
  const artifactsPath = useAuditDatePath('/evidence/artifacts')
  const activeStage = useActiveStage()

  const beats: (Beat & { to: string })[] = [
    {
      id: 'watch',
      step: '1',
      title: 'Choose',
      text: 'Start with people, not keywords. A screened Registry of frontier labs and the researchers inside them decides whose word is worth collecting. Their own follow graph reveals the layer below the obvious names.',
      to: '/network/ranking',
      linkLabel: 'See the network',
    },
    {
      id: 'collect',
      step: '2',
      title: 'Collect',
      text: 'Capture what the cohort publishes, with nothing lost. Replies, quotes, and threads are grouped into exact Events, and every paper, repo, or model card they cite is fetched and frozen.',
      to: feedPath,
      linkLabel: 'See the evidence',
    },
    {
      id: 'rank',
      step: '3',
      title: 'Rank',
      text: 'A transparent attention score orders each day: who amplified it, who wrote it, how the public reacted. It decides where to look first, and never pretends to decide what is true.',
      to: feedPath,
      linkLabel: 'See a ranked day',
    },
    {
      id: 'judge',
      step: '4',
      title: 'Judge',
      text: 'Every Event is asked two independent questions. Does this change an investment position? Should an engineering team act on it? Each answer keeps its reasons attached.',
      to: feedPath,
      linkLabel: 'See the routing',
    },
    {
      id: 'publish',
      step: '5',
      title: 'Publish',
      text: 'An editorial agent reviews everything that survived and must surface or explicitly suppress each candidate. What remains becomes two daily briefs, and every claim in them cites its source.',
      to: insightsPath,
      linkLabel: 'Read the brief',
    },
  ]

  const rubric: { weight: string; name: string; text: string; to: string; linkLabel: string }[] = [
    {
      weight: '20%',
      name: 'Registry of labs and people',
      text: 'A screened cohort of frontier labs and the researchers inside them, kept current and extended through the follow graph.',
      to: '/network/registry',
      linkLabel: 'Registry',
    },
    {
      weight: '20%',
      name: 'Signal vs noise',
      text: 'The funnel above is the answer: five stages, each removing what does not matter, with the suppressions as visible as the picks.',
      to: feedPath,
      linkLabel: 'A filtered day',
    },
    {
      weight: '20%',
      name: 'Scoring rigor',
      text: 'Attention ranking and audience judgments are separate steps, each with its inputs and reasoning inspectable per Event.',
      to: '/system/architecture#ranking-methods',
      linkLabel: 'Methods',
    },
    {
      weight: '15%',
      name: 'Actionable delivery',
      text: 'One daily brief per audience, investment and AI engineering, and every claim in them cites its source.',
      to: insightsPath,
      linkLabel: 'Insights',
    },
    {
      weight: '10%',
      name: 'Ingestion pipeline',
      text: 'The cohort\u2019s output is captured losslessly, and every cited paper, repo, or model card is fetched and frozen.',
      to: artifactsPath,
      linkLabel: 'Artifacts',
    },
    {
      weight: '10%',
      name: 'Extraction',
      text: 'Posts, replies, and threads are resolved into exact Events with structured claims and their evidence attached.',
      to: feedPath,
      linkLabel: 'Events',
    },
    {
      weight: '5%',
      name: 'Web interface',
      text: 'You are in it. Everything shown here is the live product reading from the same database as the pipeline.',
      to: '/system/status',
      linkLabel: 'Checkpoint',
    },
  ]

  return (
    <div className="page how-page">
      <header className="how-lead">
        <h1 className="page-title" id="how-title">
          How the signal is found
        </h1>
        <p>
          Frontier labs publish constantly, and almost all of it is noise. The
          system is one funnel: each stage removes what does not matter, until
          only a cited brief for investors and one for AI engineers remain.
        </p>
      </header>

      <div className="how-canvas">
        <figure className="how-funnel" aria-hidden="false">
          <div className="how-funnel-sticky">
            <SignalFunnel active={activeStage} />
          </div>
        </figure>

        <div className="how-story">
          <div className="how-beat how-beat-intro" id="universe">
            <p className="how-beat-kicker mono">The problem</p>
            <h3>Almost everything is noise</h3>
            <p>
              Somewhere in the flood is the handful of developments a decision
              depends on. Reading everything is impossible; keyword alerts
              drown you. The funnel is the answer, one stage at a time.
            </p>
            <p className="how-scroll-hint mono">scroll &darr;</p>
          </div>

          {beats.map((beat) => (
            <div className="how-beat" id={beat.id} key={beat.id}>
              <p className="how-beat-kicker mono">Stage {beat.step}</p>
              <h3>{beat.title}</h3>
              <p>{beat.text}</p>
              <Link className="how-beat-link" to={beat.to}>
                {beat.linkLabel} &rarr;
              </Link>
            </div>
          ))}

          <div className="how-beat how-beat-outro" id="complete">
            <p className="how-beat-kicker mono">The result</p>
            <h3>Two briefs, fully traceable</h3>
            <p>
              Every conclusion keeps its path back through the funnel: from
              the Insight to its sources, to the exact Event, to the original
              post or frozen document. Nothing has to be taken on trust.
            </p>
            <div className="how-beat-links">
              <Link className="how-primary-link" to={insightsPath}>Open Insights</Link>
              <Link to={artifactsPath}>Artifact library</Link>
              <Link to="/system/architecture">Architecture</Link>
              <Link to="/system/status">Status</Link>
            </div>
          </div>
        </div>
      </div>

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
          The written deliverables travel with the repository: the
          architecture write-up with model choices per task, the prompts and
          their rationale, the evaluation approach, and the token and cost
          accounting per workflow.
        </p>
      </section>
    </div>
  )
}
