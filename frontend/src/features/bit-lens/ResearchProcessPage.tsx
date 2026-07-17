import { sources } from './bitLensData'

function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {children} <span aria-hidden="true">↗</span>
    </a>
  )
}

function ResearchGrammarMap() {
  const stages = [
    { x: 28, label: 'THESIS', question: 'What structural change is mispriced?', detail: 'Form the qualitative company view first.' },
    { x: 298, label: 'EDGE', question: 'Why can BIT know earlier?', detail: 'Domain work, models and company-specific data.' },
    { x: 568, label: 'SIGNAL', question: 'What can confirm or falsify it?', detail: 'KPIs, digital traces and leading indicators.' },
    { x: 838, label: 'KEY MOVE', question: 'What changes in the portfolio?', detail: 'Timing, weight, watchlist or thesis review.' },
  ]
  return (
    <svg
      viewBox="0 0 1110 268"
      role="img"
      aria-label="BIT's public thesis grammar moves from Thesis to Edge to Signal to Key Move. The thesis states the mispriced structural change. Edge explains why BIT can know earlier. Signal defines confirmation and falsification. Key Move describes timing, weight, watchlist, or thesis review."
    >
      <defs>
        <marker id="research-grammar-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0 L8,4 L0,8 z" fill="#4391b4" />
        </marker>
      </defs>
      <text x="28" y="30" className="lens-svg-kicker">BIT’S PUBLIC THESIS GRAMMAR</text>
      {stages.map((stage, index) => {
        const dark = index === 3
        return (
          <g key={stage.label}>
            <rect x={stage.x} y="60" width="234" height="150" fill={dark ? '#151515' : index === 0 ? '#edf6fa' : '#fff'} stroke={dark ? '#151515' : '#4391b4'} strokeWidth="1.2" />
            <text x={stage.x + 18} y="89" className={dark ? 'lens-svg-label lens-svg-label--dark' : 'lens-svg-label'}>{stage.label}</text>
            <text x={stage.x + 18} y="121" className={dark ? 'lens-svg-title lens-svg-title--dark' : 'lens-svg-title'}>
              {stage.question.split(' ').reduce<string[]>((lines, word) => {
                const last = lines.at(-1)
                if (!last || `${last} ${word}`.length > 24) lines.push(word)
                else lines[lines.length - 1] = `${last} ${word}`
                return lines
              }, []).map((line, lineIndex) => (
                <tspan key={line} x={stage.x + 18} dy={lineIndex === 0 ? 0 : 20}>{line}</tspan>
              ))}
            </text>
            <text x={stage.x + 18} y="187" className={dark ? 'lens-svg-detail lens-svg-detail--dark' : 'lens-svg-detail'}>{stage.detail}</text>
            {index < stages.length - 1 && (
              <line x1={stage.x + 234} y1="135" x2={stage.x + 263} y2="135" stroke="#4391b4" strokeWidth="1.5" markerEnd="url(#research-grammar-arrow)" />
            )}
          </g>
        )
      })}
      <text x="28" y="245" className="lens-svg-foot">Thesis first; data is selected because it can answer a thesis question.</text>
    </svg>
  )
}

function DecisionChainMap() {
  const stages = [
    ['Development', 'new fact'],
    ['Exposure', 'dated map'],
    ['Driver', 'operating bridge'],
    ['KPI / P&L', 'forecast line'],
    ['Expectation', 'consensus gap'],
    ['Scenario', 'up / down'],
    ['Next evidence', 'confirm / falsify'],
    ['Human action', 'research decision'],
  ]
  return (
    <svg
      viewBox="0 0 1110 220"
      role="img"
      aria-label="Decision chain from development to dated exposure, operating driver, KPI or P and L line, consensus expectation gap, upside and downside scenario, next confirming or falsifying evidence, and human research action."
    >
      <defs>
        <marker id="decision-chain-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0,0 L8,4 L0,8 z" fill="#4391b4" />
        </marker>
      </defs>
      {stages.map(([title, detail], index) => {
        const x = 18 + index * 136
        const dark = index === 1 || index === 7
        return (
          <g key={title}>
            <rect x={x} y="36" width="118" height="118" fill={dark ? '#151515' : index === 4 ? '#f4f1ea' : '#fff'} stroke={dark ? '#151515' : '#4391b4'} />
            <text x={x + 12} y="66" className={dark ? 'lens-svg-title lens-svg-title--dark' : 'lens-svg-title'}>{title}</text>
            <text x={x + 12} y="91" className={dark ? 'lens-svg-detail lens-svg-detail--dark' : 'lens-svg-detail'}>{detail.split(' / ').map((part, i) => <tspan key={part} x={x + 12} dy={i === 0 ? 0 : 17}>{part}</tspan>)}</text>
            <text x={x + 12} y="138" className={dark ? 'lens-svg-label lens-svg-label--dark' : 'lens-svg-label'}>{String(index + 1).padStart(2, '0')}</text>
            {index < stages.length - 1 && <line x1={x + 118} y1="95" x2={x + 131} y2="95" stroke="#4391b4" markerEnd="url(#decision-chain-arrow)" />}
          </g>
        )
      })}
      <line x1="18" y1="183" x2="1088" y2="183" stroke="#e4e4e2" />
      <text x="18" y="205" className="lens-svg-foot">Every link must be inspectable; weak links become explicit uncertainty.</text>
    </svg>
  )
}

function DevilAdvocateLoop() {
  return (
    <svg
      viewBox="0 0 540 304"
      role="img"
      aria-label="Devil's Advocate loop. A position above five percent net asset value triggers an independent pre-mortem, downside model and thesis challenge. The portfolio manager can retain, resize, hedge, or exit, and the resulting evidence returns to monitoring."
    >
      <defs>
        <marker id="devil-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0 L8,4 L0,8 z" fill="#4391b4" />
        </marker>
      </defs>
      <circle cx="270" cy="150" r="66" fill="#151515" />
      <text x="270" y="139" textAnchor="middle" className="lens-svg-title lens-svg-title--dark">Position</text>
      <text x="270" y="164" textAnchor="middle" className="lens-svg-number lens-svg-number--dark">&gt;5% NAV</text>
      <g>
        <rect x="32" y="38" width="160" height="78" fill="#edf6fa" stroke="#4391b4" />
        <text x="48" y="68" className="lens-svg-label">PRE-MORTEM</text>
        <text x="48" y="94" className="lens-svg-detail">How does this fail?</text>
        <path d="M190 92 C225 88, 228 93, 238 101" fill="none" stroke="#4391b4" markerEnd="url(#devil-arrow)" />
      </g>
      <g>
        <rect x="348" y="38" width="160" height="78" fill="#fff" stroke="#4391b4" />
        <text x="364" y="68" className="lens-svg-label">DOWNSIDE MODEL</text>
        <text x="364" y="94" className="lens-svg-detail">What breaks in P&amp;L?</text>
        <path d="M349 92 C315 88, 312 93, 302 101" fill="none" stroke="#4391b4" markerEnd="url(#devil-arrow)" />
      </g>
      <g>
        <rect x="32" y="208" width="160" height="58" fill="#fff" stroke="#4391b4" />
        <text x="48" y="238" className="lens-svg-label">THESIS CHALLENGE</text>
        <text x="48" y="255" className="lens-svg-detail">Disconfirming evidence</text>
        <path d="M190 224 C220 215, 229 207, 241 198" fill="none" stroke="#4391b4" markerEnd="url(#devil-arrow)" />
      </g>
      <g>
        <rect x="348" y="208" width="160" height="58" fill="#f4f1ea" stroke="#4391b4" />
        <text x="364" y="238" className="lens-svg-label">HUMAN CHOICE</text>
        <text x="364" y="255" className="lens-svg-detail">Retain · resize · hedge · exit</text>
        <path d="M350 224 C320 215, 311 207, 299 198" fill="none" stroke="#4391b4" markerEnd="url(#devil-arrow)" />
      </g>
    </svg>
  )
}

const outputContract = [
  ['Development', 'What changed?', 'Primary, dated evidence'],
  ['Exposure', 'Where could it land?', 'Current top ten, historical holding, inferred exposure or candidate'],
  ['Driver', 'What operating variable moves?', 'Volume, price, mix, margin, user, capacity or unit economics'],
  ['KPI / P&L', 'Which forecast line changes?', 'Direction, magnitude range and timing'],
  ['Expectation gap', 'Why might the market be wrong?', 'Consensus, valuation or narrative mismatch'],
  ['Scenario', 'What is the opportunity and risk?', 'Upside mechanism plus strongest downside case'],
  ['Horizon', 'When can it matter?', 'Immediate print, 6–18 months or multi-year structure'],
  ['Next evidence', 'How will we know?', 'One confirming signal and one falsifier'],
  ['Human action', 'What should the analyst do?', 'Investigate, update, monitor, challenge or ignore'],
]

export default function ResearchProcessPage() {
  return (
    <article className="bit-lens-view research-process-view">
      <section className="lens-lead lens-lead--process" aria-labelledby="process-lead-title">
        <div>
          <p className="lens-overline mono">RESEARCH PROCESS · PUBLICLY DOCUMENTED · REVIEWED 17 JUL 2026</p>
          <h2 id="process-lead-title">A company thesis, made continuously testable</h2>
          <p>
            BIT’s public material points to a thesis-first research system. Models and
            agents expand coverage and surface evidence; analysts own the forecast,
            valuation, position and challenge process.
          </p>
        </div>
        <div className="lens-process-principle">
          <span className="mono">CORE PRINCIPLE</span>
          <strong>Signal is useful only when it changes a model, a thesis, or a research priority.</strong>
          <SourceLink href={sources.approach}>Investment approach</SourceLink>
        </div>
      </section>

      <section className="lens-section lens-section--first" aria-labelledby="grammar-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">PUBLIC THESIS GRAMMAR</p>
            <h2 id="grammar-title">Thesis → Edge → Signal → Key Move</h2>
          </div>
          <p>
            Alternative data does not begin with a generic dataset. The company thesis
            determines which observable traces are worth building or buying.
          </p>
        </header>
        <div className="lens-canvas"><ResearchGrammarMap /></div>
        <p className="lens-note mono">
          Sources: <SourceLink href={sources.fund}>flagship thesis examples</SourceLink> · <SourceLink href={sources.oldenkottInterview}>Marcel Oldenkott interview</SourceLink>
        </p>
      </section>

      <section className="lens-section" aria-labelledby="fundamental-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">ANALYST OPERATING MODEL</p>
            <h2 id="fundamental-title">Translate every signal through the company model</h2>
          </div>
          <p>
            BIT’s analyst roles ask for first-principles operating work—not a topical
            relevance score floating above the P&amp;L.
          </p>
        </header>
        <div className="lens-equation" aria-label="Volume times price times mix times margin leads to KPI and profit and loss impact, then consensus and valuation impact.">
          <div><span className="mono">VOLUME</span><strong>Units, users, capacity</strong></div>
          <b aria-hidden="true">×</b>
          <div><span className="mono">PRICE</span><strong>ASP, take rate, yield</strong></div>
          <b aria-hidden="true">×</b>
          <div><span className="mono">MIX</span><strong>Product, customer, region</strong></div>
          <b aria-hidden="true">×</b>
          <div><span className="mono">MARGIN</span><strong>Cost, utilization, leverage</strong></div>
          <b aria-hidden="true">→</b>
          <div className="is-result"><span className="mono">MODEL</span><strong>KPI → P&amp;L → valuation</strong></div>
        </div>
        <p className="lens-note mono">
          Source: <SourceLink href={sources.semiconductorAnalyst}>Semiconductor analyst role</SourceLink> · corroborated by <SourceLink href={sources.seniorAnalyst}>Senior Analyst / Portfolio Manager role</SourceLink>
        </p>
      </section>

      <section className="lens-section" aria-labelledby="decision-chain-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">FLI → BIT DECISION CHAIN</p>
            <h2 id="decision-chain-title">The complete object an investment insight should become</h2>
          </div>
          <p>
            The system can draft and connect the chain. Missing links become uncertainty,
            not confident prose.
          </p>
        </header>
        <div className="lens-canvas"><DecisionChainMap /></div>
      </section>

      <section className="lens-section" aria-labelledby="aion-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">AION + INVESTMENT TEAM</p>
            <h2 id="aion-title">Machine scale, human accountability</h2>
          </div>
          <p>
            Public descriptions consistently place agents inside the research loop, with
            first-class access to data and models—not at the final decision boundary.
          </p>
        </header>
        <div className="lens-boundary">
          <div className="lens-boundary-machine">
            <span className="mono">AION / AGENTS</span>
            <h3>Expand the searchable frontier</h3>
            <ul>
              <li>Retrieve external and internal evidence</li>
              <li>Extract structured company information</li>
              <li>Update or assist financial-model work</li>
              <li>Generate scores, alerts, signals and insights</li>
              <li>Monitor freshness, uncertainty and hallucination</li>
            </ul>
          </div>
          <div className="lens-boundary-gate" aria-label="Human review boundary">
            <span className="mono">REVIEW</span>
            <i aria-hidden="true">→</i>
          </div>
          <div className="lens-boundary-human">
            <span className="mono">ANALYST / PM</span>
            <h3>Own the investment judgment</h3>
            <ul>
              <li>Form and revise the company thesis</li>
              <li>Choose forecast assumptions and valuation</li>
              <li>Judge whether the signal is causal and material</li>
              <li>Challenge the strongest disconfirming case</li>
              <li>Set timing, size, hedge, exit—or do nothing</li>
            </ul>
          </div>
        </div>
        <p className="lens-note mono">
          Sources: <SourceLink href={sources.aiEngineer}>AI Engineer / Aion role</SourceLink> · <SourceLink href={sources.faq}>BIT FAQ</SourceLink> · <SourceLink href={sources.approach}>investment approach</SourceLink>
        </p>
      </section>

      <section className="lens-section" aria-labelledby="challenge-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">RISK GATE</p>
            <h2 id="challenge-title">Conviction above 5% earns an adversary</h2>
          </div>
          <p>
            BIT describes multi-day Devil’s Advocate work for large positions: build the
            failure case, model the downside, and make the thesis survive challenge.
          </p>
        </header>
        <div className="lens-challenge-grid">
          <div className="lens-canvas"><DevilAdvocateLoop /></div>
          <div className="lens-challenge-copy">
            <div><span className="mono">TRIGGER</span><p>Position above 5% of NAV.</p></div>
            <div><span className="mono">CHALLENGER</span><p>A senior independent voice constructs the pre-mortem rather than polishing the base case.</p></div>
            <div><span className="mono">OUTPUT</span><p>Retain, resize, hedge or exit—with the strongest disconfirming evidence documented.</p></div>
            <div><span className="mono">FLI IMPLICATION</span><p>High-conviction exposures need better falsifiers, not more confirming headlines.</p></div>
            <SourceLink href={sources.approach}>BIT investment approach</SourceLink>
          </div>
        </div>
      </section>

      <section className="lens-section" aria-labelledby="worked-example-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">WORKED EXAMPLE · MICRON</p>
            <h2 id="worked-example-title">From model context growth to a portfolio research action</h2>
          </div>
          <p>
            This is the kind of bridge a frontier-lab signal can populate without pretending
            to know BIT’s internal forecast.
          </p>
        </header>
        <div className="lens-worked-example">
          <div><span className="mono">DEVELOPMENT</span><p>Agentic systems use longer context, retrieval and memory-intensive inference.</p></div>
          <div><span className="mono">EXPOSURE</span><p><strong>Micron · 8.6%</strong><br />Top-ten disclosure as of 30 Jun 2026.</p></div>
          <div><span className="mono">OPERATING BRIDGE</span><p>HBM volume × DRAM pricing × high-value mix × yield-driven margin.</p></div>
          <div><span className="mono">EXPECTATION GAP</span><p>Does HBM capacity displacement keep conventional memory tighter for longer than consensus?</p></div>
          <div><span className="mono">NEXT EVIDENCE</span><p>DRAM spot pricing, HBM qualification/yields, lead times and announced supply additions.</p></div>
          <div><span className="mono">HUMAN ACTION</span><p>Update the supply model; challenge capex-slowdown and yield-normalization scenarios.</p></div>
        </div>
      </section>

      <section className="lens-section" aria-labelledby="output-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">INVESTMENT INSIGHT SCHEMA</p>
            <h2 id="output-title">Nine questions before an insight deserves the fund’s time</h2>
          </div>
          <p>
            This is the personalization layer that differentiates the Investment view from
            a generic AI digest.
          </p>
        </header>
        <div className="lens-output-contract" role="list">
          {outputContract.map(([field, question, proof], index) => (
            <div key={field} role="listitem">
              <span className="lens-output-index mono">{String(index + 1).padStart(2, '0')}</span>
              <strong>{field}</strong>
              <p>{question}</p>
              <small>{proof}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="lens-section" aria-labelledby="tensions-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">INTERPRETATION CAUTIONS</p>
            <h2 id="tensions-title">Three public tensions the lens should preserve</h2>
          </div>
          <p>
            The honest explanation is often a scope distinction, not a choice between two
            apparently conflicting marketing statements.
          </p>
        </header>
        <div className="lens-tensions">
          <div>
            <span className="mono">LONG HORIZON / HIGH TURNOVER</span>
            <p>Long-duration company theses can coexist with frequent valuation- and signal-driven reweighting.</p>
          </div>
          <div>
            <span className="mono">BOTTOM-UP / TOP-DOWN</span>
            <p>Bottom-up work governs idea eligibility; macro, factor, liquidity and stress overlays govern portfolio exposure.</p>
          </div>
          <div>
            <span className="mono">AI SCALE CLAIMS</span>
            <p>Public data- and token-scale figures vary by page and likely by scope. No one number is treated as canonical.</p>
          </div>
        </div>
      </section>
    </article>
  )
}
