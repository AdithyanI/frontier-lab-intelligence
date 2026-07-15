const INK = '#151515'
const MUTED = '#6b6b68'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
const SURFACE = '#f7f7f6'
const SAND = '#f4f1ea'
const MONO = "'IBM Plex Mono', monospace"
const UI = "'Inter', system-ui, sans-serif"

function SystemOverview() {
  const stages = [
    {
      x: 30,
      width: 170,
      label: 'SOURCES',
      title: 'Public evidence',
      detail: 'X + linked documents',
      meta: 'TWITTERAPI.IO',
      tone: 'plain',
    },
    {
      x: 236,
      width: 190,
      label: 'BACKEND',
      title: 'Python pipeline',
      detail: 'collect · group · rank',
      meta: 'PYTHON 3.13 · CLI STAGES',
      tone: 'dark',
    },
    {
      x: 462,
      width: 190,
      label: 'DATA',
      title: 'SQLite stores',
      detail: 'Registry · raw · derived',
      meta: 'AUDITABLE + REBUILDABLE',
      tone: 'surface',
    },
    {
      x: 688,
      width: 160,
      label: 'API',
      title: 'FastAPI',
      detail: 'typed JSON',
      meta: 'PYDANTIC · UVICORN',
      tone: 'plain',
    },
    {
      x: 884,
      width: 166,
      label: 'FRONTEND',
      title: 'React SPA',
      detail: 'browse · inspect · audit',
      meta: 'TYPESCRIPT · VITE',
      tone: 'plain',
    },
  ]

  return (
    <svg
      viewBox="0 0 1080 354"
      role="img"
      aria-label="Current high-level architecture. Public X evidence and linked documents enter a Python pipeline, which preserves canonical, raw, and derived data in SQLite. The pipeline calls models through LiteLLM and stores structured judgments. FastAPI exposes typed JSON to the React and TypeScript interface."
    >
      <defs>
        <marker id="overview-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>

      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">CURRENT STACK · ONE LOCAL-FIRST APPLICATION</text>

      {stages.map((stage) => {
        const dark = stage.tone === 'dark'
        const fill = dark ? INK : stage.tone === 'surface' ? SURFACE : '#fff'
        return (
          <g key={stage.label}>
            <rect
              x={stage.x}
              y="68"
              width={stage.width}
              height="112"
              fill={fill}
              stroke={dark ? INK : BLUE_MID}
              strokeWidth="1.2"
            />
            <text x={stage.x + 16} y="93" fontFamily={MONO} fontSize="9.5" fill={dark ? BLUE : BLUE_INK} letterSpacing="0.08em">{stage.label}</text>
            <text x={stage.x + 16} y="121" fontFamily={UI} fontSize="16" fontWeight="600" fill={dark ? '#fff' : INK}>{stage.title}</text>
            <text x={stage.x + 16} y="145" fontFamily={UI} fontSize="11.5" fill={dark ? '#fff' : MUTED} opacity={dark ? 0.78 : 1}>{stage.detail}</text>
            <text x={stage.x + 16} y="165" fontFamily={MONO} fontSize="7.8" fill={dark ? BLUE : MUTED} letterSpacing="0.04em">{stage.meta}</text>
          </g>
        )
      })}

      <line x1="200" y1="124" x2="230" y2="124" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#overview-arrow)" />
      <line x1="426" y1="124" x2="456" y2="124" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#overview-arrow)" />
      <line x1="652" y1="124" x2="682" y2="124" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#overview-arrow)" />
      <line x1="848" y1="124" x2="878" y2="124" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#overview-arrow)" />

      <path d="M331 180 V216" fill="none" stroke={BLUE_MID} strokeWidth="1.4" markerEnd="url(#overview-arrow)" />
      <rect x="236" y="224" width="416" height="76" fill={SAND} stroke={BLUE_MID} strokeWidth="1.2" />
      <text x="254" y="249" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.08em">MODEL BOUNDARY</text>
      <text x="254" y="275" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>OpenAI SDK → LiteLLM → models</text>
      <text x="254" y="291" fontFamily={MONO} fontSize="8" fill={MUTED} letterSpacing="0.04em">STRUCTURED JUDGMENTS · CACHE · USAGE · COST</text>
      <path d="M557 224 V188" fill="none" stroke={BLUE_MID} strokeWidth="1.4" markerEnd="url(#overview-arrow)" />

      <line x1="30" y1="328" x2="1050" y2="328" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="348" fontFamily={UI} fontSize="11.5" fill={MUTED}>Deterministic evidence processing comes first. Model judgments return to the same inspectable data layer.</text>
    </svg>
  )
}

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
  const dots = Array.from({ length: 7 }, (_, i) => x + 6 + i * 22)
  return (
    <g>
      <line x1={x} y1={y} x2={x + 144} y2={y} stroke={MUTED} strokeWidth="1" opacity="0.45" />
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

function AudienceRoutingGlyph({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <line x1={x} y1={y} x2={x + 38} y2={y} stroke={BLUE_MID} strokeWidth="1.3" />
      <rect x={x + 38} y={y - 18} width={32} height={18} fill="none" stroke={BLUE} strokeWidth="1" />
      <rect x={x + 76} y={y - 18} width={42} height={18} fill="none" stroke={BLUE} strokeWidth="1" />
      <text x={x + 54} y={y - 5} textAnchor="middle" fontFamily={MONO} fontSize="8.5" fill="#fff">AI</text>
      <text x={x + 97} y={y - 5} textAnchor="middle" fontFamily={MONO} fontSize="8.5" fill="#fff">INV</text>
      <text x={x + 38} y={y + 20} fontFamily={MONO} fontSize="8" fill={MUTED}>OR NEITHER</text>
    </g>
  )
}

function AcceptedEvidenceGlyph({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y - 18} width={38} height={42} fill={SAND} stroke={BLUE_MID} strokeWidth="1.1" />
      <rect x={x + 50} y={y - 12} width={38} height={36} fill="#fff" stroke={MUTED} strokeWidth="1" />
      <line x1={x + 8} y1={y - 6} x2={x + 30} y2={y - 6} stroke={BLUE_MID} strokeWidth="2" />
      <line x1={x + 8} y1={y + 2} x2={x + 26} y2={y + 2} stroke={MUTED} strokeWidth="1" />
      <line x1={x + 58} y1={y} x2={x + 80} y2={y} stroke={MUTED} strokeWidth="1" />
      <line x1={x + 58} y1={y + 8} x2={x + 76} y2={y + 8} stroke={MUTED} strokeWidth="1" />
      <text x={x + 44} y={y + 33} textAnchor="middle" fontFamily={MONO} fontSize="8.5" fill={MUTED}>+ ARTIFACT</text>
    </g>
  )
}

function EvidenceInputMap() {
  const stages = [
    { x: 28, kicker: 'WHO', title: 'Registry', glyph: 'roster', dark: true },
    { x: 234, kicker: 'SOURCE', title: 'X posts + threads', glyph: 'days' },
    { x: 440, kicker: 'STRUCTURE', title: 'Exact envelopes', glyph: 'envelope' },
    { x: 646, kicker: 'ROUTE', title: 'Audience relevance', glyph: 'audience', dark: true },
    { x: 852, kicker: 'EVIDENCE', title: 'Routed evidence', glyph: 'accepted' },
  ]

  return (
    <svg
      viewBox="0 0 1080 224"
      role="img"
      aria-label="Evidence input path. A screened Registry supplies dated X posts and threads. Exact envelopes are routed independently for AI Engineering and Investment. Routed evidence may be enriched with artifacts."
    >
      <defs>
        <marker id="flow-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>

      <text x="28" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">EVIDENCE INPUT · INSPECTABLE BEFORE JUDGMENT</text>
      {stages.map((stage) => (
        <g key={stage.title}>
          <rect
            x={stage.x}
            y="66"
            width="178"
            height="124"
            fill={stage.dark ? INK : '#fff'}
            stroke={stage.dark ? INK : BLUE_MID}
            strokeWidth="1.2"
          />
          <text x={stage.x + 18} y="92" fontFamily={MONO} fontSize="10" fill={stage.dark ? BLUE : BLUE_INK} letterSpacing="0.08em">{stage.kicker}</text>
          <text x={stage.x + 18} y="122" fontFamily={UI} fontSize={stage.title.length > 16 ? 15.5 : 18} fontWeight="600" fill={stage.dark ? '#fff' : INK}>{stage.title}</text>
          {stage.glyph === 'roster' && <RosterGlyph x={stage.x + 18} y={144} dark />}
          {stage.glyph === 'days' && <DaysGlyph x={stage.x + 18} y={158} />}
          {stage.glyph === 'envelope' && <EnvelopeGlyph x={stage.x + 18} y={158} />}
          {stage.glyph === 'audience' && <AudienceRoutingGlyph x={stage.x + 18} y={158} />}
          {stage.glyph === 'accepted' && <AcceptedEvidenceGlyph x={stage.x + 18} y={152} />}
        </g>
      ))}
      <Arrow x1={206} x2={228} />
      <Arrow x1={412} x2={434} />
      <Arrow x1={618} x2={640} />
      <Arrow x1={824} x2={846} />
    </svg>
  )
}

function InsightGenerationMap() {
  return (
    <svg
      viewBox="0 0 1080 360"
      role="img"
      aria-label="Insight generation path. Accepted evidence enters one shared citation-bound insight engine. Investment and AI Engineering then use separate audience prompts and editorial judgment, independent publication audits, and separate daily insight views."
    >
      <defs>
        <marker id="insight-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>

      <text x="28" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">FROM ACCEPTED EVIDENCE TO DAILY INSIGHTS</text>

      <g>
        <rect x="28" y="56" width="220" height="100" fill={SAND} stroke={BLUE_MID} strokeWidth="1.2" />
        <text x="46" y="82" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.08em">INPUT</text>
        <text x="46" y="109" fontFamily={UI} fontSize="18" fontWeight="600" fill={INK}>Accepted evidence</text>
        <text x="46" y="134" fontFamily={MONO} fontSize="9" fill={MUTED}>OPTIONAL ARTIFACT CONTEXT</text>
      </g>

      <line x1="248" y1="106" x2="298" y2="106" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#insight-arrow)" />

      <g>
        <rect x="306" y="56" width="448" height="100" fill={INK} />
        <text x="326" y="82" fontFamily={MONO} fontSize="9.5" fill={BLUE} letterSpacing="0.08em">SHARED CORE</text>
        <text x="326" y="109" fontFamily={UI} fontSize="18" fontWeight="600" fill="#fff">Citation-bound insight engine</text>
        <text x="326" y="134" fontFamily={MONO} fontSize="8.5" fill="#fff" opacity="0.65">FROZEN EVIDENCE · EXACT PASSAGES · SHARED PROVENANCE</text>
      </g>

      <path d="M754 106 H786 V192 H240 V210" fill="none" stroke={BLUE_MID} strokeWidth="1.4" markerEnd="url(#insight-arrow)" />
      <path d="M786 192 V210" fill="none" stroke={BLUE_MID} strokeWidth="1.4" markerEnd="url(#insight-arrow)" />

      <g>
        <text x="28" y="204" fontFamily={MONO} fontSize="10" fill={BLUE_INK} letterSpacing="0.08em">INVESTMENT</text>
        <rect x="28" y="216" width="148" height="70" fill={SAND} stroke={BLUE_MID} strokeWidth="1.1" />
        <text x="42" y="243" fontFamily={UI} fontSize="13.5" fontWeight="600" fill={INK}>Audience prompt</text>
        <text x="42" y="263" fontFamily={MONO} fontSize="9" fill={MUTED}>+ EDITORIAL JUDGMENT</text>
        <line x1="176" y1="251" x2="188" y2="251" stroke={BLUE_MID} strokeWidth="1.2" markerEnd="url(#insight-arrow)" />
        <rect x="194" y="216" width="128" height="70" fill="#fff" stroke={BLUE_MID} strokeWidth="1.1" />
        <text x="208" y="243" fontFamily={UI} fontSize="13.5" fontWeight="600" fill={INK}>Publication</text>
        <text x="208" y="263" fontFamily={MONO} fontSize="9" fill={MUTED}>INDEPENDENT AUDIT</text>
        <line x1="322" y1="251" x2="334" y2="251" stroke={BLUE_MID} strokeWidth="1.2" markerEnd="url(#insight-arrow)" />
        <rect x="340" y="216" width="160" height="70" fill={INK} />
        <text x="354" y="243" fontFamily={UI} fontSize="13.5" fontWeight="600" fill="#fff">Daily insights</text>
        <text x="354" y="263" fontFamily={MONO} fontSize="9" fill={BLUE}>SEPARATE VIEW</text>

        <text x="552" y="204" fontFamily={MONO} fontSize="10" fill={BLUE_INK} letterSpacing="0.08em">AI ENGINEERING</text>
        <rect x="552" y="216" width="148" height="70" fill={SAND} stroke={BLUE_MID} strokeWidth="1.1" />
        <text x="566" y="243" fontFamily={UI} fontSize="13.5" fontWeight="600" fill={INK}>Audience prompt</text>
        <text x="566" y="263" fontFamily={MONO} fontSize="9" fill={MUTED}>+ EDITORIAL JUDGMENT</text>
        <line x1="700" y1="251" x2="712" y2="251" stroke={BLUE_MID} strokeWidth="1.2" markerEnd="url(#insight-arrow)" />
        <rect x="718" y="216" width="128" height="70" fill="#fff" stroke={BLUE_MID} strokeWidth="1.1" />
        <text x="732" y="243" fontFamily={UI} fontSize="13.5" fontWeight="600" fill={INK}>Publication</text>
        <text x="732" y="263" fontFamily={MONO} fontSize="9" fill={MUTED}>INDEPENDENT AUDIT</text>
        <line x1="846" y1="251" x2="858" y2="251" stroke={BLUE_MID} strokeWidth="1.2" markerEnd="url(#insight-arrow)" />
        <rect x="864" y="216" width="188" height="70" fill={INK} />
        <text x="878" y="243" fontFamily={UI} fontSize="13.5" fontWeight="600" fill="#fff">Daily insights</text>
        <text x="878" y="263" fontFamily={MONO} fontSize="9" fill={BLUE}>SEPARATE VIEW</text>
      </g>

      <line x1="28" y1="322" x2="1052" y2="322" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.4" />
      <text x="28" y="343" fontFamily={UI} fontSize="12" fill={MUTED}>Evidence and citation rules stay shared. Audience prompts, judgment, audits, and published views do not.</text>
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
  const CH_TOP = 174
  const CH_H = 76
  const obsDots = [370, 472, 574, 676, 778, 880]
  const rawCards = [
    { x: 340, tag: 'post' },
    { x: 470, tag: 'reply' },
    { x: 600, tag: 'quote' },
    { x: 730, tag: 'retweet' },
  ]
  return (
    <svg
      viewBox="0 0 1080 444"
      role="img"
      aria-label="Current data model: one real-world entity fans out to channels. X is live; GitHub and arXiv are planned. Dated, source-bound X output arrives as a daily event stream."
    >
      <defs>
        <marker id="data-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
        <marker id="data-arrow-muted" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={MUTED} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">ONE IDENTITY · MANY CHANNELS · ONE EVIDENCE STREAM</text>

      {/* the real-world identity */}
      <rect x="430" y="58" width="220" height="72" fill={INK} />
      <text x="450" y="88" fontFamily={MONO} fontSize="10" fill={BLUE}>ENTITY</text>
      <text x="450" y="116" fontFamily={UI} fontSize="17" fontWeight="600" fill="#fff">Andrej Karpathy</text>

      {/* one identity fans out to platform-specific channels */}
      {channels.map((c) => (
        <line
          key={`fan-${c.plane}`}
          x1="540"
          y1="130"
          x2={c.cx}
          y2={CH_TOP - 6}
          stroke={c.live ? BLUE_MID : MUTED}
          strokeWidth={c.live ? 1.6 : 1.2}
          strokeDasharray={c.live ? undefined : '5 5'}
          opacity={c.live ? 1 : 0.55}
          markerEnd={c.live ? 'url(#data-arrow)' : 'url(#data-arrow-muted)'}
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

      {/* every channel plugs into the same evidence stream */}
      {channels.map((c) => (
        <line
          key={`stream-${c.plane}`}
          x1={c.cx}
          y1={CH_TOP + CH_H}
          x2={c.cx}
          y2="306"
          stroke={c.live ? BLUE_MID : MUTED}
          strokeWidth={c.live ? 1.6 : 1.2}
          strokeDasharray={c.live ? undefined : '5 5'}
          opacity={c.live ? 1 : 0.42}
          markerEnd={c.live ? 'url(#data-arrow)' : 'url(#data-arrow-muted)'}
        />
      ))}

      <rect x="90" y="312" width="900" height="110" fill={SURFACE} />
      <text x="116" y="342" fontFamily={MONO} fontSize="10" fill={BLUE_INK} letterSpacing="0.08em">ONE EVIDENCE STREAM</text>
      <text x="116" y="371" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>Dated observations</text>
      <text x="116" y="398" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.04em">source-bound · ordered in time</text>
      <line x1="308" y1="332" x2="308" y2="402" stroke={MUTED} strokeWidth="1" opacity="0.24" />

      <text x="340" y="340" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">DATED X OUTPUT · DAILY STREAM</text>
      <text x="956" y="340" fontFamily={MONO} fontSize="9.5" fill={MUTED} textAnchor="end">time →</text>
      <line x1="340" y1="356" x2="948" y2="356" stroke={MUTED} strokeWidth="1" opacity="0.5" markerEnd="url(#data-arrow)" />
      {obsDots.map((x) => (
        <circle key={`obs-${x}`} cx={x} cy="356" r="4" fill={BLUE} />
      ))}

      {rawCards.map((r) => (
        <g key={`raw-${r.tag}`}>
          <rect x={r.x} y="378" width="96" height="24" fill="#fff" stroke={BLUE_MID} strokeWidth="1" />
          <text x={r.x + 48} y="394" textAnchor="middle" fontFamily={MONO} fontSize="10" fill={BLUE_INK}>{r.tag}</text>
        </g>
      ))}
    </svg>
  )
}

function NetworkRankFigure() {
  const leftFollowerField = Array.from({ length: 15 }, (_, index) => ({
    x: 82 + (index % 3) * 24,
    y: 108 + Math.floor(index / 3) * 24,
  }))
  const leftScreenedIndices = new Set([0, 4, 8, 10, 14])
  const rightFollowerField = Array.from({ length: 35 }, (_, index) => ({
    x: 582 + (index % 7) * 24,
    y: 108 + Math.floor(index / 7) * 24,
  }))
  const rightScreenedIndex = 25
  const supportTicks = [0, 1, 2, 3, 4]
  return (
    <svg
      viewBox="0 0 1080 288"
      role="img"
      aria-label="X follow graph and network support, observed as a slow-moving snapshot: Account A has fewer public followers but five screened Registry followers, while Account B has many public followers but only one screened Registry follower. The five screened signals count, public audience size does not."
    >
      <defs>
        <marker id="rank-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">X FOLLOW GRAPH · WHY AN ACCOUNT RANKS HIGHER</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">SLOW-MOVING SNAPSHOT</text>
      <line x1="540" y1="60" x2="540" y2="276" stroke={MUTED} strokeWidth="1" opacity="0.22" />

      {/* Account A: the same follower field, with five screened nodes. */}
      <text x="70" y="72" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">FEWER FOLLOWERS OVERALL</text>
      <text x="70" y="90" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.05em">BUT 5 SCREENED FOLLOWERS</text>
      {leftFollowerField.map((node, index) => (
        leftScreenedIndices.has(index) ? null : (
          <line
            key={`a-public-line-${index}`}
            x1={node.x + 6}
            y1={node.y}
            x2="286"
            y2="168"
            stroke={MUTED}
            strokeWidth="0.9"
            strokeDasharray="2 5"
            opacity="0.2"
          />
        )
      ))}
      {leftFollowerField.map((node, index) => (
        leftScreenedIndices.has(index) ? (
          <line
            key={`a-screened-line-${index}`}
            x1={node.x + 7}
            y1={node.y}
            x2="286"
            y2="168"
            stroke={BLUE_MID}
            strokeWidth="1.2"
            opacity="0.72"
            markerEnd="url(#rank-arrow)"
          />
        ) : null
      ))}
      {leftFollowerField.map((node, index) => (
        <circle
          key={`a-follower-${index}`}
          cx={node.x}
          cy={node.y}
          r="4.5"
          fill={leftScreenedIndices.has(index) ? BLUE : '#fff'}
          stroke={leftScreenedIndices.has(index) ? BLUE : MUTED}
          strokeWidth={leftScreenedIndices.has(index) ? 0 : 1}
          opacity={leftScreenedIndices.has(index) ? 1 : 0.52}
        />
      ))}
      <rect x="296" y="138" width="174" height="60" fill={INK} />
      <text x="320" y="174" fontFamily={UI} fontSize="15" fontWeight="600" fill="#fff">Entity A</text>
      <text x="296" y="222" fontFamily={MONO} fontSize="9" fill={BLUE_INK} letterSpacing="0.06em">COUNTED SUPPORT</text>
      {supportTicks.map((tick) => (
        <rect key={`a-tick-${tick}`} x={296 + tick * 29} y="232" width="23" height="8" fill={BLUE} />
      ))}
      <text x="296" y="264" fontFamily={UI} fontSize="12.5" fontWeight="600" fill={INK}>5 of the voter set → higher support</text>

      {/* Account B: the same follower field, with only one screened node. */}
      <text x="582" y="72" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">MANY FOLLOWERS OVERALL</text>
      <text x="582" y="90" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.05em">BUT ONLY 1 SCREENED FOLLOWER</text>
      {rightFollowerField.map((node, index) => (
        index === rightScreenedIndex ? null : (
          <line
            key={`crowd-line-${index}`}
            x1={node.x + 6}
            y1={node.y}
            x2="794"
            y2="168"
            stroke={MUTED}
            strokeWidth="0.9"
            strokeDasharray="2 5"
            opacity="0.2"
          />
        )
      ))}
      {rightFollowerField.map((node, index) => (
        <circle
          key={`crowd-node-${index}`}
          cx={node.x}
          cy={node.y}
          r="4.5"
          fill={index === rightScreenedIndex ? BLUE : '#fff'}
          stroke={index === rightScreenedIndex ? BLUE : MUTED}
          strokeWidth={index === rightScreenedIndex ? 0 : 1}
          opacity={index === rightScreenedIndex ? 1 : 0.52}
        />
      ))}
      <line
        x1={rightFollowerField[rightScreenedIndex].x + 7}
        y1={rightFollowerField[rightScreenedIndex].y}
        x2="794"
        y2="168"
        stroke={BLUE_MID}
        strokeWidth="1.4"
        markerEnd="url(#rank-arrow)"
      />
      <rect x="804" y="138" width="174" height="60" fill="#fff" stroke={MUTED} strokeWidth="1.2" />
      <text x="828" y="174" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>Entity B</text>
      <text x="804" y="222" fontFamily={MONO} fontSize="9" fill={MUTED} letterSpacing="0.06em">COUNTED SUPPORT</text>
      {supportTicks.map((tick) => (
        <rect
          key={`b-tick-${tick}`}
          x={804 + tick * 29}
          y="232"
          width="23"
          height="8"
          fill={tick === 0 ? BLUE : '#fff'}
          stroke={tick === 0 ? BLUE : MUTED}
          strokeWidth={tick === 0 ? 0 : 1}
          opacity={tick === 0 ? 1 : 0.38}
        />
      ))}
      <text x="804" y="264" fontFamily={UI} fontSize="12.5" fill={INK}>1 of the voter set → lower support</text>

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
        <div className="method-id mono"><span>ENTITY-OVERLAP-V3</span><strong>Network support</strong></div>
        <div className="method-main">
          <p className="method-question">How many screened Registry entities point here?</p>
          <div className="method-equation mono">support = distinct active Registry entities following any represented X account · self excluded · dense rank within Registry</div>
        </div>
        <p className="method-limit">Registry shows N / voter denominator. Ranking keeps the global account discovery order. Neither is relevance.</p>
      </div>
      <div className="method-row method-row--attention">
        <div className="method-id mono"><span>ATTENTION-V1.1</span><strong>Daily score</strong></div>
        <div className="method-main">
          <p className="method-question">How is evidence ordered within one observed day?</p>
          <div className="method-equation method-equation--large mono">100 × (0.55 amplification + 0.25 author support + 0.20 engagement)</div>
          <div className="method-weight" aria-label="Daily score weights">
            <div className="method-weight-network"><b>55%</b><span>tracked amplification</span></div>
            <div className="method-weight-origin"><b>25%</b><span>author support</span></div>
            <div className="method-weight-public"><b>20%</b><span>public engagement</span></div>
          </div>
          <p className="method-explain">
            <strong>Tracked amplification</strong> counts every screened Registry member — person or
            organization — exactly once per post: Andrej Karpathy and the newest
            member carry the same vote. Amplifier network position stays visible but
            does not multiply the vote. <strong>Author network support</strong> is the
            originator&rsquo;s own support percentile. <strong>Public engagement</strong> is
            log-scaled likes, replies, reposts, and quotes,
            kept small as a tie-breaker. Each component is a percentile within the
            day&rsquo;s posts.
          </p>
        </div>
        <p className="method-limit">The Feed shows one stable daily rank across Audit filters; click it for this daily score. Not importance, quality, or truth.</p>
      </div>
    </div>
  )
}

export default function Architecture() {
  return (
    <div className="page arch-page">
      <h1 className="page-title">Architecture</h1>
      <p className="page-sub">A visual map of what is live, where judgment enters, and what each number means.</p>

      <nav className="arch-chapters" aria-label="Architecture chapters">
        <a href="#overview">Overview</a>
        <a href="#data-model">Data model</a>
        <a href="#account-intake">Account intake</a>
        <a href="#system-today">Pipeline</a>
        <a href="#ranking-methods">Numbers</a>
      </nav>

      <section className="arch-section arch-section--lead" id="overview">
        <div className="arch-section-head">
          <h2 className="arch-h">System at a glance</h2>
          <p className="arch-p">The complete stack in one view—from public evidence to the operator interface.</p>
        </div>
        <div className="arch-canvas"><SystemOverview /></div>
      </section>

      <section className="arch-section" id="data-model">
        <div className="arch-section-head">
          <h2 className="arch-h">The data model</h2>
          <p className="arch-p">X is observed in two ways: dated output arrives daily; follow relationships change more slowly.</p>
        </div>
        <div className="arch-canvas"><CurrentDataModel /></div>
        <div className="arch-canvas arch-canvas--sub"><NetworkRankFigure /></div>
      </section>

      <section className="arch-section" id="account-intake">
        <div className="arch-section-head">
          <h2 className="arch-h">How an account enters the Registry</h2>
          <p className="arch-p">A short, auditable path turns a supplied X handle into a resolved identity—or a recorded rejection.</p>
        </div>
        <div className="arch-canvas"><AccountIntake /></div>
      </section>

      <section className="arch-section" id="system-today">
        <div className="arch-section-head">
          <h2 className="arch-h">The evidence-to-insight path</h2>
          <p className="arch-p">One evidence core preserves exact provenance. Investment and AI Engineering then use separate prompts, editorial judgment, publication audits, and daily views.</p>
        </div>
        <div className="arch-canvas"><EvidenceInputMap /></div>
        <div className="arch-canvas arch-canvas--sub"><InsightGenerationMap /></div>
      </section>

      <section className="arch-section arch-section--methods" id="ranking-methods">
        <div className="arch-section-head">
          <h2 className="arch-h">The numbers answer different questions</h2>
          <p className="arch-p">Reach, network support, discovery position, and the daily score answer different questions so none can masquerade as quality.</p>
        </div>
        <div className="arch-canvas arch-canvas--methods"><RankingMethods /></div>
      </section>
    </div>
  )
}
