/* SignalFunnel — the How-it-works hero figure. One cone of progressive
   signal-to-noise refinement: each ellipse is a cross-section plane of the
   funnel, dots are the units that survive to that stage, and the tip forks
   into the two audience briefs. Visual vocabulary matches /network/ranking:
   phyllotaxis dot fields, circle = person/post, square = organization,
   dashed hairlines, mono labels with white halos. Counts are the July 5–15
   frozen checkpoint, matching the prose on the page. */

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

type Plane = {
  id: FunnelStage
  y: number
  rx: number
  ry: number
  dots: number
  step: string
  name: string
  count: string
  detail: string
}

/* Vertical rhythm: planes shrink as noise is removed. */
const PLANES: Plane[] = [
  {
    id: 'universe',
    y: 78,
    rx: 172,
    ry: 46,
    dots: 190,
    step: '',
    name: 'The public record',
    count: 'millions of posts a day',
    detail: 'everyone, about everything',
  },
  {
    id: 'watch',
    y: 190,
    rx: 132,
    ry: 35,
    dots: 105,
    step: '1',
    name: 'Choose',
    count: '2,630 screened identities',
    detail: 'labs, people, one follow graph',
  },
  {
    id: 'collect',
    y: 288,
    rx: 100,
    ry: 26.5,
    dots: 62,
    step: '2',
    name: 'Collect',
    count: '51,323 posts → 9,646 Events',
    detail: 'complete days, exact relations',
  },
  {
    id: 'rank',
    y: 372,
    rx: 72,
    ry: 19,
    dots: 34,
    step: '3',
    name: 'Rank',
    count: 'one transparent score',
    detail: 'where to look first',
  },
  {
    id: 'judge',
    y: 443,
    rx: 48,
    ry: 12.5,
    dots: 16,
    step: '4',
    name: 'Judge',
    count: '404 surfaced of 947 judgments',
    detail: 'two audiences, two questions',
  },
  {
    id: 'publish',
    y: 500,
    rx: 26,
    ry: 7,
    dots: 5,
    step: '5',
    name: 'Publish',
    count: '≈5 cited Insights a day',
    detail: 'per audience, every source checked',
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
    /* Filled = routed relevant to an audience, hollow = explicitly not. */
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

function Brief({
  x,
  label,
  active,
}: {
  x: number
  label: string
  active: boolean
}) {
  const w = 118
  const h = 44
  return (
    <g opacity={active ? 1 : 0.34} style={{ transition: 'opacity 240ms ease-out' }}>
      <rect
        x={x - w / 2}
        y={FORK_Y}
        width={w}
        height={h}
        fill="#ffffff"
        stroke={active ? BLUE_MID : INK}
        strokeWidth={active ? 1.4 : 1}
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
        fill={active ? BLUE_INK : INK_SOFT}
      >
        {label}
      </text>
    </g>
  )
}

export default function SignalFunnel({ active }: { active: FunnelStage | null }) {
  const isOn = (id: FunnelStage) =>
    active == null || active === id || (active === 'publish' && id === 'publish')

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="The signal funnel: from everything published publicly, a screened cohort chooses what to collect, exact Events are ranked, judged for two audiences, and distilled into two daily cited briefs."
      className="signal-funnel"
    >
      {/* cone silhouette: dashed hairlines connecting the plane edges */}
      {PLANES.slice(0, -1).map((p, i) => {
        const q = PLANES[i + 1]
        return (
          <g key={p.id} stroke={INK} strokeOpacity="0.22" strokeDasharray="2 5" strokeWidth="1">
            <line x1={CX - p.rx} y1={p.y} x2={CX - q.rx} y2={q.y} />
            <line x1={CX + p.rx} y1={p.y} x2={CX + q.rx} y2={q.y} />
          </g>
        )
      })}
      {/* tip of the cone */}
      {(() => {
        const last = PLANES[PLANES.length - 1]
        return (
          <g stroke={INK} strokeOpacity="0.22" strokeDasharray="2 5" strokeWidth="1">
            <line x1={CX - last.rx} y1={last.y} x2={CX} y2={TIP_Y} />
            <line x1={CX + last.rx} y1={last.y} x2={CX} y2={TIP_Y} />
          </g>
        )
      })()}

      {/* fork from the tip into the two audience briefs */}
      <g stroke={BLUE_MID} strokeWidth="1.1" fill="none">
        <path d={`M ${CX} ${TIP_Y} Q ${CX} ${FORK_Y - 10} ${CX - 74} ${FORK_Y - 2}`} opacity={isOn('publish') ? 0.9 : 0.3} style={{ transition: 'opacity 240ms ease-out' }} />
        <path d={`M ${CX} ${TIP_Y} Q ${CX} ${FORK_Y - 10} ${CX + 74} ${FORK_Y - 2}`} opacity={isOn('publish') ? 0.9 : 0.3} style={{ transition: 'opacity 240ms ease-out' }} />
      </g>
      <Brief x={CX - 74} label="INVESTMENT" active={isOn('publish')} />
      <Brief x={CX + 74} label="AI ENGINEERING" active={isOn('publish')} />

      {/* planes: back rim behind the dots, solid front rim in front — the
          split rim plus depth-scaled dots is what makes each disc read 3D */}
      {PLANES.map((plane) => {
        const on = isOn(plane.id)
        const isActive = active === plane.id
        const labelX = CX + plane.rx + 14
        const backArc = `M ${CX - plane.rx} ${plane.y} A ${plane.rx} ${plane.ry} 0 0 1 ${CX + plane.rx} ${plane.y}`
        const frontArc = `M ${CX - plane.rx} ${plane.y} A ${plane.rx} ${plane.ry} 0 0 0 ${CX + plane.rx} ${plane.y}`
        return (
          <g
            key={plane.id}
            opacity={on ? 1 : 0.35}
            style={{ transition: 'opacity 240ms ease-out' }}
          >
            {/* disc surface wash */}
            <ellipse
              cx={CX}
              cy={plane.y}
              rx={plane.rx}
              ry={plane.ry}
              fill={isActive ? 'rgba(91, 197, 242, 0.10)' : 'rgba(21, 21, 21, 0.025)'}
              style={{ transition: 'fill 240ms ease-out' }}
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
            <PlaneDots plane={plane} />
            {/* front rim: solid, closer to the viewer, drawn over the dots */}
            <path
              d={frontArc}
              fill="none"
              stroke={isActive ? BLUE_MID : INK}
              strokeOpacity={isActive ? 0.95 : 0.42}
              strokeWidth={isActive ? 1.4 : 1}
              style={{ transition: 'stroke 240ms ease-out' }}
            />
            {/* stage label, anchored to the plane's right edge */}
            <g
              fontFamily={MONO}
              stroke="#ffffff"
              strokeWidth="3.5"
              paintOrder="stroke"
            >
              <text
                x={labelX}
                y={plane.y - 4}
                fontSize="10.5"
                fontWeight="600"
                letterSpacing="0.06em"
                fill={active === plane.id ? BLUE_INK : INK}
              >
                {plane.step ? `${plane.step} · ${plane.name.toUpperCase()}` : plane.name.toUpperCase()}
              </text>
              <text x={labelX} y={plane.y + 9} fontSize="9" fill={INK_SOFT}>
                {plane.count}
              </text>
              <text x={labelX} y={plane.y + 21} fontSize="8.5" fill={MUTED}>
                {plane.detail}
              </text>
            </g>
          </g>
        )
      })}

      {/* checkpoint caption */}
      <text
        x={CX}
        y={H - 6}
        textAnchor="middle"
        fontFamily={MONO}
        fontSize="8"
        letterSpacing="0.05em"
        fill={MUTED}
      >
        counts: frozen July 5–15 evidence window
      </text>
    </svg>
  )
}
