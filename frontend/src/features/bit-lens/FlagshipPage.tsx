import { holdings, snapshots, sources, themeWeights, type EvidenceGrade } from './bitLensData'

const gradeClass: Record<EvidenceGrade, string> = {
  'BIT thesis': 'is-explicit',
  'BIT commentary': 'is-partial',
  'Analyst inference': 'is-inferred',
}

function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {children} <span aria-hidden="true">↗</span>
    </a>
  )
}

function ThesisTranslationMap() {
  const stages = [
    { x: 24, width: 142, label: '01 · DEVELOPMENT', title: 'Frontier change', detail: 'What became newly true?' },
    { x: 184, width: 142, label: '02 · BOTTLENECK', title: 'Constraint', detail: 'Compute · memory · power' },
    { x: 344, width: 142, label: '03 · EXPOSURE', title: 'Fund mapping', detail: 'Dated holding or thesis' },
    { x: 504, width: 142, label: '04 · DRIVER', title: 'Operating bridge', detail: 'Volume · price · mix · margin' },
    { x: 664, width: 142, label: '05 · EXPECTATION', title: 'Market gap', detail: 'Consensus or valuation' },
    { x: 824, width: 142, label: '06 · EVIDENCE', title: 'Proof / falsifier', detail: 'Next observable KPI' },
    { x: 984, width: 142, label: '07 · ACTION', title: 'Human decision', detail: 'Investigate · update · challenge' },
  ]

  return (
    <svg
      viewBox="0 0 1150 248"
      role="img"
      aria-label="BIT Lens translation. A frontier development reveals a structural bottleneck, which maps to a dated fund exposure, an operating driver, a market expectation gap, confirming or disconfirming evidence, and finally a human research action."
    >
      <defs>
        <marker id="lens-map-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0 L8,4 L0,8 z" fill="#4391b4" />
        </marker>
      </defs>
      <text x="24" y="30" className="lens-svg-kicker">THE TRANSLATION THE PRODUCT SHOULD PERFORM</text>
      {stages.map((stage, index) => {
        const dark = index === 2 || index === 6
        return (
          <g key={stage.label}>
            <rect
              x={stage.x}
              y="62"
              width={stage.width}
              height="128"
              fill={dark ? '#151515' : index === 1 ? '#edf6fa' : '#fff'}
              stroke={dark ? '#151515' : '#4391b4'}
              strokeWidth="1.2"
            />
            <text x={stage.x + 13} y="86" className={dark ? 'lens-svg-label lens-svg-label--dark' : 'lens-svg-label'}>{stage.label}</text>
            <text x={stage.x + 13} y="123" className={dark ? 'lens-svg-title lens-svg-title--dark' : 'lens-svg-title'}>{stage.title}</text>
            <text x={stage.x + 13} y="153" className={dark ? 'lens-svg-detail lens-svg-detail--dark' : 'lens-svg-detail'}>
              {stage.detail.split(' · ').map((line, lineIndex) => (
                <tspan key={line} x={stage.x + 13} dy={lineIndex === 0 ? 0 : 17}>{line}</tspan>
              ))}
            </text>
            {index < stages.length - 1 && (
              <line
                x1={stage.x + stage.width}
                y1="126"
                x2={stage.x + stage.width + 13}
                y2="126"
                stroke="#4391b4"
                strokeWidth="1.3"
                markerEnd="url(#lens-map-arrow)"
              />
            )}
          </g>
        )
      })}
      <line x1="24" y1="219" x2="1126" y2="219" stroke="#e4e4e2" />
      <text x="24" y="239" className="lens-svg-foot">Machine-supported research object</text>
      <text x="1126" y="239" textAnchor="end" className="lens-svg-foot">Portfolio decision remains human</text>
    </svg>
  )
}

function PortfolioRhythm() {
  const x = [90, 326, 562, 798, 1034]
  const positionY = snapshots.map((item) => 122 - (item.positions - 28) * 3.15)
  const cashY = snapshots.map((item) => 230 - item.cash * 7)
  const positionPoints = x.map((value, index) => `${value},${positionY[index]}`).join(' ')
  const cashPoints = x.map((value, index) => `${value},${cashY[index]}`).join(' ')

  return (
    <svg
      viewBox="0 0 1120 286"
      role="img"
      aria-label="Portfolio rhythm from January to June 2026. Position count moves from 39 to 29, 35, 36, then 28. Cash and derivatives move from 3.2 percent to 15.1 percent, approximately 0.9 percent, 2.5 percent, then 5.4 percent."
    >
      <text x="18" y="24" className="lens-svg-label">POSITION COUNT</text>
      <line x1="90" y1="46" x2="1034" y2="46" stroke="#e4e4e2" />
      <line x1="90" y1="122" x2="1034" y2="122" stroke="#e4e4e2" />
      <polyline points={positionPoints} fill="none" stroke="#151515" strokeWidth="2" />
      {snapshots.map((item, index) => (
        <g key={`positions-${item.date}`}>
          <circle cx={x[index]} cy={positionY[index]} r="5" fill="#5bc5f2" stroke="#151515" strokeWidth="1.2" />
          <text x={x[index]} y={positionY[index] - 13} textAnchor="middle" className="lens-svg-number">{item.positions}</text>
        </g>
      ))}

      <text x="18" y="158" className="lens-svg-label">CASH + DERIVATIVES</text>
      <line x1="90" y1="174" x2="1034" y2="174" stroke="#e4e4e2" />
      <line x1="90" y1="230" x2="1034" y2="230" stroke="#e4e4e2" />
      <polyline points={cashPoints} fill="none" stroke="#4391b4" strokeWidth="2" />
      {snapshots.map((item, index) => (
        <g key={`cash-${item.date}`}>
          <rect x={x[index] - 4} y={cashY[index] - 4} width="8" height="8" fill="#235165" />
          <text x={x[index]} y={cashY[index] - 12} textAnchor="middle" className="lens-svg-number">{item.cash.toFixed(1)}%</text>
          <text x={x[index]} y="265" textAnchor="middle" className="lens-svg-date">{item.date}</text>
        </g>
      ))}
    </svg>
  )
}

function ThemeBar() {
  const total = 60.7
  let offset = 0
  return (
    <div className="lens-theme-bar" role="img" aria-label="The disclosed June top ten contains 36.9 percentage points of AI infrastructure exposure, 10.4 of AI platform exposure, 8.4 of HealthTech exposure, and 5.0 of Fintech exposure.">
      <div className="lens-theme-track" aria-hidden="true">
        {themeWeights.map((theme) => {
          const left = offset
          offset += theme.value
          return (
            <span
              key={theme.label}
              className={`lens-theme-segment is-${theme.tone}`}
              style={{ left: `${(left / total) * 100}%`, width: `${(theme.value / total) * 100}%` }}
            />
          )
        })}
      </div>
      <div className="lens-theme-legend">
        {themeWeights.map((theme) => (
          <div key={theme.label}>
            <span className={`lens-theme-key is-${theme.tone}`} aria-hidden="true" />
            <strong className="mono">{theme.value.toFixed(1)}%</strong>
            <span>{theme.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function EvidenceBadge({ grade }: { grade: EvidenceGrade }) {
  return <span className={`lens-evidence-badge ${gradeClass[grade]}`}>{grade}</span>
}

const sourceLedger = [
  ['30 Jun 2026', 'Official June factsheet', 'Current top ten, weights, allocations and manager commentary', sources.juneFactsheet],
  ['31 Dec 2025', 'Audited annual report', 'Latest complete public portfolio and fund-year accounts', sources.annualReport],
  ['30 Jun 2025', 'Semiannual report', 'Complete midyear holdings for historical comparison', sources.semiannualReport],
  ['Current', 'Flagship fund page', 'Public mandate and published company thesis examples', sources.fund],
  ['Current', 'Investment approach', 'Research loop, agent support, sizing and Devil’s Advocate gate', sources.approach],
  ['Current', 'BIT FAQ', 'Human/model responsibilities and current operating description', sources.faq],
]

export default function FlagshipPage() {
  return (
    <article className="bit-lens-view flagship-view">
      <section className="lens-lead" aria-labelledby="flagship-lead-title">
        <div>
          <p className="lens-overline mono">FLAGSHIP · PUBLIC EVIDENCE · REVIEWED 17 JUL 2026</p>
          <h2 id="flagship-lead-title">Where frontier AI becomes portfolio evidence</h2>
          <p>
            The useful unit is not “AI news.” It is a cited development translated into a
            dated exposure, an operating driver, a measurable expectation gap, and a
            falsifiable research action.
          </p>
        </div>
        <dl className="lens-metric-strip">
          <div><dt>Fund assets</dt><dd>€1.594B</dd></div>
          <div><dt>Positions</dt><dd>28</dd></div>
          <div><dt>Top ten</dt><dd>60.7%</dd></div>
          <div><dt>Equity</dt><dd>94.6%</dd></div>
        </dl>
      </section>

      <section className="lens-section lens-section--first" aria-labelledby="translation-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">OUTPUT CONTRACT</p>
            <h2 id="translation-title">One development, translated all the way to a decision</h2>
          </div>
          <p>
            Exposure is always dated. The final node is a research action—not an
            automated trade recommendation.
          </p>
        </header>
        <div className="lens-canvas"><ThesisTranslationMap /></div>
      </section>

      <section className="lens-section" aria-labelledby="snapshot-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">PORTFOLIO RHYTHM · 2026</p>
            <h2 id="snapshot-title">The fund moves faster than an annual holdings file</h2>
          </div>
          <p>
            Position count and cash changed sharply within five months. A holding name
            without an <span className="mono">as_of</span> date is not portfolio truth.
          </p>
        </header>
        <div className="lens-canvas lens-canvas--rhythm"><PortfolioRhythm /></div>
        <div className="lens-snapshot-row" role="list" aria-label="Monthly flagship snapshots">
          {snapshots.map((item) => (
            <div key={item.date} role="listitem">
              <span className="mono">{item.date}</span>
              <strong>{item.note}</strong>
              <small>{item.top}</small>
            </div>
          ))}
        </div>
        <p className="lens-note mono">
          March factsheet not found · April cash approximated from 99.1% reported equity ·
          January and February values recovered from indexed official factsheets whose origin URLs no longer resolve.
        </p>
      </section>

      <section className="lens-section" aria-labelledby="top-ten-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">CURRENT DISCLOSED EXPOSURE · 30 JUN 2026</p>
            <h2 id="top-ten-title">The top ten, with evidence strength attached</h2>
          </div>
          <p>
            Six names have usable BIT-stated public evidence. Only three have a full
            public Thesis–Edge–Signal story; four remain analyst inference.
          </p>
        </header>
        <ThemeBar />
        <div className="lens-table-wrap">
          <table className="lens-holdings-table">
            <thead>
              <tr>
                <th scope="col">Rank</th>
                <th scope="col">Holding</th>
                <th scope="col">Weight</th>
                <th scope="col">Evidence</th>
                <th scope="col">Observable bridge</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => (
                <tr key={holding.ticker}>
                  <td className="num">#{holding.rank}</td>
                  <td>
                    <strong>{holding.name}</strong>
                    <span className="lens-ticker mono">{holding.ticker} · {holding.theme}</span>
                  </td>
                  <td className="lens-weight-cell">
                    <span className="mono">{holding.weight.toFixed(1)}%</span>
                    <span className="lens-weight-track" aria-hidden="true">
                      <span style={{ width: `${(holding.weight / 10.4) * 100}%` }} />
                    </span>
                  </td>
                  <td><EvidenceBadge grade={holding.grade} /></td>
                  <td>{holding.signals[0]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="lens-note mono">
          Theme percentages describe disclosed top-ten weight only—not total fund exposure.
          Source: <SourceLink href={sources.juneFactsheet}>official June factsheet</SourceLink>.
        </p>
      </section>

      <section className="lens-section" aria-labelledby="rotation-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">AUDITED BASELINE → CURRENT DISCLOSURE</p>
            <h2 id="rotation-title">Five of December’s top ten remain in June’s top ten</h2>
          </div>
          <p>
            Amazon rose from 1.78% in the complete year-end portfolio to 10.4% in June.
            SanDisk, Marvell and Infineon entered the disclosed top ten.
          </p>
        </header>
        <div className="lens-rotation">
          <div>
            <span className="mono">31 DEC 2025 · AUDITED</span>
            <p>IREN · AUTO1 · Hinge · TSMC · Micron · Reddit · Alphabet · Datadog · Lemonade · Robinhood</p>
          </div>
          <div className="lens-rotation-bridge" aria-label="Five names retained, five names replaced">
            <strong className="mono">5 / 10</strong>
            <span>retained</span>
          </div>
          <div>
            <span className="mono">30 JUN 2026 · DISCLOSED</span>
            <p>Amazon · Micron · IREN · SanDisk · Robinhood · Marvell · TSMC · Infineon · Hinge · Oscar</p>
          </div>
        </div>
      </section>

      <section className="lens-section" aria-labelledby="holding-theses-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">HOLDING LENSES</p>
            <h2 id="holding-theses-title">Thesis, edge, signal and disconfirming risk</h2>
          </div>
          <p>
            Expand a name to see the minimum context an investment insight should carry.
            Inference is labeled rather than written in BIT’s voice.
          </p>
        </header>
        <div className="lens-holding-details">
          {holdings.map((holding) => (
            <details key={holding.ticker}>
              <summary>
                <span className="lens-detail-rank mono">#{holding.rank}</span>
                <span className="lens-detail-name"><strong>{holding.name}</strong><small>{holding.ticker} · {holding.weight.toFixed(1)}%</small></span>
                <EvidenceBadge grade={holding.grade} />
                <span className="lens-detail-signal">{holding.signals[0]}</span>
                <span className="lens-detail-toggle" aria-hidden="true">+</span>
              </summary>
              <div className="lens-detail-body">
                <div>
                  <h3>Thesis</h3>
                  <p>{holding.thesis}</p>
                </div>
                <div>
                  <h3>Possible edge</h3>
                  <p>{holding.edge}</p>
                </div>
                <div>
                  <h3>Watch next</h3>
                  <ul>{holding.signals.map((signal) => <li key={signal}>{signal}</li>)}</ul>
                </div>
                <div>
                  <h3>Disconfirming case</h3>
                  <p>{holding.risk}</p>
                  <p className="lens-detail-source mono"><SourceLink href={holding.sourceUrl}>{holding.sourceLabel}</SourceLink></p>
                </div>
              </div>
            </details>
          ))}
        </div>
      </section>

      <section className="lens-section" aria-labelledby="source-ledger-title">
        <header className="lens-section-head">
          <div>
            <p className="lens-section-kicker mono">SOURCE LEDGER</p>
            <h2 id="source-ledger-title">What is known, and from when</h2>
          </div>
          <p>
            Mandatory reports establish holdings. BIT’s pages and dated commentary
            establish public theses. They are different evidence classes.
          </p>
        </header>
        <div className="lens-table-wrap">
          <table className="lens-source-table">
            <thead><tr><th scope="col">As of</th><th scope="col">Source</th><th scope="col">Use</th></tr></thead>
            <tbody>
              {sourceLedger.map(([date, label, use, url]) => (
                <tr key={label}>
                  <td className="mono">{date}</td>
                  <td><SourceLink href={url}>{label}</SourceLink></td>
                  <td>{use}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="lens-limitations" aria-labelledby="limits-title">
        <div>
          <p className="lens-section-kicker mono">RESEARCH BOUNDARY</p>
          <h2 id="limits-title">Public context—not a shadow portfolio system</h2>
        </div>
        <ul>
          <li>No public complete current 28-name portfolio.</li>
          <li>No internal forecasts, cost bases, targets or sell thresholds.</li>
          <li>No public model-accuracy or signal-attribution history.</li>
          <li>Public case studies skew toward successful investments.</li>
        </ul>
      </section>
    </article>
  )
}
