import { Link } from 'react-router-dom'
import { useAuditDatePath } from '../../shared/date/auditDateStore'

export default function HowItWorks() {
  const insightsPath = useAuditDatePath('/insights')
  const feedPath = useAuditDatePath('/evidence/feed')
  const artifactsPath = useAuditDatePath('/evidence/artifacts')

  return (
    <section className="system-view how-page" aria-labelledby="how-title">
      <header className="how-lead">
        <div className="how-lead-copy">
          <h2 className="system-view-title" id="how-title">
            From public output to a decision-ready brief
          </h2>
          <p>
            BIT asked for a working system that tracks frontier labs and their
            key people, finds the few developments that matter, and explains
            what they mean to investors and AI engineers. This is how the
            current product answers that brief.
          </p>
        </div>
        <blockquote>
          <p>
            Did this surface something we would genuinely want to know, and did
            it keep the noise out?
          </p>
          <cite>The assignment&rsquo;s central test</cite>
        </blockquote>
      </header>

      <nav className="how-steps-nav" aria-label="How the system works">
        <a href="#watch"><span className="mono">1</span>Choose</a>
        <a href="#collect"><span className="mono">2</span>Collect</a>
        <a href="#rank"><span className="mono">3</span>Rank</a>
        <a href="#judge"><span className="mono">4</span>Judge</a>
        <a href="#publish"><span className="mono">5</span>Publish</a>
      </nav>

      <ol className="how-journey">
        <li className="how-step" id="watch">
          <div className="how-step-index">
            <span className="mono">1</span>
            <p>Registry</p>
          </div>
          <div className="how-step-body">
            <h3>Choose who is worth watching</h3>
            <p className="how-step-intro">
              The system starts with labs and people, not keywords. Labs are
              first-class entities alongside the researchers and engineers who
              work inside them. Each identity owns its known channels and a
              reasoned admission record.
            </p>
            <div className="how-step-detail">
              <div>
                <h4>How it works</h4>
                <p>
                  A screened Registry defines the trusted cohort. A frozen X
                  follow graph then shows which additional accounts several
                  members of that cohort pay attention to. That helps find the
                  useful layer below the obvious founders without treating
                  popularity as expertise.
                </p>
              </div>
              <div>
                <h4>Inspect it</h4>
                <p>
                  Start with <Link to="/network/ranking">Network ranking</Link>,
                  then open the <Link to="/network/registry">Registry</Link> to
                  inspect identities, channels, support, and recorded rejection
                  reasons. <Link to="/network/add-profile">Add Profile</Link>
                  shows the audited admission path.
                </p>
              </div>
            </div>
          </div>
        </li>

        <li className="how-step" id="collect">
          <div className="how-step-index">
            <span className="mono">2</span>
            <p>Ingestion and extraction</p>
          </div>
          <div className="how-step-body">
            <h3>Build one complete evidence day</h3>
            <p className="how-step-intro">
              The current scheduled source is X for the tracked cohort. The
              collector stores complete UTC days with the original text,
              relations, timestamps, metrics, and discovery provenance.
            </p>
            <div className="how-step-detail">
              <div>
                <h4>How it works</h4>
                <p>
                  Feed materialization keeps only complete collection days.
                  Events group exact replies, quotes, reposts, and first-party
                  threads, never vague topic similarity. When a first-party post
                  discloses a paper, repository, model card, blog post, or other
                  primary document, the Artifact library preserves that link and
                  its extracted text.
                </p>
              </div>
              <div>
                <h4>Inspect it</h4>
                <p>
                  The <Link to={feedPath}>Feed</Link> shows the dated evidence and
                  exact Event structure. <Link to={artifactsPath}>Artifacts</Link>
                  shows the linked primary documents, retrieval state, frozen
                  text, and the Feed Event that disclosed each source.
                </p>
              </div>
            </div>
          </div>
        </li>

        <li className="how-step" id="rank">
          <div className="how-step-index">
            <span className="mono">3</span>
            <p>Scoring</p>
          </div>
          <div className="how-step-body">
            <h3>Rank attention without calling it truth</h3>
            <p className="how-step-intro">
              Scoring decides where to look first. It does not decide whether a
              claim is true, important, or useful to either audience.
            </p>
            <div className="how-step-detail">
              <div>
                <h4>How it works</h4>
                <p>
                  Network support counts how many screened Registry entities
                  follow an account. The daily Attention score then combines
                  tracked amplification, author support, and public engagement.
                  Each component is measured within the same observed day, and
                  the complete formula remains visible.
                </p>
              </div>
              <div>
                <h4>Inspect it</h4>
                <p>
                  Open any rank in the <Link to={feedPath}>Feed</Link> to see its
                  score inputs and limitations. The technical definitions and
                  weights are kept in <Link to="/system/architecture#ranking-methods">Architecture</Link>.
                </p>
              </div>
            </div>
          </div>
        </li>

        <li className="how-step" id="judge">
          <div className="how-step-index">
            <span className="mono">4</span>
            <p>Signal and noise</p>
          </div>
          <div className="how-step-body">
            <h3>Ask two different questions of the same evidence</h3>
            <p className="how-step-intro">
              Each Event is judged independently for Investment and AI
              Engineering. It can matter to either audience, both, or neither.
              The evidence and citation rules stay shared while the prompts and
              decisions stay separate.
            </p>
            <div className="audience-questions" aria-label="Audience-specific questions">
              <div>
                <h4>Investment</h4>
                <p className="audience-question">What does this change for our positions and theses?</p>
                <p>
                  The output connects a lab development to public-company
                  exposure, a causal mechanism, confirmation and challenge
                  signals, and the next diligence step.
                </p>
              </div>
              <div>
                <h4>AI Engineering</h4>
                <p className="audience-question">What should we adopt, test, or investigate?</p>
                <p>
                  The output explains the technical relevance and proposes a
                  bounded next step with a measurable decision rule.
                </p>
              </div>
            </div>
            <p className="how-inline-link">
              The <Link to={feedPath}>Feed routing disclosure</Link> keeps both
              decisions and their reasons attached to the exact Event.
            </p>
          </div>
        </li>

        <li className="how-step" id="publish">
          <div className="how-step-index">
            <span className="mono">5</span>
            <p>Reports and alerts</p>
          </div>
          <div className="how-step-body">
            <h3>Publish only what clears the audience bar</h3>
            <p className="how-step-intro">
              The daily editorial agent reviews the complete routed-positive
              cohort. It must select an Event into an Insight or explicitly
              leave it out, so weak candidates cannot disappear without an
              accountable decision.
            </p>
            <div className="how-step-detail">
              <div>
                <h4>How it works</h4>
                <p>
                  Selected Insights are ranked by qualitative editorial
                  priority. Every citation is checked against frozen evidence
                  before the complete daily run is imported atomically. The same
                  canonical brief powers the web reader, PDF, Slack, and email.
                </p>
              </div>
              <div>
                <h4>Inspect it</h4>
                <p>
                  <Link to={insightsPath}>Insights</Link> is the finished product.
                  Read both audiences, open the rank rationale and source ledger,
                  download the PDF, or inspect the explicitly confirmed delivery
                  flow.
                </p>
              </div>
            </div>
          </div>
        </li>
      </ol>

      <section className="how-audit" aria-labelledby="audit-title">
        <div className="how-section-heading">
          <h3 id="audit-title">Verify one conclusion from end to end</h3>
          <p>Every reader-facing claim keeps a path back to the evidence that earned it.</p>
        </div>
        <ol className="audit-path">
          <li><span className="mono">1</span><strong>Read the Insight</strong><p>Start with the conclusion, interpretation, and audience action.</p></li>
          <li><span className="mono">2</span><strong>Open its sources</strong><p>The source ledger identifies every supporting Event and document.</p></li>
          <li><span className="mono">3</span><strong>Inspect the Event</strong><p>The exact Feed Event preserves rank, routing reasons, and source relations.</p></li>
          <li><span className="mono">4</span><strong>Reach the primary source</strong><p>Open the original post or the frozen Artifact text used by the citation.</p></li>
        </ol>
      </section>

      <section className="how-scope" aria-labelledby="scope-title">
        <div className="how-section-heading">
          <h3 id="scope-title">The current boundary</h3>
          <p>A narrow system that works is more useful than broad coverage it cannot defend.</p>
        </div>
        <div className="scope-columns">
          <div>
            <h4>Live in this submission</h4>
            <ul>
              <li>Public hosted product plus a one-command local reviewer release.</li>
              <li>Daily X evidence for the screened cohort and linked first-party documents.</li>
              <li>Registry discovery, transparent ranking, two-audience routing, and cited daily briefs.</li>
              <li>Web, PDF, and explicitly confirmed Slack and email delivery.</li>
            </ul>
          </div>
          <div>
            <h4>Next, not claimed</h4>
            <ul>
              <li>Unattended scheduling and a materiality policy for automatic alerts.</li>
              <li>Source-native recurring collectors for GitHub, arXiv, blogs, and conference video.</li>
              <li>A longer feedback loop that learns from stored human corrections.</li>
            </ul>
          </div>
        </div>
      </section>

      <footer className="how-next">
        <div>
          <h3>Start with the finished brief</h3>
          <p>Then move backward through its evidence, ranking, and source cohort.</p>
        </div>
        <div className="how-next-links">
          <Link className="how-primary-link" to={insightsPath}>Open Insights</Link>
          <Link to="/system/architecture">Technical architecture</Link>
          <Link to="/system/status">Current checkpoint</Link>
        </div>
      </footer>
    </section>
  )
}
