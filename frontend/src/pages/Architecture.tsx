const INK = '#151515'
const MUTED = '#6b6b68'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
const SURFACE = '#f7f7f6'
const SAND = '#f4f1ea'
const MONO = "'IBM Plex Mono', monospace"
const UI = "'Inter', system-ui, sans-serif"

function Arrow({ x1, x2, y = 128 }: { x1: number; x2: number; y?: number }) {
  return (
    <line
      x1={x1}
      y1={y}
      x2={x2}
      y2={y}
      stroke={BLUE_MID}
      strokeWidth="1.5"
      markerEnd="url(#flow-arrow)"
    />
  )
}

function LiveSystemMap() {
  const stages = [
    {
      x: 28,
      kicker: 'WHO',
      title: 'Registry',
      lines: ['screened people', 'and organizations'],
      dark: true,
    },
    {
      x: 292,
      kicker: 'SOURCE',
      title: 'X evidence',
      lines: ['7 complete UTC days', 'stored locally'],
    },
    {
      x: 556,
      kicker: 'STRUCTURE',
      title: 'Exact envelopes',
      lines: ['replies · quotes', 'retweets · singletons'],
    },
    {
      x: 820,
      kicker: 'SURFACE',
      title: 'Feed',
      lines: ['attention · recent', 'engagement'],
      dark: true,
    },
  ]

  return (
    <svg
      viewBox="0 0 1080 360"
      role="img"
      aria-label="The live system: the screened Registry determines whose public X evidence is stored, exact relationships organize that evidence, and the Feed makes it inspectable. Primary artifacts, cited insights, and delivery are the next planned boundary."
    >
      <defs>
        <marker id="flow-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>

      <text x="28" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">LIVE TODAY · ONE X EVIDENCE STREAM</text>
      {stages.map((stage) => (
        <g key={stage.title}>
          <rect
            x={stage.x}
            y="66"
            width="204"
            height="124"
            fill={stage.dark ? INK : '#fff'}
            stroke={stage.dark ? INK : BLUE_MID}
            strokeWidth="1.2"
          />
          <text x={stage.x + 18} y="92" fontFamily={MONO} fontSize="10" fill={stage.dark ? BLUE : BLUE_INK} letterSpacing="0.08em">{stage.kicker}</text>
          <text x={stage.x + 18} y="124" fontFamily={UI} fontSize="18" fontWeight="600" fill={stage.dark ? '#fff' : INK}>{stage.title}</text>
          {stage.lines.map((line, index) => (
            <text key={line} x={stage.x + 18} y={153 + index * 19} fontFamily={UI} fontSize="12.5" fill={stage.dark ? '#fff' : MUTED} opacity={stage.dark ? 0.78 : 1}>{line}</text>
          ))}
        </g>
      ))}
      <Arrow x1={232} x2={286} />
      <Arrow x1={496} x2={550} />
      <Arrow x1={760} x2={814} />

      <line x1="28" y1="238" x2="1052" y2="238" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.45" />
      <text x="28" y="270" fontFamily={MONO} fontSize="11" fill={MUTED} letterSpacing="0.08em">NEXT BOUNDARY · NOT YET THE FEED</text>
      <text x="28" y="307" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>Primary artifacts</text>
      <text x="204" y="307" fontFamily={MONO} fontSize="14" fill={BLUE_MID}>→</text>
      <text x="244" y="307" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>Cited insights</text>
      <text x="386" y="307" fontFamily={MONO} fontSize="14" fill={BLUE_MID}>→</text>
      <text x="426" y="307" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>Investor + engineer delivery</text>
      <text x="28" y="333" fontFamily={UI} fontSize="12.5" fill={MUTED}>The Feed is evidence for this later reasoning layer; it does not claim interpretation yet.</text>
    </svg>
  )
}

function AccountIntake() {
  const stages = [
    { x: 34, title: 'X handle', detail: 'one supplied account', tone: 'dark' },
    { x: 272, title: 'Profile gate', detail: 'public · collectable', tone: 'plain' },
    { x: 510, title: 'Resolve identity', detail: 'person · organization', tone: 'plain' },
    { x: 748, title: 'Registry', detail: 'or rejected + reason', tone: 'dark' },
  ]
  return (
    <svg viewBox="0 0 1080 262" role="img" aria-label="A supplied X handle passes a profile gate and identity resolution before entering the Registry or being rejected with a reason">
      <defs>
        <marker id="intake-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>
      <text x="34" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">WHEN AN X ACCOUNT IS SUPPLIED</text>
      {stages.map((stage, index) => (
        <g key={stage.title}>
          <rect x={stage.x} y="70" width="190" height="100" fill={stage.tone === 'dark' ? INK : index === 1 ? SAND : '#fff'} stroke={stage.tone === 'dark' || index === 1 ? 'none' : BLUE_MID} strokeWidth="1.2" />
          <text x={stage.x + 18} y="111" fontFamily={UI} fontSize="17" fontWeight="600" fill={stage.tone === 'dark' ? '#fff' : INK}>{stage.title}</text>
          <text x={stage.x + 18} y="139" fontFamily={UI} fontSize="12.5" fill={stage.tone === 'dark' ? '#fff' : MUTED} opacity={stage.tone === 'dark' ? 0.78 : 1}>{stage.detail}</text>
          {index < stages.length - 1 && <line x1={stage.x + 190} y1="120" x2={stages[index + 1].x - 8} y2="120" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#intake-arrow)" />}
        </g>
      ))}
      <path d="M843 170 L843 206" fill="none" stroke={MUTED} strokeWidth="1.2" strokeDasharray="4 4" />
      <text x="843" y="230" textAnchor="middle" fontFamily={MONO} fontSize="10.5" fill={MUTED}>EVERY EXIT STAYS AUDITABLE</text>
    </svg>
  )
}

function CurrentDataModel() {
  const channels = [
    { cx: 245, label: '@karpathy', plane: 'X', live: true },
    { cx: 540, label: 'github.com/karpathy', plane: 'GitHub', live: false },
    { cx: 835, label: 'arXiv · A. Karpathy', plane: 'Papers', live: false },
  ]
  const CW = 250
  const CH_TOP = 210
  const CH_H = 76
  const obsDots = [368, 440, 512, 584, 656, 728, 800]
  const rawCards = [
    { x: 380, tag: 'post' },
    { x: 500, tag: 'reply' },
    { x: 620, tag: 'quote' },
    { x: 740, tag: 'retweet' },
  ]
  return (
    <svg
      viewBox="0 0 1080 580"
      role="img"
      aria-label="Current data model: one real-world entity fans out to channels — the X channel is live, GitHub and arXiv are planned — and every channel writes into one dated evidence store that feeds the rebuildable derived run"
    >
      <defs>
        <marker id="data-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">ONE IDENTITY · CHANNELS PLUG IN · ONE EVIDENCE STORE</text>

      {/* entity (who) — faint stack behind = the whole Registry */}
      <rect x="438" y="68" width="220" height="72" fill={INK} opacity="0.12" />
      <rect x="430" y="60" width="220" height="72" fill={INK} />
      <text x="450" y="90" fontFamily={MONO} fontSize="10" fill={BLUE}>ENTITY · WHO</text>
      <text x="450" y="118" fontFamily={UI} fontSize="17" fontWeight="600" fill="#fff">Andrej Karpathy</text>

      {/* entity → channel fan */}
      {channels.map((c) => (
        <line
          key={`fan-${c.plane}`}
          x1="540"
          y1="132"
          x2={c.cx}
          y2={CH_TOP - 6}
          stroke={c.live ? BLUE_MID : MUTED}
          strokeWidth={c.live ? 1.6 : 1.2}
          strokeDasharray={c.live ? undefined : '5 5'}
          opacity={c.live ? 1 : 0.55}
          markerEnd={c.live ? 'url(#data-arrow)' : undefined}
        />
      ))}

      {/* channels (where) */}
      {channels.map((c) => (
        <g key={`chan-${c.plane}`} opacity={c.live ? 1 : 0.62}>
          <rect
            x={c.cx - CW / 2}
            y={CH_TOP}
            width={CW}
            height={CH_H}
            fill="#fff"
            stroke={c.live ? BLUE_MID : MUTED}
            strokeWidth="1.2"
            strokeDasharray={c.live ? undefined : '5 5'}
          />
          <text x={c.cx - CW / 2 + 16} y={CH_TOP + 27} fontFamily={MONO} fontSize="10" fill={c.live ? BLUE_INK : MUTED} letterSpacing="0.08em">
            {c.plane.toUpperCase()} · {c.live ? 'LIVE' : 'PLANNED'}
          </text>
          <text x={c.cx - CW / 2 + 16} y={CH_TOP + 54} fontFamily={UI} fontSize="15.5" fontWeight="600" fill={INK}>{c.label}</text>
        </g>
      ))}

      {/* channels → one store */}
      {channels.map((c) => (
        <line
          key={`conf-${c.plane}`}
          x1={c.cx}
          y1={CH_TOP + CH_H}
          x2="540"
          y2="332"
          stroke={c.live ? BLUE_MID : MUTED}
          strokeWidth="1.2"
          strokeDasharray={c.live ? undefined : '5 5'}
          opacity={c.live ? 0.8 : 0.4}
        />
      ))}
      <line x1="540" y1="332" x2="540" y2="344" stroke={BLUE_MID} strokeWidth="1.6" markerEnd="url(#data-arrow)" />

      {/* the dated evidence store (what) */}
      <rect x="90" y="348" width="900" height="122" fill={SURFACE} />
      <text x="112" y="376" fontFamily={MONO} fontSize="10" fill={BLUE_INK} letterSpacing="0.08em">SOURCE DATA · WHAT WE SAW, DATED</text>
      <text x="920" y="376" fontFamily={MONO} fontSize="11" fill={MUTED}>time →</text>

      <text x="112" y="408" fontFamily={MONO} fontSize="12" fill={INK}>observations</text>
      <line x1="352" y1="404" x2="924" y2="404" stroke={MUTED} strokeWidth="1" opacity="0.5" markerEnd="url(#data-arrow)" />
      {obsDots.map((x) => (
        <circle key={`obs-${x}`} cx={x} cy="404" r="4" fill={BLUE} />
      ))}

      <text x="112" y="446" fontFamily={MONO} fontSize="12" fill={INK}>raw posts</text>
      {rawCards.map((r) => (
        <g key={`raw-${r.tag}`}>
          <rect x={r.x} y="428" width="74" height="24" fill="#fff" stroke={BLUE_MID} strokeWidth="1" />
          <text x={r.x + 37} y="444" textAnchor="middle" fontFamily={MONO} fontSize="10" fill={BLUE_INK}>{r.tag}</text>
        </g>
      ))}

      {/* derived run */}
      <line x1="540" y1="470" x2="540" y2="494" stroke={BLUE_MID} strokeWidth="1.6" markerEnd="url(#data-arrow)" />
      <rect x="90" y="498" width="900" height="60" fill={SAND} />
      <text x="112" y="524" fontFamily={MONO} fontSize="10" fill={BLUE_INK} letterSpacing="0.08em">DERIVED RUN · REBUILDABLE</text>
      <text x="112" y="546" fontFamily={UI} fontSize="14" fontWeight="600" fill={INK}>Exact envelopes</text>
      <text x="252" y="546" fontFamily={MONO} fontSize="12" fill={BLUE_MID}>→</text>
      <text x="282" y="546" fontFamily={UI} fontSize="14" fontWeight="600" fill={INK}>Attention features</text>
      <text x="428" y="546" fontFamily={MONO} fontSize="12" fill={BLUE_MID}>→</text>
      <text x="458" y="546" fontFamily={UI} fontSize="14" fontWeight="600" fill={INK}>Feed rows</text>
      <text x="988" y="546" textAnchor="end" fontFamily={UI} fontSize="12" fill={MUTED}>new channels join the same store — nothing downstream changes</text>
    </svg>
  )
}

function RankingMethods() {
  return (
    <div className="methodology" aria-label="Current ranking formulas">
      <div className="method-row">
        <div className="method-id mono"><span>REACH</span><strong>Registry</strong></div>
        <div className="method-main">
          <p className="method-question">How large is the observed X audience?</p>
          <div className="method-equation mono">people: X followers · organizations: sum of owned X channels</div>
        </div>
        <p className="method-limit">Useful for reach. Not a trust score.</p>
      </div>
      <div className="method-row">
        <div className="method-id mono"><span>ENTITY-OVERLAP-V2</span><strong>Network support</strong></div>
        <div className="method-main">
          <p className="method-question">How many screened Registry entities point here?</p>
          <div className="method-equation mono">support = distinct active Registry entities following an account</div>
        </div>
        <p className="method-limit">Follower count is not an input. Support is not relevance.</p>
      </div>
      <div className="method-row method-row--attention">
        <div className="method-id mono"><span>ATTENTION-V1.1</span><strong>Feed ordering</strong></div>
        <div className="method-main">
          <p className="method-question">Which evidence is the screened network noticing today?</p>
          <div className="method-equation method-equation--large mono">100 × (0.55 network + 0.25 originator + 0.20 engagement)</div>
          <div className="method-weight" aria-label="Feed attention weights">
            <div className="method-weight-network"><b>55%</b><span>network</span></div>
            <div className="method-weight-origin"><b>25%</b><span>originator</span></div>
            <div className="method-weight-public"><b>20%</b><span>engagement</span></div>
          </div>
          <p className="method-explain">
            <strong>Network</strong> counts every screened Registry member — person or
            organization — exactly once per post: Andrej Karpathy and the newest
            member carry the same vote. Breadth of insider convergence is the
            signal, not celebrity, because trusted people retweet football too.
            <strong> Originator</strong> is the author&rsquo;s own standing in the trust
            ranking. <strong>Engagement</strong> is log-scaled public interactions,
            kept small as a tie-breaker. Each component is a percentile within the
            day&rsquo;s posts.
          </p>
        </div>
        <p className="method-limit">A candidate-generation score. Not quality or truth.</p>
      </div>
    </div>
  )
}

export default function Architecture() {
  return (
    <div className="page arch-page">
      <h1 className="page-title">Architecture</h1>
      <p className="page-sub">A visual map of what is live today, what the numbers mean, and where reasoning begins next.</p>

      <nav className="arch-chapters" aria-label="Architecture chapters">
        <a href="#system-today">System today</a>
        <a href="#account-intake">Account intake</a>
        <a href="#data-model">Data model</a>
        <a href="#ranking-methods">Numbers</a>
      </nav>

      <section className="arch-section arch-section--lead" id="system-today">
        <div className="arch-section-head">
          <h2 className="arch-h">The system today</h2>
          <p className="arch-p">The current Feed is one stored X evidence stream. It organizes evidence; it does not yet write insights.</p>
        </div>
        <div className="arch-canvas"><LiveSystemMap /></div>
      </section>

      <section className="arch-section" id="account-intake">
        <div className="arch-section-head">
          <h2 className="arch-h">How an account enters the Registry</h2>
          <p className="arch-p">A short, auditable path turns a supplied X handle into a resolved identity—or a recorded rejection.</p>
        </div>
        <div className="arch-canvas"><AccountIntake /></div>
      </section>

      <section className="arch-section" id="data-model">
        <div className="arch-section-head">
          <h2 className="arch-h">One data model underneath</h2>
          <p className="arch-p">Source evidence is preserved; Feed groupings and scores are rebuildable derived views.</p>
        </div>
        <div className="arch-canvas"><CurrentDataModel /></div>
      </section>

      <section className="arch-section arch-section--methods" id="ranking-methods">
        <div className="arch-section-head">
          <h2 className="arch-h">The numbers answer different questions</h2>
          <p className="arch-p">Reach, network support, and attention are deliberately separate so none can masquerade as quality.</p>
        </div>
        <div className="arch-canvas arch-canvas--methods"><RankingMethods /></div>
      </section>
    </div>
  )
}
