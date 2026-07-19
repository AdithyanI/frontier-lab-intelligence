/* SignalFunnel — the How-it-works hero. One cone of progressive
   signal-to-noise refinement, told as a visual story:

   Overview (stage null / 'universe'): the problem statement. A borderless
   field of pale dots bleeding past the frame at the top — the universe is
   not a shape, it is everything — with a few faintly darker dots buried in
   it (the useful information) and one dashed focus ring: the decision to
   look here. The ghost cone hangs from that ring, and the two briefs wait
   at the tip. The figure poses the question: how does all of that become
   exactly these two documents?

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
  | 'complete'

const INK = '#151515'
const INK_SOFT = '#434343'
const MUTED = '#6b6b68'
const PALE = '#c9c9c6'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
const MONO = "'IBM Plex Mono', ui-monospace, monospace"

const GOLDEN = Math.PI * (3 - Math.sqrt(5))

const W = 560
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
    rx: 132,
    ry: 35,
    dots: 190,
    step: '',
    name: 'Everything public',
    concept: 'everyone, about everything',
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
    concept: 'output grouped into exact Events',
    detail: 'and the sources they cite',
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
    concept: 'two questions for every Event',
    detail: 'for investors? for engineers?',
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

/* Deterministic PRNG so the universe field is stable across renders. */
function mulberry32(seed: number) {
  let a = seed
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/* The universe is drawn in the same vocabulary as every other plane — a
   tilted phyllotaxis disc — but so large it runs past both sides of the
   frame: a plane too vast to fit. A few blue dots are the useful signal
   buried in the noise, the same blue that re-emerges at Publish and in
   the two briefs. The dashed ring on its surface is the decision to look
   here; the cone hangs from that ring. */
const UNIVERSE_DISC = { y: 78, rx: 480, ry: 60 }
const UNIVERSE_PTS = (() => {
  const rand = mulberry32(20260719)
  const n = 780
  const pts: { x: number; y: number; d: number; dark: boolean; i: number }[] = []
  for (let i = 0; i < n; i += 1) {
    const angle = i * GOLDEN
    const radius = Math.sqrt((i + 0.55) / n) * 0.97
    const d = (Math.sin(angle) * radius + 1) / 2
    pts.push({
      x: CX + Math.cos(angle) * radius * UNIVERSE_DISC.rx,
      y: UNIVERSE_DISC.y + Math.sin(angle) * radius * UNIVERSE_DISC.ry,
      d,
      dark: rand() < 0.05,
      i,
    })
  }
  return pts.sort((a, b) => a.d - b.d)
})()

function UniverseField({ ring }: { ring: Plane }) {
  const { y, rx, ry } = UNIVERSE_DISC
  const backArc = `M ${CX - rx} ${y} A ${rx} ${ry} 0 0 1 ${CX + rx} ${y}`
  const frontArc = `M ${CX - rx} ${y} A ${rx} ${ry} 0 0 0 ${CX + rx} ${y}`
  return (
    <>
      <defs>
        {/* the universe has no edge: fade it out before the frame cuts it */}
        <linearGradient id="universe-fade" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#000" />
          <stop offset="0.09" stopColor="#fff" />
          <stop offset="0.91" stopColor="#fff" />
          <stop offset="1" stopColor="#000" />
        </linearGradient>
        <mask id="universe-mask" maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
          <rect x={0} y={0} width={W} height={H} fill="url(#universe-fade)" />
        </mask>
      </defs>
      <g mask="url(#universe-mask)">
        <ellipse cx={CX} cy={y} rx={rx} ry={ry} fill="rgba(21, 21, 21, 0.02)" />
        <path
          d={backArc}
          fill="none"
          stroke={INK}
          strokeOpacity={0.12}
          strokeWidth={1}
          strokeDasharray="2 5"
        />
        {UNIVERSE_PTS.map((p) => {
          const inside =
            ((p.x - CX) / ring.rx) ** 2 + ((p.y - ring.y) / ring.ry) ** 2 <= 1
          return p.dark ? (
            <circle
              key={p.i}
              cx={p.x}
              cy={p.y}
              r={1.9 * persp(p.d)}
              fill={BLUE}
              stroke={BLUE_INK}
              strokeWidth={0.6}
              opacity={(inside ? 1 : 0.8) * fade(p.d)}
            />
          ) : (
            <circle
              key={p.i}
              cx={p.x}
              cy={p.y}
              r={1.4 * persp(p.d)}
              fill={PALE}
              opacity={(inside ? 0.95 : 0.7) * fade(p.d)}
            />
          )
        })}
        <path
          d={frontArc}
          fill="none"
          stroke={INK}
          strokeOpacity={0.3}
          strokeWidth={1}
        />
      </g>
    </>
  )
}

function PlaneDots({ plane }: { plane: Plane }) {
  const pts = field(plane)

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
  /* Three narrative modes: the overview poses the question, focused stages
     answer it one plane at a time, and 'complete' zooms back out to show
     the whole machine running. */
  const complete = active === 'complete'
  const overview = active == null || active === 'universe'
  const focusIdx = overview || complete ? 0 : STAGE_ORDER.indexOf(active)

  const revealed = (id: FunnelStage) =>
    complete ? true : overview ? id === 'universe' : STAGE_ORDER.indexOf(id) <= focusIdx
  const publishOn = complete || active === 'publish'

  /* Camera: each focused stage gets a precomputed pan/zoom that keeps the
     plane and its right-edge label inside the frame. */
  const FOCUS: Record<FunnelStage, { fx: number; fy: number; s: number }> = {
    universe: { fx: CX, fy: 0, s: 1 },
    watch: { fx: 296, fy: 178, s: 1.14 },
    collect: { fx: 262, fy: 268, s: 1.22 },
    rank: { fx: 250, fy: 350, s: 1.3 },
    judge: { fx: 258, fy: 420, s: 1.32 },
    publish: { fx: 225, fy: 510, s: 1.24 },
    complete: { fx: CX, fy: 0, s: 1 },
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

        {/* planes: back rim behind the dots, solid front rim in front.
            The universe is the exception: a borderless dot field with a
            dashed focus ring instead of a disc. */}
        {PLANES.map((plane) => {
          const on = revealed(plane.id)
          const isActive = !overview && active === plane.id
          const labelX = CX + plane.rx + 14
          if (plane.id === 'universe') {
            return (
              <g
                key={plane.id}
                opacity={on ? 1 : 0.18}
                style={{ transition: 'opacity 600ms ease-out' }}
              >
                {on && <UniverseField ring={plane} />}
                {/* the focus ring: the decision to look here */}
                <ellipse
                  cx={CX}
                  cy={plane.y}
                  rx={plane.rx}
                  ry={plane.ry}
                  fill="none"
                  stroke={INK}
                  strokeOpacity={0.55}
                  strokeWidth={1.1}
                  strokeDasharray="3 4"
                />
                <g
                  fontFamily={MONO}
                  stroke="#ffffff"
                  strokeWidth="3.5"
                  paintOrder="stroke"
                  opacity={complete || overview ? 1 : 0}
                  style={{ transition: 'opacity 500ms ease-out' }}
                >
                  <text
                    x={labelX}
                    y={complete ? plane.y + 3 : plane.y - 4}
                    fontSize="10.5"
                    fontWeight="600"
                    letterSpacing="0.06em"
                    fill={INK}
                  >
                    {plane.name.toUpperCase()}
                  </text>
                  <g opacity={complete ? 0 : 1} style={{ transition: 'opacity 500ms ease-out' }}>
                    <text x={labelX} y={plane.y + 9} fontSize="9" fill={INK_SOFT}>
                      {plane.concept}
                    </text>
                    <text x={labelX} y={plane.y + 21} fontSize="8.5" fill={MUTED}>
                      {plane.detail}
                    </text>
                  </g>
                </g>
              </g>
            )
          }
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
                opacity={complete ? 1 : overview ? (on ? 1 : 0) : isActive ? 1 : 0}
                style={{ transition: 'opacity 500ms ease-out' }}
              >
                <text
                  x={labelX}
                  y={complete ? plane.y + 3 : plane.y - 4}
                  fontSize="10.5"
                  fontWeight="600"
                  letterSpacing="0.06em"
                  fill={isActive ? BLUE_INK : INK}
                >
                  {plane.step ? `${plane.step} · ${plane.name.toUpperCase()}` : plane.name.toUpperCase()}
                </text>
                {/* the finale shows a one-line recap per plane; sub-lines stay
                    with the focused reading */}
                <g opacity={complete ? 0 : 1} style={{ transition: 'opacity 500ms ease-out' }}>
                  <text x={labelX} y={plane.y + 9} fontSize="9" fill={INK_SOFT}>
                    {plane.concept}
                  </text>
                  <text x={labelX} y={plane.y + 21} fontSize="8.5" fill={MUTED}>
                    {plane.detail}
                  </text>
                </g>
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
