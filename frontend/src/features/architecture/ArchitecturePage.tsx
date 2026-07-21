import NetworkRankFigure from './NetworkRankFigure'

const INK = '#151515'
const MUTED = '#6b6b68'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
const SURFACE = '#f7f7f6'
const SAND = '#f4f1ea'
const MONO = "'IBM Plex Mono', monospace"
const UI = "'Inter', system-ui, sans-serif"

/* One shared card so every diagram uses the same geometry: kicker at the
   top, title in the middle, one detail line below. */
function Card({
  x,
  y,
  w,
  h = 104,
  kicker,
  title,
  detail,
  tone = 'plain',
}: {
  x: number
  y: number
  w: number
  h?: number
  kicker?: string
  title: string
  detail?: string
  tone?: 'plain' | 'dark' | 'sand' | 'surface'
}) {
  const dark = tone === 'dark'
  const fill = dark ? INK : tone === 'sand' ? SAND : tone === 'surface' ? SURFACE : '#fff'
  const midY = kicker ? y + h / 2 + 10 : y + h / 2 - 4
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} fill={fill} stroke={dark ? INK : BLUE_MID} strokeWidth="1.2" />
      {kicker && (
        <text x={x + 18} y={y + 28} fontFamily={MONO} fontSize="9.5" fill={dark ? BLUE : BLUE_INK} letterSpacing="0.08em">
          {kicker}
        </text>
      )}
      <text x={x + 18} y={midY} fontFamily={UI} fontSize={title.length > 16 ? 15.5 : 17} fontWeight="600" fill={dark ? '#fff' : INK}>
        {title}
      </text>
      {detail && (
        <text x={x + 18} y={midY + 25} fontFamily={UI} fontSize="12" fill={dark ? '#fff' : MUTED} opacity={dark ? 0.78 : 1}>
          {detail}
        </text>
      )}
    </g>
  )
}

function FlowArrow({ x1, y1, x2, y2, marker }: { x1: number; y1: number; x2: number; y2: number; marker: string }) {
  return <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={BLUE_MID} strokeWidth="1.5" markerEnd={`url(#${marker})`} />
}

function ArrowDefs({ id }: { id: string }) {
  return (
    <defs>
      <marker id={id} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
      </marker>
      <marker id={`${id}-muted`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L8,4 L0,8 z" fill={MUTED} />
      </marker>
    </defs>
  )
}

/* ---- 1 · System at a glance ---- */

function SystemOverview() {
  const stages = [
    { x: 30, w: 178, kicker: 'SOURCE', title: 'Public sources', detail: 'X · primary documents', tone: 'plain' as const },
    { x: 236, w: 178, kicker: 'PROCESS', title: 'Python pipeline', detail: 'collect · group · rank', tone: 'dark' as const },
    { x: 442, w: 178, kicker: 'STORE', title: 'SQLite', detail: 'raw · Registry · derived', tone: 'surface' as const },
    { x: 648, w: 188, kicker: 'SERVE', title: 'FastAPI + React', detail: 'typed API · built SPA', tone: 'plain' as const },
    { x: 864, w: 186, kicker: 'PUBLIC', title: 'Cloudflare Tunnel', detail: 'public reviewer URL', tone: 'plain' as const },
  ]
  return (
    <svg
      viewBox="0 0 1080 300"
      role="img"
      aria-label="Deployed architecture. Public X evidence and linked documents enter a Python pipeline, which preserves raw, canonical, and derived data in SQLite. Bounded routing calls go through LiteLLM, while final brief authoring runs through Codex App Server. FastAPI serves the typed API and built React application, and Cloudflare Tunnel exposes the public reviewer URL."
    >
      <ArrowDefs id="overview-arrow" />
      {stages.map((s) => (
        <Card key={s.kicker} x={s.x} y={34} w={s.w} kicker={s.kicker} title={s.title} detail={s.detail} tone={s.tone} />
      ))}
      <FlowArrow x1={210} y1={86} x2={232} y2={86} marker="overview-arrow" />
      <FlowArrow x1={416} y1={86} x2={438} y2={86} marker="overview-arrow" />
      <FlowArrow x1={622} y1={86} x2={644} y2={86} marker="overview-arrow" />
      <FlowArrow x1={838} y1={86} x2={860} y2={86} marker="overview-arrow" />

      {/* the two model boundaries hang off the pipeline */}
      <path d="M325 138 V172" fill="none" stroke={BLUE_MID} strokeWidth="1.4" markerEnd="url(#overview-arrow)" />
      <path d="M531 180 V146" fill="none" stroke={BLUE_MID} strokeWidth="1.4" markerEnd="url(#overview-arrow)" />
      <rect x="236" y="180" width="384" height="62" fill={SAND} stroke={BLUE_MID} strokeWidth="1.2" />
      <text x="254" y="205" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.08em">MODEL BOUNDARY</text>
      <text x="254" y="230" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>LiteLLM + Codex</text>
      <text x="406" y="230" fontFamily={UI} fontSize="11.5" fill={MUTED}>routing telemetry · editorial task</text>

      <line x1="30" y1="270" x2="1050" y2="270" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="292" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        Deterministic first. Every model judgment stays auditable. The same code restores a frozen local reviewer release.
      </text>
    </svg>
  )
}

/* ---- 2 · Models per task ---- */

const MODEL_TASKS = [
  {
    task: 'Entity classification',
    where: 'Registry intake',
    model: 'gpt-5.6-luna',
    effort: 'medium',
    why: 'Bounded structured decision with an evaluated classifier contract. The efficient model matched the larger one here.',
  },
  {
    task: 'Registry admission + identity research',
    where: 'Registry intake',
    model: 'gpt-5.6-luna',
    effort: 'high',
    why: 'Grounded multi-source identity resolution needs more checking than plain classification, so effort rises before model size does.',
  },
  {
    task: 'Audience routing',
    where: 'Judge stage',
    model: 'gpt-5.4-mini',
    effort: 'high',
    why: 'Evaluated on a 900-decision run with zero failures. A higher effort tier changed no decisions and used 5.4× the tokens.',
  },
  {
    task: 'Per-Event working annotations',
    where: 'Optional editorial input',
    model: 'gpt-5.6-terra',
    effort: 'high',
    why: 'A calibration pass produced audience-specific notes. The daily agent may inspect them, but must re-evaluate the frozen evidence and does not treat them as editorial truth.',
  },
  {
    task: 'FLI daily-intelligence agent',
    where: 'Final selection',
    model: 'gpt-5.6-sol',
    effort: 'xhigh',
    why: 'Free-running synthesis must compare the complete routed cohort, resolve duplication, and produce one defensible brief for each audience.',
  },
  {
    task: 'Registry relevance audit',
    where: 'One-time evaluation',
    model: 'gpt-5.6-terra',
    effort: 'high',
    why: 'Used once to audit the initial Registry with required web search. It does not run in the daily brief path and cannot mutate the Registry.',
  },
]

export function ModelTable({ tasks }: { tasks?: string[] } = {}) {
  const visibleTasks = tasks
    ? MODEL_TASKS.filter((row) => tasks.includes(row.task))
    : MODEL_TASKS

  return (
    <div className="model-table" role="table" aria-label="Model selection per task">
      <div className="model-table-row model-table-head" role="row">
        <span role="columnheader">Task</span>
        <span role="columnheader">Model · effort</span>
        <span role="columnheader">Why this one</span>
      </div>
      {visibleTasks.map((row) => (
        <div className="model-table-row" role="row" key={row.task}>
          <span role="cell" className="model-table-task">
            <strong>{row.task}</strong>
            <em className="mono">{row.where}</em>
          </span>
          <span role="cell" className="mono model-table-model">
            {row.model}
            <em>{row.effort}</em>
          </span>
          <span role="cell" className="model-table-why">{row.why}</span>
        </div>
      ))}
    </div>
  )
}

/* ---- 3 · The pipeline ---- */

function RosterGlyph({ x, y }: { x: number; y: number }) {
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
          <rect x={x + 16} y={y + i * 15 - 1.5} width={row.w} height={3} fill="#fff" opacity={0.5} />
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

function EventGlyph({ x, y }: { x: number; y: number }) {
  const kids = [y - 16, y, y + 16]
  return (
    <g>
      <rect x={x} y={y - 10} width={30} height={20} fill="#fff" stroke={BLUE_MID} strokeWidth="1.2" />
      {kids.map((ky) => (
        <g key={ky}>
          <line x1={x + 30} y1={y} x2={x + 68} y2={ky} stroke={MUTED} strokeWidth="1" opacity="0.5" />
          <rect x={x + 68} y={ky - 5.5} width={24} height={11} fill="#fff" stroke={MUTED} strokeWidth="1" opacity="0.75" />
        </g>
      ))}
    </g>
  )
}

function ArtifactGlyph({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y - 16} width={34} height={38} fill={SAND} stroke={BLUE_MID} strokeWidth="1.1" />
      <rect x={x + 46} y={y - 10} width={34} height={32} fill="#fff" stroke={MUTED} strokeWidth="1" />
      <line x1={x + 7} y1={y - 5} x2={x + 27} y2={y - 5} stroke={BLUE_MID} strokeWidth="2" />
      <line x1={x + 7} y1={y + 3} x2={x + 23} y2={y + 3} stroke={MUTED} strokeWidth="1" />
      <line x1={x + 53} y1={y + 1} x2={x + 73} y2={y + 1} stroke={MUTED} strokeWidth="1" />
      <line x1={x + 53} y1={y + 9} x2={x + 69} y2={y + 9} stroke={MUTED} strokeWidth="1" />
    </g>
  )
}

function AudienceGlyph({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y - 12} width={40} height={20} fill="none" stroke={BLUE} strokeWidth="1" />
      <rect x={x + 48} y={y - 12} width={40} height={20} fill="none" stroke={BLUE} strokeWidth="1" />
      <text x={x + 20} y={y + 2} textAnchor="middle" fontFamily={MONO} fontSize="8.5" fill="#fff">INV</text>
      <text x={x + 68} y={y + 2} textAnchor="middle" fontFamily={MONO} fontSize="8.5" fill="#fff">ENG</text>
      <text x={x} y={y + 26} fontFamily={MONO} fontSize="8" fill={BLUE} opacity="0.85">BOTH · ONE · NEITHER</text>
    </g>
  )
}

function EvidenceInputMap() {
  const stages = [
    { x: 28, kicker: 'WHO', title: 'Registry', glyph: 'roster', dark: true },
    { x: 234, kicker: 'SOURCE', title: 'X posts + threads', glyph: 'days', dark: false },
    { x: 440, kicker: 'STRUCTURE', title: 'Exact Events', glyph: 'event', dark: false },
    { x: 646, kicker: 'ENRICH', title: 'Source artifacts', glyph: 'artifact', dark: false },
    { x: 852, kicker: 'ROUTE', title: 'Audience relevance', glyph: 'audience', dark: true },
  ]
  return (
    <svg
      viewBox="0 0 1080 226"
      role="img"
      aria-label="Evidence input path. A screened Registry supplies dated X posts and threads. Exact Events disclose source artifacts before the complete evidence packet is routed independently for Investment and AI Engineering."
    >
      <ArrowDefs id="flow-arrow" />
      <text x="28" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">EVIDENCE INPUT · INSPECTABLE BEFORE JUDGMENT</text>
      {stages.map((stage) => (
        <g key={stage.title}>
          <rect x={stage.x} y="60" width="178" height="132" fill={stage.dark ? INK : '#fff'} stroke={stage.dark ? INK : BLUE_MID} strokeWidth="1.2" />
          <text x={stage.x + 18} y="86" fontFamily={MONO} fontSize="9.5" fill={stage.dark ? BLUE : BLUE_INK} letterSpacing="0.08em">{stage.kicker}</text>
          <text x={stage.x + 18} y="116" fontFamily={UI} fontSize={stage.title.length > 15 ? 15 : 17} fontWeight="600" fill={stage.dark ? '#fff' : INK}>{stage.title}</text>
          {stage.glyph === 'roster' && <RosterGlyph x={stage.x + 18} y={144} />}
          {stage.glyph === 'days' && <DaysGlyph x={stage.x + 18} y={158} />}
          {stage.glyph === 'event' && <EventGlyph x={stage.x + 18} y={158} />}
          {stage.glyph === 'artifact' && <ArtifactGlyph x={stage.x + 18} y={154} />}
          {stage.glyph === 'audience' && <AudienceGlyph x={stage.x + 18} y={150} />}
        </g>
      ))}
      <FlowArrow x1={206} y1={126} x2={230} y2={126} marker="flow-arrow" />
      <FlowArrow x1={412} y1={126} x2={436} y2={126} marker="flow-arrow" />
      <FlowArrow x1={618} y1={126} x2={642} y2={126} marker="flow-arrow" />
      <FlowArrow x1={824} y1={126} x2={848} y2={126} marker="flow-arrow" />
    </svg>
  )
}

function DailyIntelligenceMap() {
  const stages = [
    { x: 28, kicker: '1 · ROUTE', title: 'Audience routing', detail: 'one call · two judgments', tone: 'surface' as const },
    { x: 232, kicker: '2 · FREEZE', title: 'Daily workspace', detail: 'union-positive · seven days', tone: 'sand' as const },
    { x: 436, kicker: '3 · CODEX', title: 'FLI daily agent', detail: 'research · group · select', tone: 'dark' as const },
    { x: 640, kicker: '4 · VERIFY', title: 'Strict draft gate', detail: 'coverage · citations', tone: 'surface' as const },
    { x: 844, kicker: '5 · SERVE', title: 'Two daily briefs', detail: 'web · PDF · manual send', tone: 'plain' as const },
  ]
  return (
    <svg
      viewBox="0 0 1080 236"
      role="img"
      aria-label="Daily brief path. Audience routing returns two independent judgments per Event. The date is frozen into one immutable workspace, then one persisted FLI daily-intelligence Codex task researches the complete cohort and writes both briefs. Deterministic validation checks coverage and citations before the run is imported for the web reader, PDF, and manual delivery."
    >
      <ArrowDefs id="daily-arrow" />
      <text x="28" y="30" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">ONE DATE · ONE CHECKPOINTED DAILY RUN</text>
      {stages.map((stage) => (
        <Card key={stage.kicker} x={stage.x} y={54} w={180} h={108} kicker={stage.kicker} title={stage.title} detail={stage.detail} tone={stage.tone} />
      ))}
      <FlowArrow x1={208} y1={108} x2={228} y2={108} marker="daily-arrow" />
      <FlowArrow x1={412} y1={108} x2={432} y2={108} marker="daily-arrow" />
      <FlowArrow x1={616} y1={108} x2={636} y2={108} marker="daily-arrow" />
      <FlowArrow x1={820} y1={108} x2={840} y2={108} marker="daily-arrow" />
      <text x="426" y="44" fontFamily={MONO} fontSize="8.5" fill={BLUE_INK} textAnchor="middle">--launch-codex →</text>
      <line x1="28" y1="194" x2="1024" y2="194" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.4" />
      <text x="28" y="218" fontFamily={UI} fontSize="12" fill={MUTED}>
        Without --launch-codex, run-day stops after freezing the workspace. A retry resumes the same dated run.
      </text>
    </svg>
  )
}

/* ---- 4 · The data model ---- */

function CurrentDataModel() {
  const channels = [
    { cx: 245, label: '@karpathy', plane: 'X', role: 'DAILY EVIDENCE', daily: true },
    { cx: 540, label: 'github.com/karpathy', plane: 'GitHub', role: 'IDENTITY LINK', daily: false },
    { cx: 835, label: 'arXiv · A. Karpathy', plane: 'Papers', role: 'IDENTITY LINK', daily: false },
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
      aria-label="Current data model. One real-world entity can resolve to several channels. X supplies the scheduled daily evidence. GitHub and paper identities support entity resolution and may enter evidence when a first-party X post discloses a linked primary document."
    >
      <ArrowDefs id="data-arrow" />
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">ONE IDENTITY · MANY CHANNELS · ONE SCHEDULED SOURCE</text>

      <rect x="430" y="58" width="220" height="72" fill={INK} />
      <text x="450" y="88" fontFamily={MONO} fontSize="10" fill={BLUE}>ENTITY</text>
      <text x="450" y="116" fontFamily={UI} fontSize="17" fontWeight="600" fill="#fff">Andrej Karpathy</text>

      {channels.map((c) => (
        <line
          key={`fan-${c.plane}`}
          x1="540"
          y1="130"
          x2={c.cx}
          y2={CH_TOP - 6}
          stroke={c.daily ? BLUE_MID : MUTED}
          strokeWidth={c.daily ? 1.6 : 1.2}
          strokeDasharray={c.daily ? undefined : '5 5'}
          opacity={c.daily ? 1 : 0.55}
          markerEnd={c.daily ? 'url(#data-arrow)' : 'url(#data-arrow-muted)'}
        />
      ))}

      {channels.map((c) => (
        <g key={`chan-${c.plane}`} opacity={c.daily ? 1 : 0.72}>
          <rect
            x={c.cx - CW / 2}
            y={CH_TOP}
            width={CW}
            height={CH_H}
            fill="#fff"
            stroke={c.daily ? BLUE_MID : MUTED}
            strokeWidth="1.2"
            strokeDasharray={c.daily ? undefined : '5 5'}
          />
          <text x={c.cx - CW / 2 + 16} y={CH_TOP + 27} fontFamily={MONO} fontSize="10" fill={c.daily ? BLUE_INK : MUTED} letterSpacing="0.08em">
            {c.plane.toUpperCase()} · {c.role}
          </text>
          <text x={c.cx - CW / 2 + 16} y={CH_TOP + 54} fontFamily={UI} fontSize="15.5" fontWeight="600" fill={INK}>{c.label}</text>
        </g>
      ))}

      {channels.filter((channel) => channel.daily).map((c) => (
        <line key={`stream-${c.plane}`} x1={c.cx} y1={CH_TOP + CH_H} x2={c.cx} y2="306" stroke={BLUE_MID} strokeWidth="1.6" markerEnd="url(#data-arrow)" />
      ))}

      <rect x="90" y="312" width="900" height="110" fill={SURFACE} />
      <text x="116" y="342" fontFamily={MONO} fontSize="10" fill={BLUE_INK} letterSpacing="0.08em">PUBLISHED EVIDENCE</text>
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

function AccountIntake() {
  const stages = [
    { x: 34, title: 'X handle', detail: 'one supplied account', tone: 'dark' as const },
    { x: 272, title: 'Profile gate', detail: 'public · collectable', tone: 'sand' as const },
    { x: 510, title: 'Resolve identity', detail: 'person · organization', tone: 'plain' as const },
    { x: 748, title: 'Registry', detail: 'tracked from now on', tone: 'dark' as const },
  ]
  return (
    <svg viewBox="0 0 1080 306" role="img" aria-label="A supplied X handle passes a profile gate and identity resolution before entering the Registry; either checkpoint can reject it, and the rejection reason is kept">
      <ArrowDefs id="intake-arrow" />
      <text x="34" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">WHEN AN X ACCOUNT IS SUPPLIED</text>
      {stages.map((stage, index) => (
        <g key={stage.title}>
          <Card x={stage.x} y={70} w={190} h={100} title={stage.title} detail={stage.detail} tone={stage.tone} />
          {index < stages.length - 1 && (
            <FlowArrow x1={stage.x + 190} y1={120} x2={stages[index + 1].x - 8} y2={120} marker="intake-arrow" />
          )}
        </g>
      ))}
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

/* ---- 5 · The numbers ---- */

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
            <strong>Tracked amplification</strong> counts every screened Registry member, person or
            organization, exactly once per post: Andrej Karpathy and the newest
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
    <section className="system-view arch-page" aria-labelledby="architecture-title">
      <h2 className="system-view-title" id="architecture-title">Architecture</h2>
      <p className="page-sub">A technical map of the current implementation: the stack, the models, the pipeline, and the meaning of each number.</p>

      <nav className="ruled-nav arch-chapters" aria-label="Architecture chapters">
        <a href="#overview">Overview</a>
        <a href="#models">Models</a>
        <a href="#pipeline">Pipeline</a>
        <a href="#data-model">Data model</a>
        <a href="#ranking-methods">Numbers</a>
      </nav>

      <section className="arch-section arch-section--lead" id="overview">
        <div className="arch-section-head">
          <h2 className="arch-h">System at a glance</h2>
          <p className="arch-p">The deployed stack in one view, from public evidence to the hosted reviewer interface. Every section below drills into one part of this picture.</p>
        </div>
        <div className="arch-canvas"><SystemOverview /></div>
      </section>

      <section className="arch-section" id="models">
        <div className="arch-section-head">
          <h2 className="arch-h">One model per task, chosen by evidence</h2>
          <p className="arch-p">Bounded pipeline calls go through LiteLLM, which records the model, tokens, cache reads, and request cost. Final brief authoring runs as a persisted Codex App Server task with its effective model, effort, tier, and thread attached to the editorial run. Defaults come from comparisons on real workloads, not from picking the biggest model.</p>
        </div>
        <div className="arch-canvas arch-canvas--methods"><ModelTable /></div>
        <p className="arch-note">Measured, not estimated: the per-Event annotation batch averaged $0.01638 per surface-or-suppress decision, with 1.76M tokens served from prompt cache across the batch. That was working-note and calibration spend, not the cost of the final daily briefs. Each immutable run keeps its own exact model, prompt version, and cost telemetry, so changing a default never relabels old results.</p>
      </section>

      <section className="arch-section" id="pipeline">
        <div className="arch-section-head">
          <h2 className="arch-h">The evidence-to-insight path</h2>
          <p className="arch-p">The deterministic path ends with two audience-routing judgments per Event. For each date, the runner freezes the union-positive cohort and can hand that exact workspace to one persisted FLI daily-intelligence task. The agent researches the complete day and writes one validated draft containing both audience briefs.</p>
        </div>
        <div className="arch-canvas"><EvidenceInputMap /></div>
        <div className="arch-canvas arch-canvas--sub"><DailyIntelligenceMap /></div>
      </section>

      <section className="arch-section" id="data-model">
        <div className="arch-section-head">
          <h2 className="arch-h">The data model</h2>
          <p className="arch-p">The Registry resolves several channels to one identity. X supplies scheduled daily evidence; linked primary documents enter through Artifacts. A supplied account passes an auditable gate before it is tracked.</p>
        </div>
        <div className="arch-canvas"><CurrentDataModel /></div>
        <div className="arch-canvas arch-canvas--sub"><AccountIntake /></div>
      </section>

      <section className="arch-section arch-section--methods" id="ranking-methods">
        <div className="arch-section-head">
          <h2 className="arch-h">The numbers answer different questions</h2>
          <p className="arch-p">Reach, network support, and the daily score answer different questions so none can masquerade as quality.</p>
        </div>
        <div className="arch-canvas arch-canvas--methods"><RankingMethods /></div>
        <div className="arch-canvas arch-canvas--sub"><NetworkRankFigure /></div>
      </section>
    </section>
  )
}
