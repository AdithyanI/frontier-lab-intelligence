import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import litellmRequestLog from '../../assets/litellm-request-log.webp'
import { EvidenceInputMap } from '../architecture/ArchitecturePage'
import NetworkRankFigure from '../architecture/NetworkRankFigure'
import { CollectFigure, JudgeFigure, PublishFigure, RankFigure, RankLayersFigure, SourceChoiceFigure, TrustedSetFigure } from './DecisionFigures'
import { VIDEO_WALKTHROUGH_URL } from './howContent'

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

type HowNarrativeProps = {
  feedPath: string
  insightsPath: string
}

export default function HowNarrative({
  feedPath,
  insightsPath,
}: HowNarrativeProps) {
  return (
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
          <p>
            Sometimes several tracked accounts publish separate original posts
            about the same release. When those posts point to the same specific
            paper, model card, repository, or announcement on the same day, the
            system groups their exact Events into one Development. Every
            original post and Event ID remains visible underneath.
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
            tells us what was popular on X. Instead the rank asks the narrower
            question the network can actually answer: how many distinct trusted
            Registry entities authored an original post, quoted it, or
            reposted any source in this Development? Each entity counts once
            across the complete Development.
          </p>
          <p>
            Plenty of Developments tie on that count, so two further questions
            break ties: the average network position of those participants,
            then the strongest public interaction total on one source post.
            They stay as three separate questions rather than one weighted
            formula, so there is no weight to tune and no lane can quietly
            outvote another.
          </p>
          <FigureFrame label="Expand how the three questions decide the order">
            <RankLayersFigure />
          </FigureFrame>
          <p>
            This is where the Registry ranking becomes useful again. An
            announcement repeated by three trusted entities always ranks ahead
            of one repeated by two, even if those two sit higher in the
            network. Network position only decides between Developments with
            the same number of participants. It is a tie-aware percentile of
            entity-union support, so entities with equal support receive the
            same position.
          </p>
          <p>
            The rank only decides what we look at first. It does not say that
            a Development is true, important, or relevant. The top Developments move to
            the next step, where they are judged without seeing this rank.
          </p>
          <FigureFrame label="Expand how ranking orders a day">
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
          <h4><span className="mono">5</span> Write: connect each Development to actual companies</h4>
          <p>
            At this point we have a much smaller set of Developments that may
            matter. The ten highest-ranked ones with a positive investment
            route go to the company-aware Investment agent, one at a time.
          </p>
          <p>
            The agent screens all 37 companies in BIT's disclosed portfolio
            from a single compact card set. It can then open a full research
            memo on any of them &mdash; but the tool call requires it to state
            the mechanism, the affected operating driver, and why it needs the
            memo <em>before</em> the file opens. It has to commit to a claim
            first.
          </p>
          <p>
            Every memo it opens must end in one of two places: the company
            appears in the output, or the agent writes down why it was
            rejected. Validation fails the run otherwise. Nothing quietly
            disappears between the screen and the brief.
          </p>
          <p>
            The output is grouped by causal path, not by company. Each path
            carries the companies exposed through it, and for each one: the
            direction, the operating driver it touches, whether the scale can
            be stated honestly, and what would have to be true. Application
            code supplies every link. The model never writes a URL.
          </p>
          <p>
            A day publishes only when every requested rank succeeds. A partial
            run stays invisible rather than mixing prompt versions on one
            page.
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
          <h4><span className="mono">6</span> The models and cost</h4>
          <p>
            The daily path has one shared routing judgment, followed by a
            separate agent for each audience.
          </p>
          <p>
            Audience routing uses <code>gpt-5.6-luna</code> at medium effort.
            One structured call reads an Event and returns an independent
            decision for investment and AI engineering. Investment then uses{' '}
            <code>gpt-5.6-sol</code> at xhigh effort to screen the portfolio
            and open only justified company memos. AI Engineering uses the same
            model at high effort to map the Development to concrete technical
            decisions.
          </p>
          <div className="how-cost-table" role="table" aria-label="Models and measured cost">
            <div className="how-cost-row how-cost-head" role="row">
              <span role="columnheader">Step</span>
              <span role="columnheader">Model</span>
              <span role="columnheader">Cost record</span>
            </div>
            <div className="how-cost-row" role="row">
              <strong role="cell">Audience routing</strong>
              <span role="cell" className="mono">gpt-5.6-luna · medium</span>
              <span role="cell">recorded per request</span>
            </div>
            <div className="how-cost-row" role="row">
              <strong role="cell">Investment agent</strong>
              <span role="cell" className="mono">gpt-5.6-sol · xhigh</span>
              <span role="cell">attached to each saved run</span>
            </div>
            <div className="how-cost-row" role="row">
              <strong role="cell">AI Engineering agent</strong>
              <span role="cell" className="mono">gpt-5.6-sol · high</span>
              <span role="cell">attached to each saved run</span>
            </div>
          </div>
          <p className="how-cost-note">
            LiteLLM records the exact model, tokens, cache reuse, latency, and
            cost for each request. The agent traces keep the complete request
            and response before a result is imported.
          </p>
          <p>
            Audience-routing calls pass through LiteLLM. It handles retries
            and records the model, tokens, time, and cost for every request.
            The screenshot below is one real call.
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
            This request used 2,732 tokens, took 4.385 seconds, and cost
            $0.0033444. It is a real historical request, not a current price
            estimate; other requests vary with the model and evidence.
          </p>
          <p>
            <a className="how-beat-link" href="#technical-appendix">
              Open the technical appendix &rarr;
            </a>
          </p>
        </article>

        <article className="how-read-block how-read-block--wide" id="future-work">
          <h4>Future work</h4>
          <p className="how-read-sub mono">Give the network more time</p>
          <p>
            Today, the rank counts reactions that happen on the same calendar
            day as the original post. This keeps each daily rank stable, but a
            post published late has less time to be noticed.
          </p>
          <p>
            If this becomes a real problem, we can wait for a fixed period
            after every post before freezing the rank. A shorter wait gives us
            faster briefs. A longer wait gives the network more time. For now,
            I am keeping the simpler rule.
          </p>

          <p className="how-read-sub mono">
            Fold one story back together
          </p>
          <p>
            Two posts become one Development only when they point to the exact
            same link. That rule is deliberate. It means the system can never
            invent a connection between two things that merely look related.
          </p>
          <p>
            The cost appears when one event is covered widely. On 24 July,
            TIME, the Guardian and the Wall Street Journal each published their
            own article about the same OpenAI agent incident, so each one
            arrived as a separate Development and the brief carried four
            versions of a single story, pointing at the same companies.
          </p>
          <p>
            The fix belongs at the end rather than the start. Once a day&rsquo;s
            Insights are written, they can be compared and the repeats folded
            together. I would rather show a duplicate a reader can see than
            silently merge two stories that were never the same, so the
            grouping rule stays exact until that pass exists.
          </p>
        </article>

        <article className="how-read-block">
          <h4><span className="mono">&rarr;</span> The result</h4>
          <p>
            Each day ends with one brief for investment and one for AI
            engineering. Every Insight links back to the exact Event, the
            available frozen source, and the original post.
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
  )
}
