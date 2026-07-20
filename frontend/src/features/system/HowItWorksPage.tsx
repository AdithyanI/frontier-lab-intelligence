import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuditDatePath } from '../../shared/date/auditDateStore'
import SignalFunnel, { type FunnelStage } from './SignalFunnel'
import NetworkRankFigure from '../architecture/NetworkRankFigure'
import { CollectFigure, JudgeFigure, PublishFigure, RankFigure, SourceChoiceFigure, TrustedSetFigure } from './DecisionFigures'

/* The page is the figure. A sticky signal funnel carries the whole story;
   the scrolling rail beside it holds one short beat per stage and a single
   link into the live product surface that proves it. */

const SCROLL_STAGES: FunnelStage[] = ['watch', 'collect', 'rank', 'judge', 'publish', 'complete']

/* Step-by-step navigation: bring the next beat past the spy threshold,
   so the funnel camera plays the transition by itself. */
function scrollToBeat(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

/* Keyboard navigation for presenting: arrow keys (or j/k) step through the
   beats while the funnel is on screen. Past the funnel, keys scroll normally. */
function useBeatKeys(active: FunnelStage) {
  useEffect(() => {
    const order: FunnelStage[] = ['universe', ...SCROLL_STAGES]
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return
      const target = event.target as HTMLElement | null
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return
      if (document.querySelector('.how-figure-overlay')) return

      const canvas = document.querySelector('.how-canvas')
      if (!canvas) return
      const rect = canvas.getBoundingClientRect()
      if (rect.bottom < window.innerHeight * 0.6 || rect.top > window.innerHeight * 0.6) return

      const next = event.key === 'ArrowDown' || event.key === 'ArrowRight' || event.key === 'j'
      const prev = event.key === 'ArrowUp' || event.key === 'ArrowLeft' || event.key === 'k'
      if (!next && !prev) return

      const i = order.indexOf(active)
      const to = order[i + (next ? 1 : -1)]
      if (!to) return
      event.preventDefault()
      scrollToBeat(to)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [active])
}

/* Each beat links down to the chapter that explains the decision behind it. */
function WhyLink({ stage }: { stage: string }) {
  return (
    <button
      type="button"
      className="how-why"
      onClick={() =>
        document
          .getElementById(`why-${stage}`)
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    >
      Why this choice &darr;
    </button>
  )
}

/* Decision figures open fullscreen on click, so they can be presented
   and talked over. Esc or a click anywhere closes the overlay. */
function FigureFrame({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open])

  return (
    <>
      <button
        type="button"
        className="how-read-figure"
        onClick={() => setOpen(true)}
        aria-label="Expand figure to full screen"
      >
        {children}
        <span className="how-figure-expand mono" aria-hidden="true">expand &#x2921;</span>
      </button>
      {open && (
        <div
          className="how-figure-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Figure, full screen"
          onClick={() => setOpen(false)}
        >
          <span className="how-figure-close mono" aria-hidden="true">esc / click to close &times;</span>
          <div className="how-figure-overlay-inner">{children}</div>
        </div>
      )}
    </>
  )
}

function NextButton({ to }: { to: string }) {
  return (
    <button type="button" className="how-next mono" onClick={() => scrollToBeat(to)}>
      next &darr;
    </button>
  )
}

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
}

export default function HowItWorks() {
  const insightsPath = useAuditDatePath('/insights')
  const feedPath = useAuditDatePath('/evidence/feed')
  const artifactsPath = useAuditDatePath('/evidence/artifacts')
  const activeStage = useActiveStage()
  useBeatKeys(activeStage)

  /* Deep link: /how#writing jumps straight to the written chapters. */
  useEffect(() => {
    const hash = window.location.hash.replace('#', '')
    if (!hash) return
    const id = hash === 'writing' ? 'how-read-title' : hash
    requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ block: 'start' })
    })
  }, [])

  const beats: Beat[] = [
    {
      id: 'watch',
      step: '1',
      title: 'Choose',
      text: 'The system watches one source: X. Inside it, a screened network of frontier labs and the researchers who work there. Only what this trusted cohort posts gets collected.',
    },
    {
      id: 'collect',
      step: '2',
      title: 'Collect',
      text: 'Capture complete observed X days for the screened cohort. Replies, quotes, and threads are grouped into exact Events. Linked papers, repos, and model cards enter a separate artifact catalogue, and successful text snapshots are frozen.',
    },
    {
      id: 'rank',
      step: '3',
      title: 'Rank',
      text: 'A transparent attention score orders each day: who amplified it, who wrote it, how the public reacted. It decides where to look first, and never pretends to decide what is true.',
    },
    {
      id: 'judge',
      step: '4',
      title: 'Judge',
      text: 'Every Event is asked two independent questions. Does this change an investment position? Should an engineering team act on it? Each answer keeps its reasons attached.',
    },
    {
      id: 'publish',
      step: '5',
      title: 'Publish',
      text: 'An editorial agent reviews everything that survived and must surface or explicitly suppress each candidate. What remains becomes two audience-specific briefs, and every claim in them cites its source.',
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
              depends on, and attention is limited. So the system is a funnel:
              stage by stage it raises the signal-to-noise ratio, keeping the
              signal and dropping the noise, until one data source becomes two
              cited briefs.
            </p>
            <NextButton to="watch" />
            <p className="how-key-hint mono" aria-hidden="true">or use &uarr; &darr; arrow keys</p>
          </div>

          {beats.map((beat, i) => (
            <div className="how-beat" id={beat.id} key={beat.id}>
              <p className="how-beat-kicker mono">Stage {beat.step}</p>
              <h3>{beat.title}</h3>
              <p>{beat.text}</p>
              <WhyLink stage={beat.id} />
              <NextButton to={beats[i + 1]?.id ?? 'complete'} />
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
            words, one stage at a time, with the design choice behind each and
            the numbers from one real day: 17 July 2026, when 4,537 captured
            posts became 1,287 Events, 56 candidates worth judging, and 10
            cited Insights.
          </p>
          <p>
            The system works one day at a time. Every brief covers a single
            day of evidence, judged on its own, and every Insight belongs to
            a date. Rolling several days into one weekly digest can come
            later.
          </p>
        </header>

        <article className="how-read-block how-read-block--wide" id="why-watch">
          <h4><span className="mono">1</span> Choose: one source, and trust over popularity</h4>

          <p className="how-read-sub mono">1a · Where to look</p>
          <p>
            I chose X as the single source and went deep on it. My judgment:
            X is the front page of AI. Almost everything breaks there first.
            When a lab ships a model or a researcher publishes a paper, they
            announce it on X themselves, and the argument about whether it
            matters happens in the replies. The founders are in those replies
            too.
          </p>
          <p>
            There is a second reason. When news breaks, the artifact behind
            it, the model card, the blog post, the repo, is almost always
            linked in the post itself. So one source, read carefully, carries
            the announcement, the argument, and the primary document. One
            source done deeply beats six done shallowly, and the other source
            classes can plug into the same Registry later.
          </p>
          <FigureFrame>
            <SourceChoiceFigure />
          </FigureFrame>

          <p className="how-read-sub mono">1b · Collect the trusted set</p>
          <p>
            From everything on X, the system keeps a small set it trusts:
            frontier labs and the researchers who work there. I started from
            a seed list of people I already knew were signal, pulled who they
            follow, and let the set grow outward from there. Growing it meant
            screening a follow graph of 557,363 accounts and 2.8 million
            follow edges down to a Registry of 2,591 active identities: 2,431
            researchers and 160 organizations. Screening mixes simple gates
            with LLM judgment. Every admission keeps its provenance, and the
            39 rejections stay on the books with their reasons.
          </p>
          <FigureFrame>
            <TrustedSetFigure />
          </FigureFrame>

          <p className="how-read-sub mono">1c · Rank by trust, not popularity</p>
          <p>
            Within this network, the next call was whose word should carry
            more weight. Here is the human intuition. If ten people I know
            are good and authentic all follow and trust some other person,
            that person is very likely worth trusting too. Trust flows
            through the network. So the system ranks an account by how many
            entities inside the screened set follow it, never by raw
            follower count. A million followers measures reach, not trust.
          </p>
          <p>
            Two examples. Andrej Karpathy is
            the most followed account inside the Registry, which is exactly
            what you would expect. Elon Musk is one of the most popular
            accounts on the platform, but inside this network he is nowhere
            near the top. Popularity and trust are different measurements,
            and this system uses the second one. Organizations earn their
            place the same way: OpenAI and Anthropic bubble up because the
            researchers follow them, not because I ranked them by hand.
          </p>
          <FigureFrame>
            <NetworkRankFigure />
          </FigureFrame>
          <p>
            The thesis held up. Across the first 13 briefed days, Events by authors
            in the top half of the ranking became kept Insights at 12.2%,
            against 7.3% for the bottom half, and the judges never see the
            author&apos;s rank. An independent public ranking of AI accounts,
            frozen before the comparison, agrees with ours at a rank
            correlation of 0.877 across 872 shared accounts.
          </p>
          <p>
            <Link className="how-beat-link" to="/network/ranking">
              See the live ranking &rarr;
            </Link>
          </p>
        </article>

        <article className="how-read-block how-read-block--wide" id="why-collect">
          <h4><span className="mono">2</span> Collect: preserve before interpreting</h4>
          <p>
            The system collects whole days, one at a time. When a UTC day
            completes, everything the cohort posted in it is stored exactly
            as posted, before any interpretation.
          </p>
          <p>
            X has its idiosyncrasies: a post can be replied to, quoted, or
            reposted, and the same development ends up scattered across all
            of them. So the system merges the scatter into one exact Event
            per development, using only relationships the platform itself
            declares. There is no topic clustering at this stage because
            clustering is already an opinion, and this stage is not allowed
            to have one. The result is our own version of the feed: what the
            trusted network posted, plus what it engaged with.
          </p>
          <p>
            Linked artifacts go into a separate catalogue. When
            a lab announces a model and links the blog post, an adapter for
            that content type fetches the text and freezes a snapshot of it.
            Websites, papers, and X articles each have their own adapter.
            The frozen text is what later citation checks run against, and
            retrieval gaps stay visible instead of being treated as
            evidence. On 17 July this stage held 4,537 captured posts
            resolving into 1,287 exact Events.
          </p>
          <FigureFrame>
            <CollectFigure />
          </FigureFrame>
          <p>
            <Link className="how-beat-link" to={feedPath}>
              See the evidence &rarr;
            </Link>
          </p>
        </article>

        <article className="how-read-block how-read-block--wide" id="why-rank">
          <h4><span className="mono">3</span> Rank: order the day, do not judge it</h4>
          <p>
            A single day holds over a thousand Events, and nobody reads a
            thousand of anything. With an unlimited LLM budget I could judge
            them all. With a real one, the day needs an order: which Events
            get attention first. A transparent attention score provides it.
          </p>
          <p>
            Sorting by raw engagement gives the wrong order. Whatever Elon
            Musk posts floats to the top of that list, and it is rarely what
            an analyst or an engineer needs. So the score leans on the
            trusted network instead. When the Thinking Machines Lab model
            release landed, it rose to the top of its day because the
            researchers engaged with it, not because the public did.
          </p>
          <p>
            The weights are not hidden in code; the API response declares
            them. The score is deliberately simple, three parts:
          </p>
          <ul className="how-score-parts">
            <li>
              <span className="how-score-weight mono">55%</span>
              <span className="how-score-label">
                Amplification by the trusted network: how many Registry
                members quoted or reposted it
              </span>
            </li>
            <li>
              <span className="how-score-weight mono">25%</span>
              <span className="how-score-label">
                The author&apos;s own standing inside the network
              </span>
            </li>
            <li>
              <span className="how-score-weight mono">20%</span>
              <span className="how-score-label">
                Public engagement, as a tie-breaker only
              </span>
            </li>
          </ul>
          <p>
            The score does one job: it picks the top 100 Events of each day
            for judging, and the judges never see it. It decides where to
            look first, never what is true or what matters, because attention
            is evidence of noise as often as of signal. A quarter of the kept
            Insights came from the lower half of that window. I would rather
            defend a simple formula with known limits than a sophisticated one
            that pretends to measure importance.
          </p>
          <FigureFrame>
            <RankFigure />
          </FigureFrame>
          <p>
            <Link className="how-beat-link" to={feedPath}>
              See a ranked day &rarr;
            </Link>
          </p>
        </article>

        <article className="how-read-block how-read-block--wide" id="why-judge">
          <h4><span className="mono">4</span> Judge: two independent questions</h4>
          <p>
            An Event can top the attention ranking and still be useless to
            both readers. So each of the top 100 Events is asked two separate
            questions, by two independent LLM calls: does this change an
            investment position? Should an engineering team act on it? The
            two answers never mix. An Event can matter to both audiences, to
            one, or to neither, and each verdict comes back as a structured
            yes or no with its reasoning attached, readable on the Event
            itself.
          </p>
          <p>
            The declines tell the story best. One post that day was a joke
            about cancelled Claude subscriptions. Many in the trusted network
            engaged with it, so attention ranked it high, and both judges
            correctly turned it away: funny, but useless to an analyst and
            an engineer. That is the filter working.
          </p>
          <p>
            Only fresh first-party evidence counts here. A week-old post
            cannot be rescued by someone else reacting to it today. On 17
            July, 56 of the day&rsquo;s 1,287 Events crossed this bar for at
            least one audience.
          </p>
          <FigureFrame>
            <JudgeFigure />
          </FigureFrame>
          <p>
            <Link className="how-beat-link" to={feedPath}>
              See the routing &rarr;
            </Link>
          </p>
        </article>

        <article className="how-read-block how-read-block--wide" id="why-publish">
          <h4><span className="mono">5</span> Publish: surface it, or say why not</h4>
          <p>
            The last stage turns surviving evidence into the two daily
            briefs. An editorial agent, a small harness I built on the Codex
            app server, reads everything that survived and must do one of
            two things with each candidate: turn it into an Insight or
            decline it in writing. Nothing is dropped silently.
          </p>
          <p>
            The agent does not judge in a vacuum. It carries packaged
            context for each reader: for the investment brief, BIT
            Capital&apos;s publicly known holdings and what would move a
            position; for the engineering brief, what a production AI team
            can act on. That context is why the same Event can become two
            different Insights, or one, or none.
          </p>
          <p>
            Every claim in the final brief cites its source, and cited
            excerpts are checked verbatim against the frozen text before the
            brief is accepted. That check is the hallucination control: a
            quote that cannot be matched to preserved source text does not
            ship. The order of the brief is a written rationale, not a
            synthetic score.
          </p>
          <p>
            On 17 July, 56 Events reached the editorial run, each carrying a
            decision for every audience it qualified for: 84 decisions in all.
            The run kept 10 Insights, 7 for engineering and 3 for investment.
            The other decisions are written declines, each with its reason
            attached.
          </p>
          <p>
            A person starts each dated run, and its stages resume from saved
            checkpoints.
          </p>
          <FigureFrame>
            <PublishFigure />
          </FigureFrame>
          <p>
            <Link className="how-beat-link" to={insightsPath}>
              Read the brief &rarr;
            </Link>
          </p>
        </article>

        <article className="how-read-block how-read-block--wide" id="why-plumbing">
          <h4><span className="mono">6</span> The plumbing: models, costs, delivery</h4>
          <p>
            The stack is simple on purpose: a Python pipeline
            writing SQLite files, served by FastAPI and a built React app
            through a Cloudflare tunnel. The page you are reading runs on
            it. Every LLM call in the system goes through one shared LiteLLM
            gateway. That single choke point handles retries, backoff, and
            model fallback, and it prices every request. Cost is telemetry
            here: each run records exactly which model produced it, at what
            reasoning effort, and what it cost.
          </p>
          <p>
            Models are matched to the size of the job. Bounded structured
            work like screening and audience routing runs on small, fast
            models with prompt caching and structured schema output, so a
            full day of judging the top 100 Events costs well under a
            dollar. Measured, not estimated: the current Insight batch made
            947 surface-or-suppress decisions for $15.51, with 1.76 million
            tokens served from prompt cache. The editorial writing, where
            quality matters most, runs on a large reasoning
            model. The exact model and effort per task, and the reasoning
            behind each choice, live in
            the <Link to="/system/architecture">Architecture</Link> chapters.
          </p>
          <p>
            Reading the brief here is one option. Each completed day can
            also be downloaded as a PDF, sent to Slack, or sent by email
            with the PDF attached, all from the same canonical brief. Each
            send is a deliberate human action: the system prepares, a person
            decides.
          </p>
          <p>
            <Link className="how-beat-link" to={insightsPath}>
              Try the delivery options &rarr;
            </Link>
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
          <p>
            Follow one chain from that same day. The 17 July engineering brief
            warns that a model grading another model&apos;s answers is swayed
            by visible provider labels. Its citation quotes the arXiv paper on
            value leakage from the frozen snapshot, the citation names the
            exact Event, and the Event holds the original announcement thread
            with its captured metrics. That chain exists for every Insight in
            every brief.
          </p>
          <p>
            <Link
              className="how-beat-link"
              to="/insights?audience=ai_engineering&status=kept&date=2026-07-17"
            >
              Read the 17 July engineering brief &rarr;
            </Link>
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
          their design rationale, the evaluation approach for extraction and
          scoring, and the token and cost accounting per workflow. The{' '}
          <Link to="/system/architecture">Architecture</Link> chapters cover
          the same ground inside the product.
        </p>
      </section>
    </div>
  )
}
