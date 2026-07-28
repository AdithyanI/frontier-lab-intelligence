import { useEffect } from 'react'
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

/* ---- 2 · Current model boundaries ---- */

const DAILY_MODEL_BOUNDARIES = [
  {
    task: 'Audience routing',
    where: 'LiteLLM',
    model: 'gpt-5.4-mini',
    effort: 'high',
    why: 'A 900-decision evaluation completed without failures. The xhigh comparison changed no decisions and used 5.4× the tokens.',
  },
  {
    task: 'FLI daily-intelligence agent',
    where: 'Codex App Server',
    model: 'gpt-5.6-sol',
    effort: 'xhigh',
    why: 'Submitted runs recorded this effective setting. This is the only stage that researches the complete cohort, resolves duplication, and writes both briefs.',
  },
]

export function ModelTable({ tasks }: { tasks?: string[] } = {}) {
  const visibleTasks = tasks
    ? DAILY_MODEL_BOUNDARIES.filter((row) => tasks.includes(row.task))
    : DAILY_MODEL_BOUNDARIES

  return (
    <div className="model-table" role="table" aria-label="Daily brief model boundaries">
      <div className="model-table-row model-table-head" role="row">
        <span role="columnheader">Boundary</span>
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
  const dots = Array.from({ length: 7 }, (_, i) => x + 6 + i * 17)
  return (
    <g>
      <line x1={x} y1={y} x2={x + 116} y2={y} stroke={MUTED} strokeWidth="1" opacity="0.45" />
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

function RankGlyph({ x, y }: { x: number; y: number }) {
  const rows = [64, 48, 34]
  return (
    <g>
      {rows.map((width, index) => (
        <g key={width}>
          <text x={x} y={y + index * 17} fontFamily={MONO} fontSize="8.5" fill={BLUE_INK}>{index + 1}</text>
          <rect x={x + 18} y={y + index * 17 - 7} width={width} height={7} fill={index === 0 ? BLUE : SURFACE} stroke={BLUE_MID} strokeWidth="1" />
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

export function EvidenceInputMap({
  includeDailyOutcome = false,
}: {
  includeDailyOutcome?: boolean
} = {}) {
  const stages = [
    { x: 28, kicker: 'WHO', title: 'Registry', glyph: 'roster', dark: true },
    { x: 202, kicker: 'SOURCE', title: 'X output', glyph: 'days', dark: false },
    { x: 376, kicker: 'STRUCTURE', title: 'Exact Events', glyph: 'event', dark: false },
    { x: 550, kicker: 'ORDER', title: 'Daily rank', glyph: 'rank', dark: false },
    { x: 724, kicker: 'ENRICH', title: 'Artifacts', glyph: 'artifact', dark: false },
    { x: 898, kicker: 'JUDGE', title: 'Audience routing', glyph: 'audience', dark: true },
  ]
  const stageWidth = 154
  return (
    <svg
      viewBox={includeDailyOutcome ? '0 0 1080 420' : '0 0 1080 226'}
      role="img"
      aria-label={includeDailyOutcome
        ? 'Daily intelligence path. A screened Registry supplies dated X output. The system preserves exact Events, groups same-artifact posts into Developments, orders the day, and routes each Development for Investment and AI Engineering. Evidence relevant to either audience can then pass to the FLI daily agent.'
        : 'Evidence input path. A screened Registry supplies dated X output. The system preserves exact Events, groups same-artifact posts into Developments, and orders the day before any audience judgment.'}
    >
      <ArrowDefs id="flow-arrow" />
      <text x="28" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">EVIDENCE INPUT · INSPECTABLE BEFORE JUDGMENT</text>
      {stages.map((stage) => (
        <g key={stage.title}>
          <rect x={stage.x} y="60" width={stageWidth} height="132" fill={stage.dark ? INK : '#fff'} stroke={stage.dark ? INK : BLUE_MID} strokeWidth="1.2" />
          <text x={stage.x + 18} y="86" fontFamily={MONO} fontSize="9.5" fill={stage.dark ? BLUE : BLUE_INK} letterSpacing="0.08em">{stage.kicker}</text>
          <text x={stage.x + 18} y="116" fontFamily={UI} fontSize={stage.title.length > 15 ? 15 : 17} fontWeight="600" fill={stage.dark ? '#fff' : INK}>{stage.title}</text>
          {stage.glyph === 'roster' && <RosterGlyph x={stage.x + 18} y={144} />}
          {stage.glyph === 'days' && <DaysGlyph x={stage.x + 18} y={158} />}
          {stage.glyph === 'event' && <EventGlyph x={stage.x + 18} y={158} />}
          {stage.glyph === 'rank' && <RankGlyph x={stage.x + 18} y={148} />}
          {stage.glyph === 'artifact' && <ArtifactGlyph x={stage.x + 18} y={154} />}
          {stage.glyph === 'audience' && <AudienceGlyph x={stage.x + 18} y={150} />}
        </g>
      ))}
      {stages.slice(0, -1).map((stage, index) => (
        <FlowArrow
          key={`${stage.title}-arrow`}
          x1={stage.x + stageWidth}
          y1={126}
          x2={stages[index + 1].x - 4}
          y2={126}
          marker="flow-arrow"
        />
      ))}
      {includeDailyOutcome && (
        <>
          <text x="28" y="244" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">AFTER ROUTING · ONE DAILY EDITORIAL PASS</text>
          <path
            d="M975 192 V252 H385 V276"
            fill="none"
            stroke={BLUE_MID}
            strokeWidth="1.5"
            strokeDasharray="4 5"
            markerEnd="url(#flow-arrow)"
          />
          <Card
            x={260}
            y={280}
            w={250}
            h={108}
            kicker="AGENT"
            title="FLI daily agent"
            detail="research · group · select · write"
            tone="dark"
          />
          <FlowArrow x1={510} y1={334} x2={566} y2={334} marker="flow-arrow" />
          <Card
            x={570}
            y={280}
            w={250}
            h={108}
            kicker="OUTCOME"
            title="Two daily briefs"
            detail="Investment · AI Engineering"
          />
        </>
      )}
    </svg>
  )
}

function DailyIntelligenceMap() {
  const stages = [
    { x: 28, kicker: '1 · FREEZE', title: 'Daily workspace', detail: 'union-positive · seven days', tone: 'surface' as const },
    { x: 232, kicker: '2 · HAND OFF', title: 'Persisted Codex task', detail: 'one date · one task', tone: 'sand' as const },
    { x: 436, kicker: '3 · AUTHOR', title: 'FLI daily agent', detail: 'research · group · select', tone: 'dark' as const },
    { x: 640, kicker: '4 · VERIFY', title: 'Strict draft gate', detail: 'coverage · citations', tone: 'surface' as const },
    { x: 844, kicker: '5 · SERVE', title: 'Two daily briefs', detail: 'web · PDF · manual send', tone: 'plain' as const },
  ]
  return (
    <svg
      viewBox="0 0 1080 236"
      role="img"
      aria-label="Daily brief path. The union-positive audience-routing cohort is frozen into one immutable workspace. One persisted Codex task runs the FLI daily-intelligence agent, which researches the complete cohort and writes both briefs. Deterministic validation checks coverage and citations before the run is imported for the web reader, PDF, and manual delivery."
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
      <text x="222" y="44" fontFamily={MONO} fontSize="8.5" fill={BLUE_INK} textAnchor="middle">--launch-codex →</text>
      <line x1="28" y1="194" x2="1024" y2="194" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.4" />
      <text x="28" y="218" fontFamily={UI} fontSize="12" fill={MUTED}>
        Without --launch-codex, run-day stops after freezing the workspace. A retry resumes the same dated run.
      </text>
    </svg>
  )
}

const RECOVERY_BOUNDARIES = [
  {
    boundary: 'Bounded model calls',
    response: 'LiteLLM handles retries, backoff, and provider fallback. Invalid structured output never becomes a judgment.',
    invariant: 'The prompt version, input hash, and completed rows stay fixed.',
  },
  {
    boundary: 'Daily editorial run',
    response: 'The runner restarts from the last completed checkpoint and resumes the same persisted Codex task.',
    invariant: 'The date, workspace, model settings, and task identity stay fixed.',
  },
  {
    boundary: 'Draft validation',
    response: 'An incomplete disposition or unmatched artifact excerpt rejects the draft before import.',
    invariant: 'No partial brief replaces the last complete product state.',
  },
]

function RecoveryTable() {
  return (
    <div className="recovery-table" role="table" aria-label="Failure and recovery boundaries">
      <div className="recovery-table-row recovery-table-head" role="row">
        <span role="columnheader">Boundary</span>
        <span role="columnheader">What happens</span>
        <span role="columnheader">What stays fixed</span>
      </div>
      {RECOVERY_BOUNDARIES.map((row) => (
        <div className="recovery-table-row" role="row" key={row.boundary}>
          <strong role="cell">{row.boundary}</strong>
          <span role="cell">{row.response}</span>
          <span role="cell">{row.invariant}</span>
        </div>
      ))}
    </div>
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
    <div className="methodology" aria-label="Current ranking methods">
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
          <div className="method-equation mono">support = distinct active Registry entities following any represented X account · self excluded · tied counts share one percentile</div>
        </div>
        <p className="method-limit">Registry shows N / voter denominator. Ranking keeps the global account discovery order. Neither is relevance.</p>
      </div>
      <div className="method-row method-row--rank">
        <div className="method-id mono"><span>DAILY-DEVELOPMENT-RANK-V1</span><strong>Development rank</strong></div>
        <div className="method-main">
          <p className="method-question">How is evidence ordered within one observed day?</p>
          <div className="method-equation method-equation--large mono">trusted participants → mean participant position → public interactions → Development ID</div>
          <div className="method-weight" aria-label="Daily Development ranking layers">
            <div className="method-weight-network"><b>1</b><span>distinct trusted participants</span></div>
            <div className="method-weight-origin"><b>2</b><span>participant-position tie</span></div>
            <div className="method-weight-public"><b>3–4</b><span>public then stable ID</span></div>
          </div>
          <p className="method-explain">
            <strong>Trusted participants</strong> are the union of distinct active
            Registry entities that authored an original post, quoted it, or reposted
            any source inside the complete Development. Each entity counts once.
            <strong>Network position</strong> breaks equal-participant ties using
            the mean position of those participants. It is the share of all other
            ranked Registry entities with strictly lower entity-union support;
            equal support receives an equal position.
            <strong>Public interactions</strong> use the largest same-day single-post
            sum of likes, replies, reposts, and quotes. Development ID makes a full
            tie deterministic.
          </p>
        </div>
        <p className="method-limit">The Feed groups exact Events only through a shared release-specific artifact. It preserves every original post underneath, binds exact rank inputs, and remains unavailable without current network analysis.</p>
      </div>
    </div>
  )
}

export default function Architecture() {
  useEffect(() => {
    const id = window.location.hash.replace('#', '')
    if (!id) return
    requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ block: 'start' })
    })
  }, [])

  return (
    <section className="system-view arch-page" aria-labelledby="architecture-title">
      <h2 className="system-view-title" id="architecture-title">Architecture</h2>
      <p className="page-sub">Start with one completed day, then open the stack, model boundaries, data model, ranking, and recovery behavior behind it.</p>

      <nav className="ruled-nav arch-chapters" aria-label="Architecture chapters">
        <a href="#overview">Daily run</a>
        <a href="#stack">Stack</a>
        <a href="#models">Models</a>
        <a href="#data-model">Data model</a>
        <a href="#ranking-methods">Numbers</a>
        <a href="#recovery">Recovery</a>
      </nav>

      <section className="arch-section arch-section--lead" id="overview">
        <div className="arch-section-head">
          <h2 className="arch-h">One completed day, end to end</h2>
          <p className="arch-p">The system collects X output from the screened Registry, preserves exact Events, groups same-artifact posts into Developments, and orders the day. Audience judgment and daily-brief generation remain separate downstream stages. Nothing is published or sent until a complete draft passes deterministic validation.</p>
        </div>
        <div className="arch-canvas"><EvidenceInputMap /></div>
        <div className="arch-canvas arch-canvas--sub"><DailyIntelligenceMap /></div>
      </section>

      <section className="arch-section" id="stack">
        <div className="arch-section-head">
          <h2 className="arch-h">The deployed system underneath it</h2>
          <p className="arch-p">One Python pipeline owns collection, transformation, and orchestration. SQLite preserves raw evidence and every derived decision. FastAPI and React expose the same stored state through the reviewer interface, while LiteLLM and Codex App Server remain explicit model boundaries.</p>
        </div>
        <div className="arch-canvas"><SystemOverview /></div>
      </section>

      <section className="arch-section" id="models">
        <div className="arch-section-head">
          <h2 className="arch-h">Two model boundaries produce each daily brief</h2>
          <p className="arch-p">Audience routing is one structured LiteLLM call per Event. Final selection and writing run once for the complete day as a persisted Codex App Server task.</p>
        </div>
        <div className="arch-canvas arch-canvas--methods"><ModelTable /></div>
        <p className="arch-note">Registry intake runs separately from daily brief generation: <code>gpt-5.6-luna</code> at medium classifies entity kind, while high handles admission and identity research. The system stores the effective model and run identity at each boundary; LiteLLM also records prompt, token, cache, latency, and cost telemetry.</p>
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
          <p className="arch-p">Reach, network support, and the daily Development rank answer different questions so none can masquerade as quality.</p>
        </div>
        <div className="arch-canvas arch-canvas--methods"><RankingMethods /></div>
        <div className="arch-canvas arch-canvas--sub"><NetworkRankFigure /></div>
      </section>

      <section className="arch-section arch-section--methods" id="recovery">
        <div className="arch-section-head">
          <h2 className="arch-h">Failure recovery preserves the run</h2>
          <p className="arch-p">Retries may continue work, but they cannot silently change the evidence or model settings. A daily brief enters product state only after one complete, validated import.</p>
        </div>
        <div className="arch-canvas arch-canvas--methods"><RecoveryTable /></div>
      </section>
    </section>
  )
}
