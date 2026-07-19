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
      text: 'Capture complete observed X days for the screened cohort. Replies, quotes, and threads are grouped into exact Events. Linked papers, repos, and model cards enter a separate artifact catalogue, and successful text snapshots are frozen.',
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
      text: 'An editorial agent reviews everything that survived and must surface or explicitly suppress each candidate. What remains becomes two audience-specific briefs, and every claim in them cites its source.',
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
      text: 'One brief per audience for each completed editorial day, investment and AI engineering, and every claim in them cites its source.',
      to: insightsPath,
      linkLabel: 'Insights',
    },
    {
      weight: '10%',
      name: 'Ingestion pipeline',
      text: 'Completed observed X days are preserved before interpretation. Linked primary documents are catalogued, and successful normalized text snapshots are frozen with retrieval gaps visible.',
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
      text: 'You are in it. The live product reads the published SQLite models produced by the same pipeline.',
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
          Frontier labs publish constantly. The system narrows that output
          through one inspectable funnel until only a cited brief for investors
          and one for AI engineers remain.
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

      <section className="how-read" aria-labelledby="how-read-title">
        <header className="how-read-head">
          <p className="how-beat-kicker mono">In writing</p>
          <h3 id="how-read-title">The same funnel, in words</h3>
          <p>
            The figure above is the whole system. Here is the same story in
            words, one stage at a time, with the design choice behind each.
          </p>
        </header>

        <article className="how-read-block">
          <h4><span className="mono">1</span> Choose: start with people, not keywords</h4>
          <p>
            Keyword alerts fail because the words arrive after the signal. The
            people come first. So the system starts with a screened Registry of
            frontier labs and the researchers inside them, not a list of search
            terms.
          </p>
          <p>
            The cohort also extends itself. Who these researchers follow
            reveals the layer below the obvious names, and that is often where
            the earliest signal lives. Every admission keeps its provenance,
            and a rejected identity disappears from every view without
            rewriting history.
          </p>
        </article>

        <article className="how-read-block">
          <h4><span className="mono">2</span> Collect: preserve before interpreting</h4>
          <p>
            For each completed observed UTC day, the cohort&rsquo;s captured X
            output is stored before interpretation. Replies, quotes, and threads
            are grouped into exact Events using only relationships the platform
            itself declares. There is no topic clustering at this stage because
            clustering is already an opinion, and this stage is not allowed to
            have one.
          </p>
          <p>
            Each linked paper, repo, or model card is catalogued. When retrieval
            succeeds, the normalized text is frozen for later citation checks.
            Retrieval gaps remain visible instead of being treated as evidence.
          </p>
        </article>

        <article className="how-read-block">
          <h4><span className="mono">3</span> Rank: order the day, do not judge it</h4>
          <p>
            A single day holds more Events than anyone reads. A transparent
            attention score orders them: who wrote it, who inside the cohort
            amplified it, how the public reacted. The formula is versioned and
            every input is inspectable per Event.
          </p>
          <p>
            The score deliberately stops there. It decides where to look
            first. It never decides what is true or what matters, because
            attention is evidence of noise as often as of signal.
          </p>
        </article>

        <article className="how-read-block">
          <h4><span className="mono">4</span> Judge: two independent questions</h4>
          <p>
            Every Event is asked two separate questions. Does this change an
            investment position? Should an engineering team act on it? The
            judgments never share an answer. An Event can matter to both
            audiences, to one, or to neither, and each verdict keeps its
            reasoning attached.
          </p>
          <p>
            Only fresh first-party evidence counts here. A week-old post
            cannot be rescued by someone else reacting to it today.
          </p>
        </article>

        <article className="how-read-block">
          <h4><span className="mono">5</span> Publish: surface it, or say why not</h4>
          <p>
            An editorial agent reads everything that survived and must do one
            of two things with each candidate: turn it into an Insight or
            explicitly decline it. Nothing is dropped silently. That forced
            disposition is what keeps the funnel honest.
          </p>
          <p>
            Every claim in the final brief cites its source, and citations to
            documents are checked against the frozen text before the brief is
            accepted. The order of the brief is a written rationale, not a
            synthetic score.
          </p>
          <p>
            Today an operator starts the dated run. Its stages resume from
            checkpoints, and delivery remains an explicit action.
          </p>
        </article>

        <article className="how-read-block">
          <h4><span className="mono">&rarr;</span> The result: nothing on trust</h4>
          <p>
            Each completed editorial day can publish one brief for investment
            and one for AI engineering. Every Insight traces back through the
            funnel to the exact Event, the available frozen document, and the
            original post. You never have to take the system&apos;s word for
            anything it says.
          </p>
        </article>
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
          The written deliverables travel with the repository: the
          architecture write-up with model choices per task, the prompts and
          their rationale, the evaluation approach, and the token and cost
          accounting per workflow.
        </p>
      </section>
    </div>
  )
}
