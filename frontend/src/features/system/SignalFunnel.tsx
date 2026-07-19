/* SignalFunnel — the How-it-works hero. One cone of progressive
   signal-to-noise refinement, told as a visual story:

   Overview (stage null / 'universe'): the problem statement. A vast pale
   field of dots at the top, a ghost cone with nothing inside, and the two
   briefs waiting at the tip. The figure poses the question: how does
   everything become exactly these two documents?

   Focused stages ('watch' … 'publish'): the answer, revealed one plane at
   a time. Planes at or above the focus are solved and visible; planes
   below stay ghosts, so the machine appears to build itself as the reader
   moves through the story. A gentle camera pan/zoom keeps the focused
   plane centered.

   Visual vocabulary matches /network/ranking: phyllotaxis dot fields,
   circle = person/post, square = organization, dashed hairlines, mono
   labels with white halos. Concept-first: no counts, no telemetry. */

export type FunnelStage =
  | 'universe'
  | 'watch'
  | 'collect'
  | 'rank'
  | 'judge'
  | 'publish'

const INK = '#151515'
const INK_SOFT = '#434343'
const MUTED = '#6b6b68'
const PALE = '#c9c9c6'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
const MONO = "'IBM Plex Mono', ui-monospace, monospace"

const GOLDEN = Math.PI * (3 - Math.sqrt(5))

const W = 520
const CX = 195

const STAGE_ORDER: FunnelStage[] = [
  'universe',
  'watch',
  'collect',
  'rank',
  'judge',
  'publish',
]

type Plane = {
  id: FunnelStage
  y: number
  rx: number
  ry: number
  dots: number
  step: string
  name: string
  concept: string
  detail: string
}

/* Vertical rhythm: planes shrink as noise is removed. Labels carry the
   concept, never the numbers. */
const PLANES: Plane[] = [
  {
    id: 'universe',
    y: 78,
    rx: 172,
    ry: 46,
    dots: 190,
    step: '',
    name: 'Everything public',
    concept: 'everyone, posting about everything',
    detail: 'almost all of it is noise',
  },
  {
    id: 'watch',
    y: 190,
    rx: 132,
    ry: 35,
    dots: 105,
    step: '1',
    name: 'Choose',
    concept: 'a screened cohort of labs and people',
    detail: 'decide who is worth listening to',
  },
  {
    id: 'collect',
    y: 288,
    rx: 100,
    ry: 26.5,
    dots: 62,
    step: '2',
    name: 'Collect',
    concept: 'their output, grouped into exact Events',
    detail: 'plus the primary sources they cite',
  },
  {
    id: 'rank',
    y: 372,
    rx: 72,
    ry: 19,
    dots: 34,
    step: '3',
    name: 'Rank',
    concept: 'a transparent attention score',
    detail: 'decides where to look first',
  },
  {
    id: 'judge',
    y: 443,
    rx: 48,
    ry: 12.5,
    dots: 16,
    step: '4',
    name: 'Judge',
    concept: 'two questions asked of every Event',
    detail: 'relevant to investors? to engineers?',
  },
  {
    id: 'publish',
    y: 500,
    rx: 26,
    ry: 7,
    dots: 5,
    step: '5',
    name: 'Publish',
    concept: 'only what clears the bar',
    detail: 'every claim cited to its source',
  },
]

const TIP_Y = 540
const FORK_Y = 574
const H = 636

/* Deterministic phyllotaxis field inside an ellipse — same construction as
   the network orbit, so the two figures read as one system. `d` is depth:
   1 = front rim (near the viewer), 0 = back rim. Dots shrink and fade as
   they recede, which is what makes each plane read as a tilted 3D disc. */
function field(plane: Plane) {
  const pts: { x: number; y: number; t: number; d: number; i: number }[] = []
  for (let i = 0; i < plane.dots; i += 1) {
    const angle = i * GOLDEN
    const radius = Math.sqrt((i + 0.55) / plane.dots) * 0.94
    const d = (Math.sin(angle) * radius + 1) / 2
    pts.push({
      x: CX + Math.cos(angle) * radius * plane.rx,
      y: plane.y + Math.sin(angle) * radius * plane.ry,
      t: 1 - radius,
      d,
      i,
    })
  }
  /* Paint back-to-front so near dots overlap far ones. */
  return pts.sort((a, b) => a.d - b.d)
}

/* Perspective scale and atmospheric fade for one dot. */
const persp = (d: number) => 0.72 + 0.42 * d
const fade = (d: number) => 0.5 + 0.5 * d

function PlaneDots({ plane }: { plane: Plane }) {
  const pts = field(plane)

  if (plane.id === 'universe') {
    return (
      <>
        {pts.map((p) => (
          <circle
            key={p.i}
            cx={p.x}
            cy={p.y}
            r={1.5 * persp(p.d)}
            fill={PALE}
            opacity={fade(p.d)}
          />
        ))}
      </>
    )
  }

  if (plane.id === 'watch') {
    /* The screened cohort: mostly people (ink circles), some organizations
       (blue squares) — the Registry vocabulary. */
    return (
      <>
        {pts.map((p) => {
          const s = 4.4 * persp(p.d)
          return p.i % 13 === 5 ? (
            <rect
              key={p.i}
              x={p.x - s / 2}
              y={p.y - s / 2}
              width={s}
              height={s}
              fill={BLUE_MID}
              opacity={fade(p.d)}
            />
          ) : (
            <circle
              key={p.i}
              cx={p.x}
              cy={p.y}
              r={1.8 * persp(p.d)}
              fill={INK}
              opacity={fade(p.d)}
            />
          )
        })}
      </>
    )
  }

  if (plane.id === 'collect') {
    return (
      <>
        {pts.map((p) => (
          <circle
            key={p.i}
            cx={p.x}
            cy={p.y}
            r={1.9 * persp(p.d)}
            fill={INK}
            opacity={fade(p.d)}
          />
        ))}
      </>
    )
  }

  if (plane.id === 'rank') {
    /* Ordered: size now encodes the day's attention score, biggest first. */
    return (
      <>
        {pts.map((p) => (
          <circle
            key={p.i}
            cx={p.x}
            cy={p.y}
            r={(1.4 + 2.6 * Math.pow(p.t, 1.5)) * persp(p.d)}
            fill={INK}
            opacity={fade(p.d)}
          />
        ))}
      </>
    )
  }

  if (plane.id === 'judge') {
    /* Filled = relevant to an audience, hollow = explicitly not. */
    return (
      <>
        {pts.map((p) =>
          p.i % 5 === 3 ? (
            <circle
              key={p.i}
              cx={p.x}
              cy={p.y}
              r={2 * persp(p.d)}
              fill="#ffffff"
              stroke={MUTED}
              strokeWidth={1}
              opacity={fade(p.d)}
            />
          ) : (
            <circle
              key={p.i}
              cx={p.x}
              cy={p.y}
              r={2.3 * persp(p.d)}
              fill={INK}
              opacity={fade(p.d)}
            />
          ),
        )}
      </>
    )
  }

  /* publish: the few that clear the audience bar. */
  return (
    <>
      {pts.map((p) => (
        <circle
          key={p.i}
          cx={p.x}
          cy={p.y}
          r={2.6 * persp(p.d)}
          fill={BLUE}
          stroke={BLUE_INK}
          strokeWidth={0.9}
          opacity={0.75 + 0.25 * p.d}
        />
      ))}
    </>
  )
}

function Brief({ x, label, lit }: { x: number; label: string; lit: boolean }) {
  const w = 118
  const h = 44
  return (
    <g opacity={lit ? 1 : 0.45} style={{ transition: 'opacity 500ms ease-out' }}>
      <rect
        x={x - w / 2}
        y={FORK_Y}
        width={w}
        height={h}
        fill="#ffffff"
        stroke={lit ? BLUE_MID : INK}
        strokeWidth={lit ? 1.4 : 1}
        strokeDasharray={lit ? undefined : '3 4'}
      />
      {/* document rule lines */}
      <line x1={x - w / 2 + 12} y1={FORK_Y + 26} x2={x + w / 2 - 12} y2={FORK_Y + 26} stroke={PALE} strokeWidth={1} />
      <line x1={x - w / 2 + 12} y1={FORK_Y + 34} x2={x + w / 2 - 30} y2={FORK_Y + 34} stroke={PALE} strokeWidth={1} />
      <text
        x={x}
        y={FORK_Y + 17}
        textAnchor="middle"
        fontFamily={MONO}
        fontSize="8.5"
        fontWeight="600"
        letterSpacing="0.08em"
        fill={lit ? BLUE_INK : INK_SOFT}
      >
        {label}
      </text>
    </g>
  )
}

/* A plane directly above or below the focus keeps a whisper of presence so
   the camera move stays legible. */
function isAdjacent(id: FunnelStage, active: FunnelStage | null) {
  if (!active) return false
  return Math.abs(STAGE_ORDER.indexOf(active) - STAGE_ORDER.indexOf(id)) === 1
}

export default function SignalFunnel({ active }: { active: FunnelStage | null }) {
  const overview = active == null || active === 'universe'
  const focusIdx = overview ? 0 : STAGE_ORDER.indexOf(active)

  const revealed = (id: FunnelStage) =>
    overview ? id === 'universe' : STAGE_ORDER.indexOf(id) <= focusIdx
  const publishOn = !overview && active === 'publish'

  /* Camera: each focused stage gets a precomputed pan/zoom that keeps the
     plane and its right-edge label inside the frame. */
  const FOCUS: Record<FunnelStage, { fx: number; fy: number; s: number }> = {
    universe: { fx: CX, fy: 0, s: 1 },
    watch: { fx: 262, fy: 178, s: 1.18 },
    collect: { fx: 268, fy: 270, s: 1.3 },
    rank: { fx: 252, fy: 352, s: 1.42 },
    judge: { fx: 268, fy: 420, s: 1.46 },
    publish: { fx: 228, fy: 512, s: 1.34 },
  }
  const cam = FOCUS[active ?? 'universe']
  const zoomed = cam.s > 1
  const tx = zoomed ? W / 2 - cam.s * cam.fx : 0
  const ty = zoomed ? H * 0.42 - cam.s * cam.fy : 0

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="The signal funnel: from everything published publicly, a screened cohort chooses what to collect, exact Events are ranked, judged for two audiences, and distilled into two daily cited briefs."
      className="signal-funnel"
    >
      <g
        style={{
          transform: `translate(${tx}px, ${ty}px) scale(${cam.s})`,
          transition: 'transform 800ms cubic-bezier(0.22, 1, 0.36, 1)',
        }}
      >
        {/* cone silhouette: dashed hairlines connecting the plane edges */}
        {PLANES.slice(0, -1).map((p, i) => {
          const q = PLANES[i + 1]
          return (
            <g
              key={p.id}
              stroke={INK}
              strokeOpacity={revealed(q.id) ? 0.26 : 0.12}
              strokeDasharray="2 5"
              strokeWidth="1"
              style={{ transition: 'stroke-opacity 500ms ease-out' }}
            >
              <line x1={CX - p.rx} y1={p.y} x2={CX - q.rx} y2={q.y} />
              <line x1={CX + p.rx} y1={p.y} x2={CX + q.rx} y2={q.y} />
            </g>
          )
        })}
        {/* tip of the cone */}
        {(() => {
          const last = PLANES[PLANES.length - 1]
          return (
            <g
              stroke={INK}
              strokeOpacity={revealed('publish') ? 0.26 : 0.12}
              strokeDasharray="2 5"
              strokeWidth="1"
              style={{ transition: 'stroke-opacity 500ms ease-out' }}
            >
              <line x1={CX - last.rx} y1={last.y} x2={CX} y2={TIP_Y} />
              <line x1={CX + last.rx} y1={last.y} x2={CX} y2={TIP_Y} />
            </g>
          )
        })()}

        {/* the goal, always present: two audience briefs leave the tip */}
        <g stroke={BLUE_MID} strokeWidth="1.1" fill="none">
          <path
            d={`M ${CX} ${TIP_Y} Q ${CX} ${FORK_Y - 10} ${CX - 74} ${FORK_Y - 2}`}
            opacity={publishOn || overview ? 0.9 : 0.3}
            style={{ transition: 'opacity 500ms ease-out' }}
          />
          <path
            d={`M ${CX} ${TIP_Y} Q ${CX} ${FORK_Y - 10} ${CX + 74} ${FORK_Y - 2}`}
            opacity={publishOn || overview ? 0.9 : 0.3}
            style={{ transition: 'opacity 500ms ease-out' }}
          />
        </g>
        <Brief x={CX - 74} label="INVESTMENT" lit={publishOn || overview} />
        <Brief x={CX + 74} label="AI ENGINEERING" lit={publishOn || overview} />

        {/* planes: back rim behind the dots, solid front rim in front */}
        {PLANES.map((plane) => {
          const on = revealed(plane.id)
          const isActive = !overview && active === plane.id
          const labelX = CX + plane.rx + 14
          const backArc = `M ${CX - plane.rx} ${plane.y} A ${plane.rx} ${plane.ry} 0 0 1 ${CX + plane.rx} ${plane.y}`
          const frontArc = `M ${CX - plane.rx} ${plane.y} A ${plane.rx} ${plane.ry} 0 0 0 ${CX + plane.rx} ${plane.y}`
          return (
            <g
              key={plane.id}
              opacity={on ? 1 : isAdjacent(plane.id, active) ? 0.3 : 0.18}
              style={{ transition: 'opacity 600ms ease-out' }}
            >
              {/* disc surface wash */}
              <ellipse
                cx={CX}
                cy={plane.y}
                rx={plane.rx}
                ry={plane.ry}
                fill={isActive ? 'rgba(91, 197, 242, 0.10)' : 'rgba(21, 21, 21, 0.025)'}
                style={{ transition: 'fill 500ms ease-out' }}
              />
              {/* back rim: fainter, dashed, hidden behind the dot field */}
              <path
                d={backArc}
                fill="none"
                stroke={isActive ? BLUE_MID : INK}
                strokeOpacity={isActive ? 0.4 : 0.16}
                strokeWidth={1}
                strokeDasharray="2 5"
              />
              {on && <PlaneDots plane={plane} />}
              {/* front rim: solid, closer to the viewer, drawn over the dots */}
              <path
                d={frontArc}
                fill="none"
                stroke={isActive ? BLUE_MID : INK}
                strokeOpacity={isActive ? 0.95 : 0.42}
                strokeWidth={isActive ? 1.4 : 1}
                style={{ transition: 'stroke 500ms ease-out' }}
              />
              {/* stage label, anchored to the plane's right edge */}
              <g
                fontFamily={MONO}
                stroke="#ffffff"
                strokeWidth="3.5"
                paintOrder="stroke"
                opacity={on ? 1 : 0}
                style={{ transition: 'opacity 500ms ease-out' }}
              >
                <text
                  x={labelX}
                  y={plane.y - 4}
                  fontSize="10.5"
                  fontWeight="600"
                  letterSpacing="0.06em"
                  fill={isActive ? BLUE_INK : INK}
                >
                  {plane.step ? `${plane.step} · ${plane.name.toUpperCase()}` : plane.name.toUpperCase()}
                </text>
                <text x={labelX} y={plane.y + 9} fontSize="9" fill={INK_SOFT}>
                  {plane.concept}
                </text>
                <text x={labelX} y={plane.y + 21} fontSize="8.5" fill={MUTED}>
                  {plane.detail}
                </text>
              </g>
            </g>
          )
        })}

        {/* overview only: the open question inside the ghost cone */}
        <g
          opacity={overview ? 1 : 0}
          style={{ transition: 'opacity 500ms ease-out' }}
          fontFamily={MONO}
          stroke="#ffffff"
          strokeWidth="4"
          paintOrder="stroke"
        >
          <text x={CX} y={316} textAnchor="middle" fontSize="14" fontWeight="600" fill={INK_SOFT}>
            ?
          </text>
          <text x={CX} y={338} textAnchor="middle" fontSize="8.5" fill={MUTED}>
            how does all of that become
          </text>
          <text x={CX} y={350} textAnchor="middle" fontSize="8.5" fill={MUTED}>
            exactly these two briefs
          </text>
        </g>
      </g>
    </svg>
  )
}
