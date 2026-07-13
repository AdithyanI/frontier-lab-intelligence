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

function RosterGlyph({ x, y, dark }: { x: number; y: number; dark?: boolean }) {
  const bar = dark ? '#fff' : MUTED
  const rows = [
    { w: 66, org: false },
    { w: 46, org: true },
    { w: 76, org: false },
  ]
  return (
    <g>
      {rows.map((row, i) => (
        <g key={i}>
          {row.org ? (
            <rect x={x} y={y + i * 15 - 4} width={8} height={8} fill={BLUE} />
          ) : (
            <circle cx={x + 4} cy={y + i * 15} r={4} fill={BLUE} />
          )}
          <rect x={x + 16} y={y + i * 15 - 1.5} width={row.w} height={3} fill={bar} opacity={0.5} />
        </g>
      ))}
    </g>
  )
}

function DaysGlyph({ x, y }: { x: number; y: number }) {
  const dots = Array.from({ length: 7 }, (_, i) => x + 6 + i * 26)
  return (
    <g>
      <line x1={x} y1={y} x2={x + 168} y2={y} stroke={MUTED} strokeWidth="1" opacity="0.45" />
      {dots.map((cx) => (
        <circle key={cx} cx={cx} cy={y} r={3.5} fill={BLUE} />
      ))}
    </g>
  )
}

function EnvelopeGlyph({ x, y }: { x: number; y: number }) {
  const kids = [y - 18, y, y + 18]
  return (
    <g>
      <rect x={x} y={y - 11} width={32} height={22} fill="#fff" stroke={BLUE_MID} strokeWidth="1.2" />
      {kids.map((ky) => (
        <g key={ky}>
          <line x1={x + 32} y1={y} x2={x + 74} y2={ky} stroke={MUTED} strokeWidth="1" opacity="0.5" />
          <rect x={x + 74} y={ky - 6} width={26} height={12} fill="#fff" stroke={MUTED} strokeWidth="1" opacity="0.75" />
        </g>
      ))}
    </g>
  )
}

function RankedGlyph({ x, y }: { x: number; y: number }) {
  const rows = [
    { w: 98 },
    { w: 72 },
    { w: 50 },
  ]
  return (
    <g>
      {rows.map((row, i) => (
        <g key={i}>
          <rect x={x} y={y + i * 15 - 4.5} width={22} height={9} fill={BLUE} />
          <rect x={x + 30} y={y + i * 15 - 1.5} width={row.w} height={3} fill="#fff" opacity={0.5} />
        </g>
      ))}
    </g>
  )
}

function LiveSystemMap() {
  const stages = [
    { x: 28, kicker: 'WHO', title: 'Registry', glyph: 'roster', dark: true },
    { x: 292, kicker: 'SOURCE', title: 'X evidence', glyph: 'days' },
    { x: 556, kicker: 'STRUCTURE', title: 'Exact envelopes', glyph: 'envelope' },
    { x: 820, kicker: 'SURFACE', title: 'Feed', glyph: 'ranked', dark: true },
  ]
  const planned = [
    { x: 28, label: 'Primary artifacts' },
    { x: 370, label: 'Cited insights' },
    { x: 712, label: 'Investor + engineer delivery' },
  ]

  return (
    <svg
      viewBox="0 0 1080 392"
      role="img"
      aria-label="The live system: the screened Registry determines whose public X evidence is stored, exact relationships organize that evidence, and the Feed makes it inspectable. Primary artifacts, cited insights, and delivery are the next planned boundary."
    >
      <defs>
        <marker id="flow-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
        <marker id="flow-arrow-muted" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={MUTED} />
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
          <text x={stage.x + 18} y="122" fontFamily={UI} fontSize="18" fontWeight="600" fill={stage.dark ? '#fff' : INK}>{stage.title}</text>
          {stage.glyph === 'roster' && <RosterGlyph x={stage.x + 18} y={144} dark />}
          {stage.glyph === 'days' && <DaysGlyph x={stage.x + 18} y={158} />}
          {stage.glyph === 'envelope' && <EnvelopeGlyph x={stage.x + 18} y={158} />}
          {stage.glyph === 'ranked' && <RankedGlyph x={stage.x + 18} y={144} />}
        </g>
      ))}
      <Arrow x1={232} x2={286} />
      <Arrow x1={496} x2={550} />
      <Arrow x1={760} x2={814} />

      <line x1="28" y1="238" x2="1052" y2="238" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.45" />
      <text x="28" y="266" fontFamily={MONO} fontSize="11" fill={MUTED} letterSpacing="0.08em">NEXT BOUNDARY · PLANNED</text>
      <g opacity="0.62">
        {planned.map((box, index) => (
          <g key={box.label}>
            <rect x={box.x} y="282" width="280" height="56" fill="#fff" stroke={MUTED} strokeWidth="1.2" strokeDasharray="5 5" />
            <text x={box.x + 140} y="315" textAnchor="middle" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>{box.label}</text>
            {index < planned.length - 1 && (
              <line x1={box.x + 280} y1="310" x2={planned[index + 1].x - 8} y2="310" stroke={MUTED} strokeWidth="1.2" strokeDasharray="5 5" markerEnd="url(#flow-arrow-muted)" />
            )}
          </g>
        ))}
      </g>
      <text x="28" y="372" fontFamily={UI} fontSize="12.5" fill={MUTED}>The Feed is the evidence layer this reasoning will cite; it does not claim interpretation yet.</text>
    </svg>
  )
}

function AccountIntake() {
  const stages = [
    { x: 34, title: 'X handle', detail: 'one supplied account', tone: 'dark' },
    { x: 272, title: 'Profile gate', detail: 'public · collectable', tone: 'plain' },
    { x: 510, title: 'Resolve identity', detail: 'person · organization', tone: 'plain' },
    { x: 748, title: 'Registry', detail: 'tracked from now on', tone: 'dark' },
  ]
  return (
    <svg viewBox="0 0 1080 306" role="img" aria-label="A supplied X handle passes a profile gate and identity resolution before entering the Registry; either checkpoint can reject it, and the rejection reason is kept">
      <defs>
        <marker id="intake-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
        <marker id="intake-arrow-muted" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={MUTED} />
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
      {/* reject branch: either checkpoint can drop the account */}
      <g opacity="0.75">
        <line x1="367" y1="170" x2="367" y2="216" stroke={MUTED} strokeWidth="1.2" strokeDasharray="4 4" markerEnd="url(#intake-arrow-muted)" />
        <line x1="605" y1="170" x2="605" y2="216" stroke={MUTED} strokeWidth="1.2" strokeDasharray="4 4" markerEnd="url(#intake-arrow-muted)" />
        <rect x="272" y="222" width="428" height="52" fill="#fff" stroke={MUTED} strokeWidth="1.2" strokeDasharray="5 5" />
        <text x="486" y="248" textAnchor="middle" fontFamily={UI} fontSize="14" fontWeight="600" fill={INK}>Rejected</text>
        <text x="486" y="265" textAnchor="middle" fontFamily={MONO} fontSize="10.5" fill={MUTED} letterSpacing="0.06em">REASON KEPT · EVERY EXIT STAYS AUDITABLE</text>
      </g>
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
  const obsDots = [572, 634, 696, 758, 820, 882]
  const rawCards = [
    { x: 560, tag: 'post' },
    { x: 660, tag: 'reply' },
    { x: 760, tag: 'quote' },
    { x: 860, tag: 'retweet' },
  ]
  const graphSpokes = [
    { x: 160, y: 402 },
    { x: 148, y: 446 },
    { x: 330, y: 402 },
    { x: 344, y: 450 },
  ]
  return (
    <svg
      viewBox="0 0 1080 560"
      role="img"
      aria-label="Current data model: one real-world entity fans out to channels — the X channel is live, GitHub and arXiv are planned. X yields two streams: a fast-moving dated posts store, and a slow-moving follow graph whose network support decides who is tracked."
    >
      <defs>
        <marker id="data-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
        <marker id="data-arrow-muted" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={MUTED} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">ONE IDENTITY · CHANNELS PLUG IN · TWO STREAMS FROM X</text>

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

      {/* X → both stores */}
      <line x1="245" y1={CH_TOP + CH_H} x2="245" y2="340" stroke={BLUE_MID} strokeWidth="1.6" markerEnd="url(#data-arrow)" />
      <line x1="330" y1={CH_TOP + CH_H} x2="560" y2="340" stroke={BLUE_MID} strokeWidth="1.6" markerEnd="url(#data-arrow)" />
      {/* planned channels → posts store only */}
      <line x1="540" y1={CH_TOP + CH_H} x2="540" y2="340" stroke={MUTED} strokeWidth="1.2" strokeDasharray="5 5" opacity="0.35" />
      <line x1="835" y1={CH_TOP + CH_H} x2="835" y2="340" stroke={MUTED} strokeWidth="1.2" strokeDasharray="5 5" opacity="0.35" />

      {/* slow stream: the follow graph */}
      <rect x="90" y="346" width="310" height="154" fill={SAND} />
      <text x="112" y="374" fontFamily={MONO} fontSize="10" fill={BLUE_INK} letterSpacing="0.08em">FOLLOW GRAPH · SLOW</text>
      {graphSpokes.map((s) => (
        <g key={`spoke-${s.x}-${s.y}`}>
          <line x1={s.x} y1={s.y} x2="245" y2="430" stroke={BLUE_MID} strokeWidth="1" opacity="0.55" />
          <circle cx={s.x} cy={s.y} r="5" fill="#fff" stroke={BLUE_MID} strokeWidth="1.2" />
        </g>
      ))}
      <circle cx="245" cy="430" r="9" fill={INK} />
      <text x="112" y="481" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">who follows whom → network support</text>

      {/* fast stream: the dated posts store */}
      <rect x="440" y="346" width="550" height="154" fill={SURFACE} />
      <text x="462" y="374" fontFamily={MONO} fontSize="10" fill={BLUE_INK} letterSpacing="0.08em">POSTS · FAST</text>
      <text x="968" y="374" fontFamily={MONO} fontSize="10" fill={MUTED} textAnchor="end">time →</text>

      <text x="462" y="412" fontFamily={MONO} fontSize="11.5" fill={INK}>observations</text>
      <line x1="556" y1="408" x2="944" y2="408" stroke={MUTED} strokeWidth="1" opacity="0.5" markerEnd="url(#data-arrow)" />
      {obsDots.map((x) => (
        <circle key={`obs-${x}`} cx={x} cy="408" r="4" fill={BLUE} />
      ))}

      <text x="462" y="450" fontFamily={MONO} fontSize="11.5" fill={INK}>raw posts</text>
      {rawCards.map((r) => (
        <g key={`raw-${r.tag}`}>
          <rect x={r.x} y="432" width="74" height="24" fill="#fff" stroke={BLUE_MID} strokeWidth="1" />
          <text x={r.x + 37} y="448" textAnchor="middle" fontFamily={MONO} fontSize="10" fill={BLUE_INK}>{r.tag}</text>
        </g>
      ))}
      <text x="462" y="481" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">what they say, dated</text>

      {/* the slow stream decides who we track */}
      <path d="M 90 400 H 54 V 96 H 420" fill="none" stroke={BLUE_MID} strokeWidth="1.2" strokeDasharray="4 5" opacity="0.6" markerEnd="url(#data-arrow)" />
      <text x="70" y="86" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">DECIDES WHO WE TRACK</text>

      <text x="90" y="537" fontFamily={UI} fontSize="12.5" fill={MUTED}>Two refresh loops: posts move daily, the follow graph slowly. Planned channels join the same posts store.</text>
    </svg>
  )
}

function TrustRankFigure() {
  const insiders = [110, 142, 174, 206, 238]
  const crowd = [
    { x: 596, y: 96, r: 5 },
    { x: 622, y: 118, r: 4 },
    { x: 590, y: 142, r: 4.5 },
    { x: 626, y: 164, r: 4 },
    { x: 598, y: 188, r: 5 },
    { x: 630, y: 210, r: 4 },
    { x: 606, y: 230, r: 4.5 },
  ]
  return (
    <svg
      viewBox="0 0 1080 300"
      role="img"
      aria-label="Why an account ranks high: an account followed by five screened Registry members ranks higher than an account followed by a large public crowd but only one screened member. Public follower count is not an input."
    >
      <defs>
        <marker id="rank-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">WHY AN ACCOUNT RANKS HIGH · NETWORK SUPPORT</text>

      {/* Account A: five screened insiders */}
      <text x="100" y="76" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">SCREENED MEMBERS</text>
      {insiders.map((y) => (
        <g key={`in-${y}`}>
          <circle cx="118" cy={y + 20} r="7" fill={BLUE} />
          <line x1="130" y1={y + 20} x2="310" y2="168" stroke={BLUE_MID} strokeWidth="1.2" opacity="0.7" markerEnd="url(#rank-arrow)" />
        </g>
      ))}
      <rect x="318" y="140" width="150" height="56" fill={INK} />
      <text x="343" y="173" fontFamily={UI} fontSize="15" fontWeight="600" fill="#fff">Account A</text>
      <rect x="318" y="212" width="150" height="8" fill="none" stroke={MUTED} strokeWidth="1" opacity="0.5" />
      <rect x="318" y="212" width="132" height="8" fill={BLUE} />
      <text x="318" y="244" fontFamily={UI} fontSize="12.5" fill={INK}>5 screened followers → ranks high</text>

      {/* Account B: big public crowd, one insider */}
      <text x="588" y="76" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">PUBLIC CROWD</text>
      {crowd.map((c) => (
        <circle key={`cr-${c.x}-${c.y}`} cx={c.x} cy={c.y} r={c.r} fill="none" stroke={MUTED} strokeWidth="1.2" opacity="0.55" />
      ))}
      <circle cx="612" cy="258" r="7" fill={BLUE} />
      <line x1="624" y1="256" x2="800" y2="180" stroke={BLUE_MID} strokeWidth="1.2" opacity="0.7" markerEnd="url(#rank-arrow)" />
      <rect x="808" y="140" width="150" height="56" fill="#fff" stroke={MUTED} strokeWidth="1.2" />
      <text x="833" y="173" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>Account B</text>
      <rect x="808" y="212" width="150" height="8" fill="none" stroke={MUTED} strokeWidth="1" opacity="0.5" />
      <rect x="808" y="212" width="26" height="8" fill={BLUE} />
      <text x="808" y="244" fontFamily={UI} fontSize="12.5" fill={INK}>1 screened follower → ranks low</text>

      <text x="30" y="288" fontFamily={UI} fontSize="12.5" fill={MUTED}>Support counts screened Registry members only — a large public follower count is not an input.</text>
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
            member carry the same vote. This component measures breadth of Registry
            attention; amplifier network position stays visible but does not multiply
            the vote. <strong>Originator</strong> is the author&rsquo;s own network-support
            percentile. <strong>Engagement</strong> is log-scaled public interactions,
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
          <p className="arch-p">X yields two streams: fast-moving posts and a slow-moving follow graph that decides who is tracked.</p>
        </div>
        <div className="arch-canvas"><CurrentDataModel /></div>
        <div className="arch-canvas arch-canvas--sub"><TrustRankFigure /></div>
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
