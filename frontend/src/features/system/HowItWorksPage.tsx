import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import litellmRequestLog from '../../assets/litellm-request-log.webp'
import { useAuditDatePath } from '../../shared/date/auditDateStore'
import SignalFunnel, { type FunnelStage } from './SignalFunnel'
import {
  EvidenceInputMap,
  ModelTable,
} from '../architecture/ArchitecturePage'
import NetworkRankFigure from '../architecture/NetworkRankFigure'
import { CollectFigure, JudgeFigure, PublishFigure, RankFigure, SourceChoiceFigure, TrustedSetFigure } from './DecisionFigures'

/* The page is the figure. A sticky signal funnel carries the whole story;
   the scrolling rail beside it holds one short beat per stage and a single
   link into the live product surface that proves it. */

const SCROLL_STAGES: FunnelStage[] = ['watch', 'collect', 'rank', 'judge', 'publish', 'complete']
const VIDEO_WALKTHROUGH_URL = 'https://share.descript.com/view/LZkpHP29yub'

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
function FigureFrame({
  children,
  label = 'Expand figure to full screen',
}: {
  children: ReactNode
  label?: string
}) {
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
        aria-label={label}
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

const UNIT_COSTS = [
  {
    workflow: 'Audience routing',
    unit: 'one Event, two judgments',
    cost: '$0.00388 average',
  },
]

const DAILY_RUN_STEPS = [
  {
    id: '01',
    label: 'Evidence',
    title: 'Refresh the dated evidence state',
    text: 'Collect the new day, then materialize the exact Feed, Events, artifacts, and attention order.',
  },
  {
    id: '02',
    label: 'Route',
    title: 'Classify the top Events',
    text: 'One structured gpt-5.4-mini call returns separate Investment and AI Engineering judgments.',
  },
  {
    id: '03',
    label: 'Freeze',
    title: 'Prepare one immutable workspace',
    text: 'Keep the union-positive cohort, apply the seven-day first-party window, and bind every source hash.',
  },
  {
    id: '04',
    label: 'Codex',
    title: 'Research and write both briefs',
    text: 'One persisted gpt-5.6-sol task reviews the whole cohort, resolves gaps, consolidates, selects, and writes.',
  },
  {
    id: '05',
    label: 'Publish',
    title: 'Validate and import atomically',
    text: 'Every candidate is included or declined, every citation is checked, and the completed run becomes the reader.',
  },
]

function DailyRunFigure() {
  return (
    <figure className="how-daily-run" aria-labelledby="how-daily-run-title">
      <figcaption id="how-daily-run-title">
        One date, one resumable run
      </figcaption>
      <ol>
        {DAILY_RUN_STEPS.map((step, index) => (
          <li key={step.id} className={index === 2 ? 'how-run-step how-run-step--checkpoint' : 'how-run-step'}>
            <span className="how-run-step-id mono">{step.id} · {step.label}</span>
            <strong>{step.title}</strong>
            <p>{step.text}</p>
            {index === 2 && (
              <span className="how-run-handoff mono">
                add --launch-codex to continue →
              </span>
            )}
          </li>
        ))}
      </ol>
    </figure>
  )
}

const SHOWCASE_INSIGHTS = [
  {
    title: 'Anthropic gives TeraWulf a long lease; execution decides its value',
    meta: '6 July · Investment',
    to: '/insights?audience=investment&status=kept&date=2026-07-06&insight=3f8ecb8de3fb7bf34d3756474ba502a43a724593e37862d72163222f3fc48065',
  },
  {
    title: 'ChatGPT Work puts the agent interface above Microsoft and Google',
    meta: '9 July · Investment',
    to: '/insights?audience=investment&status=kept&date=2026-07-09&insight=18f69c9ac6e3d5e8a0c2c737973284580978dd81c3121c755da07ff88727a9f4',
  },
  {
    title: "Claude demand strengthens Amazon's capacity exposure",
    meta: '18 July · Investment',
    to: '/insights?audience=investment&status=kept&date=2026-07-18&insight=9dee6e36371b150c60e9821006f2ece26cc60c7891cb59bd933e6a76f9d7a793',
  },
  {
    title: 'FrontierFinance gives Aion a realistic evaluation target',
    meta: '9 July · AI Engineering',
    to: '/insights?audience=ai_engineering&status=kept&date=2026-07-09&insight=70a81026bd8bd1c43afb31e11451d5ab5cc66064b529274719f9ab1479923243',
  },
  {
    title: 'Retention controls do not prove what a coding agent transmits',
    meta: '13 July · AI Engineering',
    to: '/insights?audience=ai_engineering&status=kept&date=2026-07-13&insight=b2d9973fc22c09df7c132c5f79309a612c7abed40a633a661ce4199bdeff926e',
  },
]

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
      text: 'A transparent attention score orders each day: who amplified it, who wrote it, how the public reacted. It only decides where to look first; the judging comes later.',
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
            </div>
          </div>
        </div>
      </div>

      <section className="how-read" aria-labelledby="how-read-title">
        <header className="how-read-head">
          <p className="how-beat-kicker mono">In writing</p>
          <h3 id="how-read-title">The same funnel, in words</h3>
          <p>
            The easiest way to understand the system is the{' '}
            <a href={VIDEO_WALKTHROUGH_URL} target="_blank" rel="noreferrer">
              video walkthrough
            </a>
            , and I recommend starting there. But if you prefer reading, I’ll
            explain the same funnel below, step by step, with the visuals and
            the reasoning behind each choice.
          </p>
          <div className="how-overview">
            <p>
              Here is the whole system at a glance. I’ll walk through each part
              step by step below.
            </p>
            <FigureFrame label="Expand the complete daily intelligence flow">
              <EvidenceInputMap includeDailyOutcome />
            </FigureFrame>
          </div>
          <p>
            The system works one day at a time. Every brief covers a single
            day of evidence, judged on its own, and every Insight belongs to
            a date. Rolling several days into one weekly digest can come
            later.
          </p>
        </header>

        <article className="how-read-block how-read-block--wide" id="why-watch">
          <h4><span className="mono">1</span> Choose: one source, and trust over popularity</h4>

          <p>
            Before collecting anything, I had to make two choices: where to
            look, and who to listen to once I got there. I chose X as the
            source, then built a trusted network of labs and researchers
            inside it.
          </p>

          <p className="how-read-sub mono">1a · Where to look</p>
          <p>
            There is a huge amount of public information about AI. I chose to
            focus on X for two reasons.
          </p>
          <p>
            First, my judgment is that X is the front page of AI. New models,
            papers, funding announcements, and system cards often appear there
            first. Researchers, founders, and labs also speak there directly,
            so we get both the announcement and the discussion around it.
          </p>
          <p>
            Second, the post usually links to the primary artifact behind the
            announcement: the paper, model card, blog post, or GitHub
            repository. We can start from X and still collect the documents
            needed to understand what actually happened.
          </p>
          <p>
            I chose to do one source properly instead of spreading the project
            across six. We can add other sources to the same Registry later.
          </p>
          <FigureFrame>
            <SourceChoiceFigure />
          </FigureFrame>

          <p className="how-read-sub mono">1b · Decide who to follow</p>
          <p>
            Now that I had chosen X, the next question was who to follow. The
            answer could not be everyone. I started with a small set of AI
            researchers and labs whose work I already trusted, then looked at
            who they followed.
          </p>
          <p>
            The intuition is simple. If many people in that trusted group
            independently follow the same account, that account is probably
            worth looking at too. This lets the network discover researchers
            and organizations beyond the obvious names.
          </p>
          <p>
            Before an account enters the Registry, the system screens it. Some
            checks are simple, such as whether the profile is public and can be
            collected. An LLM helps with questions that need more context, such
            as whether the account belongs to a person or an organization. If
            an account is rejected, the reason is kept.
          </p>
          <FigureFrame>
            <TrustedSetFigure />
          </FigureFrame>
          <p>
            <Link className="how-beat-link" to="/network/registry">
              See the exact people and organizations in the live Registry &rarr;
            </Link>
          </p>

          <p className="how-read-sub mono">1c · Rank by trust, not popularity</p>
          <p>
            Once the network is built, we still need to decide whose posts
            deserve more attention. I did not want to use public follower
            count. A large audience tells us that someone is popular, not that
            AI insiders trust their work.
          </p>
          <p>
            Instead, the system asks how many people and labs inside the
            screened Registry follow each account. If many people I already
            trust independently follow the same researcher, that researcher is
            probably worth listening to. That is the ranking.
          </p>
          <p>
            Nobody is placed at the top by hand. People such as Andrej
            Karpathy, and organizations such as OpenAI and Anthropic, rise
            naturally because the network follows them. Elon Musk is extremely
            popular on X, but he ranks much lower inside this AI-specific
            network.
          </p>
          <FigureFrame>
            <NetworkRankFigure />
          </FigureFrame>
          <p>
            <Link className="how-beat-link" to="/network/ranking">
              Explore the live Network ranking &rarr;
            </Link>
          </p>
        </article>

        <article className="how-read-block how-read-block--wide" id="why-collect">
          <h4><span className="mono">2</span> Collect: keep the evidence together</h4>
          <p>
            Now we know which accounts to follow. The next step is to collect
            what they publish.
          </p>
          <p>
            X is not a clean list of announcements. The same development can
            appear as the original post, a reply, a quote, or a repost. If we
            treated each of those as a separate item, the same story would
            appear several times.
          </p>
          <p>
            So the system follows the relationships that X already provides.
            A post and the replies, quotes, or reposts connected to it become
            one exact Event. It does not merge unrelated posts just because
            they happen to discuss the same topic.
          </p>
          <p>
            The post often links to the more useful source behind the
            announcement: a paper, model card, blog post, GitHub repository,
            or X article. The system collects that source, freezes a text copy,
            and attaches it to the same Event. Later, if an Insight cites the
            source, we can check it against the exact text that was collected.
            Any retrieval gaps stay visible instead of being treated as
            evidence.
          </p>
          <FigureFrame>
            <CollectFigure />
          </FigureFrame>
          <p>
            <Link className="how-beat-link" to={feedPath}>
              See the live Evidence feed &rarr;
            </Link>
          </p>
        </article>

        <article className="how-read-block how-read-block--wide" id="why-rank">
          <h4><span className="mono">3</span> Rank: decide what to look at first</h4>
          <p>
            By now, one day can contain a long list of Events. We cannot read
            every one or send all of them through the more expensive judging
            step, so we need a sensible place to start.
          </p>
          <p>
            A normal engagement ranking is not very useful here. It mostly
            tells us what was popular on X. Instead, the attention score asks
            three simple things: who posted it, how much the trusted network
            engaged with it, and then how much attention it received more
            broadly.
          </p>
          <p>
            This is where the Registry ranking becomes useful again. An
            announcement from a lab the network trusts, repeated by several
            trusted researchers, should be looked at before a generally
            popular post. That is how the Thinking Machines Lab model release
            naturally rose to the top of its day.
          </p>
          <p>
            The score only decides what we look at first. It does not say that
            an Event is true, important, or relevant. The top Events move to
            the next step, where they are judged without seeing this score.
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
          <h4><span className="mono">4</span> Judge: useful for whom?</h4>
          <p>
            Something can rank highly and still not be useful to either
            reader. So each Event is now asked two separate questions. Could
            this change an investment position? And is there something here
            that an engineering team should act on?
          </p>
          <p>
            One structured call produces two independent audience decisions.
            Each answer is a yes or no with a reason, and neither answer
            affects the other. An Event can be useful to both audiences, to
            one, or to neither. You can read both decisions on the Event
            itself.
          </p>
          <p>
            A good example is a joke about cancelled Claude subscriptions.
            Many people in the trusted network engaged with it, so it ranked
            highly. But it was not useful to an investor or an engineer, and
            both decisions said no.
          </p>
          <p>
            The decision uses what was actually published that day, together
            with any first-party source attached to it. An old announcement
            does not become fresh evidence just because somebody reacts to it
            today.
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
          <h4><span className="mono">5</span> Write: turn the useful Events into two briefs</h4>
          <p>
            At this point we have a much smaller set of Events that may matter.
            I give all of them, along with their sources and audience
            decisions, to the FLI daily-intelligence agent.
          </p>
          <p>
            The agent has separate context for the two readers: what may
            matter to an investment position, and what a production AI team
            can actually use. It reviews the Events together, combines
            overlapping developments, and decides what belongs in each brief.
          </p>
          <p>
            Every candidate must end in one of two places: it becomes an
            Insight, or the agent writes down why it was declined. Nothing
            quietly disappears between the filter and the final brief.
          </p>
          <p>
            For every Insight it keeps, the agent explains what happened, why
            it matters to that reader, and what they may want to look at next.
            It also links back to the posts and source artifacts it used.
            Every cited excerpt is checked against the frozen source text. If
            it cannot be matched, it does not ship.
          </p>
          <p>
            The result is two daily briefs: one for investment and one for AI
            engineering. A person starts each dated run, and the system can
            resume from its saved checkpoints if anything stops along the way.
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
            The system uses a Python pipeline writing to SQLite, with FastAPI
            and React serving the product through a Cloudflare tunnel. The
            page you are reading runs on it. Pipeline API calls go through one
            shared LiteLLM gateway, which handles retries, backoff, fallback,
            and request-level cost telemetry. Final brief authoring runs as a
            persisted task through Codex App Server.
          </p>
          <p>
            The daily intelligence path has two model stages. First, one small,
            structured call classifies each top-ranked Event for both
            audiences. Then the FLI daily-intelligence agent reviews the
            complete routed cohort. It researches missing links, consolidates
            overlapping Events, selects what matters, and writes both final
            briefs.
          </p>
          <pre className="how-run-command" aria-label="Daily intelligence command"><code>$ .venv/bin/fli daily-intelligence run-day --day YYYY-MM-DD --json --no-input</code></pre>
          <p className="how-cost-note">
            As written, the command stops after freezing the workspace. Add{' '}
            <code>--launch-codex</code> to create or resume the one persisted
            editorial task and continue through validation, import, and final
            inspection. Every completed stage is checkpointed, so the same date
            resumes instead of starting a second run.
          </p>
          <DailyRunFigure />
          <div className="how-model-table">
            <ModelTable tasks={['Audience routing', 'FLI daily-intelligence agent']} />
          </div>
          <p>
            The LiteLLM-backed routing stage records cost at the decision
            boundary:
          </p>
          <div className="how-cost-table" role="table" aria-label="Measured model cost per decision">
            <div className="how-cost-row how-cost-head" role="row">
              <span role="columnheader">Workflow</span>
              <span role="columnheader">Measured unit</span>
              <span role="columnheader">Cost</span>
            </div>
            {UNIT_COSTS.map((row) => (
              <div className="how-cost-row" role="row" key={row.workflow}>
                <strong role="cell">{row.workflow}</strong>
                <span role="cell">{row.unit}</span>
                <span role="cell" className="mono">{row.cost}</span>
              </div>
            ))}
          </div>
          <p className="how-cost-note">
            The routing average comes from 99 new Event calls for 19 July. Each
            call returned both audience judgments.
          </p>
          <p className="how-cost-note">
            The FLI daily-intelligence agent runs through Codex App Server. Its
            effective model, reasoning effort, service tier, thread, and
            resulting brief remain attached to the editorial run rather than
            being mixed into these LiteLLM unit prices.
          </p>
          <p>
            Every request is tagged with the app, pipeline, job, scope, prompt
            version, and run identity. LiteLLM keeps the request and response,
            model, tokens, cache state, latency, and cost together. I used
            those logs to compare prompts and reasoning effort, then kept the
            cheaper path only when the result held up.
          </p>
          <FigureFrame label="Expand the LiteLLM request log screenshot">
            <img
              src={litellmRequestLog}
              alt="LiteLLM request log for a Frontier Lab Intelligence audience-routing call, showing its tags, 2,732 tokens, 4.385-second duration, and $0.0033444 cost."
              loading="lazy"
              decoding="async"
            />
          </FigureFrame>
          <p className="how-cost-note">
            One 19 July routing call: 2,732 tokens, 4.385 seconds, and
            $0.0033444. It is one measured request; real requests vary with
            input size and cache state.
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
          <h4><span className="mono">&rarr;</span> The result: every claim can be checked</h4>
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

      <section className="how-final" aria-labelledby="how-final-title">
        <header className="how-final-head">
          <p className="how-beat-kicker mono">Final report</p>
          <h3 id="how-final-title">What works, what I learned, and what comes next</h3>
          <p>
            The case-study proof is the working path from public evidence to
            two audience-specific, cited briefs. The complete corpus remains
            open for audit; these are the conclusions I would carry into the
            next version.
          </p>
        </header>

        <div className="how-final-rows">
          <article>
            <h4>What works</h4>
            <p>
              The same evidence core has produced an Investment brief and an
              AI Engineering brief for every completed day from 5 to 19 July.
              Every selected claim traces back to an exact Event and its
              available primary source. The brief can be read here, exported
              as a PDF, or deliberately sent to Slack or email.
            </p>
          </article>
          <article>
            <h4>What I learned</h4>
            <p>
              Network trust is useful for deciding where to look, but it
              should never become a truth score. Exact structural grouping
              keeps provenance cleaner than early semantic clustering. And a
              smaller model is the right choice only after checking that it
              preserves the decisions that matter.
            </p>
          </article>
          <article>
            <h4>What I would build next</h4>
            <p>
              First, route ranks 101 to 200 on several busy days to measure
              recall below the top-100 gate. Then add cross-day story memory so
              recurring themes must contain a real change. Only after measuring
              what X misses would I add independent RSS, GitHub, or arXiv
              discovery and unattended scheduling.
            </p>
          </article>
        </div>

        <div className="how-showcase">
          <h4>Five Insights I would hand to the teams</h4>
          <p>
            These are the small proof set, selected for evidence quality,
            audience consequence, and variety. Each link opens the exact
            Insight in the live reader.
          </p>
          <ol>
            {SHOWCASE_INSIGHTS.map((insight) => (
              <li key={insight.to}>
                <Link to={insight.to}>{insight.title}</Link>
                <span className="mono">{insight.meta}</span>
              </li>
            ))}
          </ol>
        </div>
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
