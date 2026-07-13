/* The architecture, explained visually: four hand-built diagrams that teach
   the account lifecycle, entity/channel layering, graph plane, and signal funnel.
   Real provenance, real handles, real colors, no generic doc dump. */

const INK = '#151515'
const MUTED = '#6b6b68'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
const SAND = '#f4f1ea'
const MONO = "'IBM Plex Mono', monospace"
const UI = "'Inter', system-ui, sans-serif"

/* ---------- diagram 1: one supplied X account to classified Registry entity ----------
   Survivors flow left→right along one spine; everything filtered drops downward
   with its written reason. Two gates (profile, relevance) drop; kind resolution
   escalates evidence but drops nothing. */

const LC_Y = 64 // top of the stage band
const LC_H = 152 // one shared box height
const LC_MID = LC_Y + LC_H / 2

function LcArrow({ x1, x2 }: { x1: number; x2: number }) {
  return <line x1={x1} y1={LC_MID} x2={x2} y2={LC_MID} stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#account-arr)" />
}

function LcDrop({ x, rows }: { x: number; rows: [string, string][] }) {
  return (
    <g>
      <line x1={x} y1={LC_Y + LC_H} x2={x} y2={LC_Y + LC_H + 40} stroke={MUTED} strokeWidth="1.2" strokeDasharray="3 4" markerEnd="url(#account-drop)" />
      {rows.map(([code, why], i) => (
        <g key={code}>
          <text x={x} y={LC_Y + LC_H + 66 + i * 34} textAnchor="middle" fontFamily={MONO} fontSize="11" fill={INK}>{code}</text>
          <text x={x} y={LC_Y + LC_H + 82 + i * 34} textAnchor="middle" fontFamily={UI} fontSize="12.5" fill={MUTED}>{why}</text>
        </g>
      ))}
    </g>
  )
}

function AccountLifecycle() {
  return (
    <svg
      viewBox="0 0 1080 356"
      role="img"
      aria-label="X account lifecycle: a supplied handle passes a profile gate, entity-kind resolution, and a web-grounded relevance screen before persisting in the Registry; every filtered account exits downward with a written reason"
    >
      <defs>
        <marker id="account-arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
        <marker id="account-drop" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={MUTED} />
        </marker>
      </defs>

      {/* stage kickers, one shared baseline */}
      <text x="24" y="34" fontFamily={MONO} fontSize="12" fill={BLUE_INK} letterSpacing="0.09em">INPUT</text>
      <text x="188" y="34" fontFamily={MONO} fontSize="12" fill={BLUE_INK} letterSpacing="0.09em">PROFILE GATE</text>
      <text x="420" y="34" fontFamily={MONO} fontSize="12" fill={BLUE_INK} letterSpacing="0.09em">ENTITY KIND</text>
      <text x="672" y="34" fontFamily={MONO} fontSize="12" fill={BLUE_INK} letterSpacing="0.09em">RELEVANCE GATE</text>
      <text x="904" y="34" fontFamily={MONO} fontSize="12" fill={BLUE_INK} letterSpacing="0.09em">PERSIST</text>

      {/* input */}
      <rect x="24" y={LC_Y} width="128" height={LC_H} fill={INK} />
      <text x="44" y={LC_Y + 34} fontFamily={MONO} fontSize="11.5" fill={BLUE}>X ACCOUNT</text>
      <text x="44" y={LC_Y + 72} fontFamily={UI} fontSize="21" fontWeight="600" fill="#fff">@handle</text>
      <text x="44" y={LC_Y + 98} fontFamily={UI} fontSize="13" fill="#fff" opacity="0.78">one X handle</text>

      <LcArrow x1={152} x2={186} />

      {/* profile gate */}
      <rect x="188" y={LC_Y} width="196" height={LC_H} fill={SAND} />
      <text x="208" y={LC_Y + 34} fontFamily={UI} fontSize="17" fontWeight="600" fill={INK}>Fetch X profile</text>
      <text x="208" y={LC_Y + 56} fontFamily={UI} fontSize="13" fill={MUTED}>identity · followers · access</text>
      <line x1="208" y1={LC_Y + 74} x2="364" y2={LC_Y + 74} stroke={MUTED} strokeWidth="1" opacity="0.35" />
      <text x="208" y={LC_Y + 102} fontFamily={MONO} fontSize="11.5" fill={BLUE_INK}>PUBLIC + 1K+</text>
      <text x="208" y={LC_Y + 124} fontFamily={UI} fontSize="13.5" fill={INK}>continues right</text>

      <LcArrow x1={384} x2={418} />

      {/* entity kind — escalating evidence, drops nothing */}
      <rect x="420" y={LC_Y} width="216" height={LC_H} fill="#fff" stroke={BLUE_MID} strokeWidth="1.2" />
      <text x="440" y={LC_Y + 34} fontFamily={UI} fontSize="17" fontWeight="600" fill={INK}>Resolve the actor</text>
      <text x="440" y={LC_Y + 66} fontFamily={MONO} fontSize="11.5" fill={BLUE_INK}>1</text>
      <text x="458" y={LC_Y + 66} fontFamily={UI} fontSize="13.5" fill={INK}>profile evidence</text>
      <text x="440" y={LC_Y + 92} fontFamily={MONO} fontSize="11.5" fill={BLUE_INK}>2</text>
      <text x="458" y={LC_Y + 92} fontFamily={UI} fontSize="13.5" fill={INK}>+ 20 authored posts</text>
      <text x="440" y={LC_Y + 118} fontFamily={MONO} fontSize="11.5" fill={BLUE_INK}>3</text>
      <text x="458" y={LC_Y + 118} fontFamily={UI} fontSize="13.5" fill={INK}>+ bounded web research</text>
      <text x="440" y={LC_Y + 140} fontFamily={UI} fontSize="12" fill={MUTED}>each step only if still unsure</text>

      <LcArrow x1={636} x2={670} />

      {/* relevance gate */}
      <rect x="672" y={LC_Y} width="196" height={LC_H} fill={SAND} />
      <text x="692" y={LC_Y + 34} fontFamily={UI} fontSize="17" fontWeight="600" fill={INK}>Relevance screen</text>
      <text x="692" y={LC_Y + 56} fontFamily={UI} fontSize="13" fill={MUTED}>web search required ·</text>
      <text x="692" y={LC_Y + 74} fontFamily={UI} fontSize="13" fill={MUTED}>follower count not an input</text>
      <line x1="692" y1={LC_Y + 88} x2="848" y2={LC_Y + 88} stroke={MUTED} strokeWidth="1" opacity="0.35" />
      <text x="692" y={LC_Y + 114} fontFamily={MONO} fontSize="11.5" fill={BLUE_INK}>FRONTIER-AI SIGNAL</text>
      <text x="692" y={LC_Y + 136} fontFamily={UI} fontSize="13.5" fill={INK}>kept, with cited evidence</text>

      <LcArrow x1={868} x2={902} />

      {/* registry */}
      <rect x="904" y={LC_Y} width="152" height={LC_H} fill={INK} />
      <text x="924" y={LC_Y + 34} fontFamily={MONO} fontSize="11.5" fill={BLUE}>REGISTRY</text>
      <text x="924" y={LC_Y + 66} fontFamily={UI} fontSize="14.5" fontWeight="600" fill="#fff">Person</text>
      <text x="924" y={LC_Y + 92} fontFamily={UI} fontSize="14.5" fontWeight="600" fill="#fff">Organization</text>
      <text x="924" y={LC_Y + 118} fontFamily={UI} fontSize="12.5" fill="#fff" opacity="0.78">unsure parked,</text>
      <text x="924" y={LC_Y + 136} fontFamily={UI} fontSize="12.5" fill="#fff" opacity="0.78">not deleted</text>

      {/* what falls out, and why */}
      <LcDrop
        x={286}
        rows={[
          ['<1,000 FOLLOWERS', 'not added'],
          ['PROTECTED', 'rejected + reason'],
        ]}
      />
      <LcDrop
        x={770}
        rows={[
          ['OFF-MANDATE', 'removed + reason & evidence URLs'],
          ['VERSIONED MANIFEST', 'replayable, never a raw delete'],
        ]}
      />
      <text x="540" y={LC_Y + LC_H + 132} textAnchor="middle" fontFamily={MONO} fontSize="11" fill={MUTED} letterSpacing="0.08em">EVERY EXIT KEEPS ITS REASON</text>
    </svg>
  )
}

/* ---------- diagram 2: the graph plane ---------- */

const NODES = [
  { x: 340, y: 150, r: 26, label: '@karpathy', big: true },
  { x: 520, y: 90, r: 22, label: '@sama', big: true },
  { x: 200, y: 90, r: 20, label: '@ylecun', big: true },
  { x: 460, y: 220, r: 18, label: '@ilyasut', big: true },
  { x: 120, y: 200, r: 10, label: '' },
  { x: 240, y: 250, r: 8, label: '' },
  { x: 620, y: 170, r: 12, label: '' },
  { x: 680, y: 80, r: 8, label: '' },
  { x: 90, y: 60, r: 8, label: '' },
  { x: 390, y: 60, r: 9, label: '' },
  { x: 580, y: 260, r: 8, label: '' },
  { x: 300, y: 300, r: 9, label: '' },
]

const EDGES: [number, number][] = [
  [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [9, 0],
  [0, 1], [7, 1], [9, 1], [6, 1],
  [8, 2], [4, 2], [0, 2],
  [6, 3], [10, 3], [11, 3], [0, 3],
]

function GraphPlane() {
  return (
    <svg viewBox="0 0 760 360" role="img" aria-label="Directed follow graph of AI X channels">
      <defs>
      <marker id="arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
      </marker>
      </defs>
      {EDGES.map(([f, t], i) => {
        const a = NODES[f], b = NODES[t]
        const dx = b.x - a.x, dy = b.y - a.y
        const len = Math.hypot(dx, dy)
        const ux = dx / len, uy = dy / len
        const x1 = a.x + ux * (a.r + 4), y1 = a.y + uy * (a.r + 4)
        const x2 = b.x - ux * (b.r + 8), y2 = b.y - uy * (b.r + 8)
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={BLUE_MID} strokeWidth="1.2" opacity="0.55" markerEnd="url(#arr)" />
      })}
      {NODES.map((n, i) => (
        <g key={i}>
          <circle cx={n.x} cy={n.y} r={n.r} fill={n.big ? BLUE : '#fff'} stroke={n.big ? BLUE_MID : MUTED} strokeWidth={n.big ? 0 : 1.2} />
          {n.label && (
            <text x={n.x} y={n.y + n.r + 18} textAnchor="middle" fontFamily={MONO} fontSize="13" fill={INK}>{n.label}</text>
          )}
        </g>
      ))}
      <text x="28" y="332" fontFamily={UI} fontSize="13" fill={MUTED}>Node size = attention received by X channels. Arrows = observed follows.</text>
    </svg>
  )
}

/* ---------- diagram 3: the data model — who / where / what over time ---------- */

const DM_CHANNELS = [
  { x: 88, label: '@karpathy', plane: 'X · seed rank #1', conf: '0.99', fan: 340 },
  { x: 292, label: 'github.com/karpathy', plane: 'GitHub · nanoGPT, llm.c', conf: '0.95', fan: 380 },
  { x: 496, label: 'A. Karpathy', plane: 'arXiv · 12 papers', conf: '0.85', fan: 420 },
]
const DM_CW = 176
const DM_CH_TOP = 176
const DM_CH_H = 56
const DM_OBS_DOTS = [316, 366, 416, 466, 516, 566, 616]
const DM_RAW_CARDS = [
  { x: 312, tag: 'post' },
  { x: 432, tag: 'paper' },
  { x: 552, tag: 'release' },
]

function DataModel() {
  return (
    <svg
      viewBox="0 0 760 480"
      role="img"
      aria-label="The data model: entities resolve to channels, which carry a dated stream of observations and raw items"
    >
      <defs>
        <marker id="dm-arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>

      {/* role labels down the spine */}
      <text transform="rotate(-90 26 72)" x={26} y={72} textAnchor="middle" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.14em">WHO</text>
      <text transform="rotate(-90 26 204)" x={26} y={204} textAnchor="middle" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.14em">WHERE</text>
      <text transform="rotate(-90 26 378)" x={26} y={378} textAnchor="middle" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.14em">WHAT</text>

      {/* entity → channel links, each carrying a confidence */}
      {DM_CHANNELS.map((c, i) => {
        const cx = c.x + DM_CW / 2
        const x1 = c.fan, y1 = 104, x2 = cx, y2 = DM_CH_TOP
        const mx = x1 + (x2 - x1) * 0.5, my = y1 + (y2 - y1) * 0.5
        return (
          <g key={`link-${i}`}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={BLUE_MID} strokeWidth="1.4" opacity="0.8" />
            <rect x={mx - 27} y={my - 11} width={54} height={22} rx={11} fill="#fff" stroke={BLUE_MID} strokeWidth="1" />
            <text x={mx} y={my + 4} textAnchor="middle" fontFamily={MONO} fontSize="11" fill={BLUE_INK}>{c.conf}</text>
          </g>
        )
      })}

      {/* entity (who) — one card, faint stack behind = the whole registry */}
      <rect x={288} y={48} width={200} height={64} fill={INK} opacity="0.12" />
      <rect x={280} y={40} width={200} height={64} fill={INK} />
      <text x={300} y={72} fontFamily={UI} fontSize="16" fontWeight="600" fill="#fff">Andrej Karpathy</text>
      <text x={300} y={92} fontFamily={MONO} fontSize="11" fill={BLUE}>ENTITY · PERSON</text>
      <text x={500} y={64} fontFamily={UI} fontSize="12.5" fill={MUTED}>labs &amp; people —</text>
      <text x={500} y={82} fontFamily={UI} fontSize="12.5" fill={MUTED}>one entity per real-world who.</text>

      {/* channels (where) */}
      {DM_CHANNELS.map((c, i) => (
        <g key={`chan-${i}`}>
          <rect x={c.x} y={DM_CH_TOP} width={DM_CW} height={DM_CH_H} fill="#fff" stroke={INK} strokeWidth="1" />
          <text x={c.x + 14} y={DM_CH_TOP + 24} fontFamily={MONO} fontSize="12.5" fill={INK}>{c.label}</text>
          <text x={c.x + 14} y={DM_CH_TOP + 43} fontFamily={UI} fontSize="12" fill={MUTED}>{c.plane}</text>
        </g>
      ))}

      {/* confluence — every channel writes into the one dated store */}
      {DM_CHANNELS.map((c, i) => (
        <line
          key={`flow-${i}`}
          x1={c.x + DM_CW / 2}
          y1={DM_CH_TOP + DM_CH_H}
          x2={380}
          y2={286}
          stroke={BLUE_MID}
          strokeWidth="1.2"
          opacity="0.45"
        />
      ))}
      <line x1={380} y1={286} x2={380} y2={300} stroke={BLUE_MID} strokeWidth="1.6" markerEnd="url(#dm-arr)" />

      {/* what we see there — the dated store */}
      <rect x={64} y={300} width={632} height={156} fill={SAND} />
      <text x={84} y={328} fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">WHAT WE SEE THERE — OVER TIME</text>
      <text x={614} y={328} fontFamily={MONO} fontSize="11" fill={MUTED}>time →</text>

      {/* lane 1 — measured observations */}
      <text x={84} y={368} fontFamily={MONO} fontSize="12" fill={INK}>channel_observations</text>
      <text x={84} y={384} fontFamily={UI} fontSize="11" fill={MUTED}>followers · source membership · rank, dated</text>
      <line x1={300} y1={370} x2={648} y2={370} stroke={MUTED} strokeWidth="1" opacity="0.55" markerEnd="url(#dm-arr)" />
      {DM_OBS_DOTS.map((x, i) => (
        <circle key={`obs-${i}`} cx={x} cy={370} r={4} fill={BLUE} />
      ))}

      {/* lane 2 — the raw content itself */}
      <text x={84} y={420} fontFamily={MONO} fontSize="12" fill={INK}>raw_items</text>
      <text x={84} y={436} fontFamily={UI} fontSize="11" fill={MUTED}>the content: posts · papers · releases</text>
      {DM_RAW_CARDS.map((r, i) => (
        <g key={`raw-${i}`}>
          <rect x={r.x} y={410} width={66} height={24} fill="#fff" stroke={BLUE_MID} strokeWidth="1" />
          <text x={r.x + 33} y={426} textAnchor="middle" fontFamily={MONO} fontSize="10" fill={BLUE_INK}>{r.tag}</text>
        </g>
      ))}
    </svg>
  )
}

/* ---------- diagram: the discovery loop, conceptually ----------
   A small circle of people we chose → the crowd they collectively point to →
   the few the pointing singles out → one reviewed door back into the circle.
   No numbers, no table names: just the shape of the idea. */

const SP_Y = 96
const SP_H = 232

// the crowd: scattered small dots inside the middle panel, a few highlighted
const CROWD: [number, number, boolean][] = [
  [452, 150, false], [492, 122, false], [532, 168, true], [572, 132, false],
  [612, 156, false], [652, 124, false], [472, 196, false], [516, 214, false],
  [556, 240, true], [600, 206, false], [644, 232, false], [488, 252, false],
  [536, 268, false], [584, 254, false], [630, 262, true], [664, 240, false],
  [456, 232, false], [668, 186, false],
]

function StoragePlanes() {
  return (
    <svg
      viewBox="0 0 1080 430"
      role="img"
      aria-label="The discovery loop: a small chosen circle of people, the large crowd they collectively follow, ranking that singles out the few worth attention, and one reviewed door that lets those few into the chosen circle"
    >
      <defs>
        <marker id="sp-arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
        <marker id="sp-arr-ink" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={INK} />
        </marker>
      </defs>

      {/* stage kickers */}
      <text x="24" y="34" fontFamily={MONO} fontSize="12" fill={BLUE_INK} letterSpacing="0.09em">THE CIRCLE</text>
      <text x="408" y="34" fontFamily={MONO} fontSize="12" fill={BLUE_INK} letterSpacing="0.09em">THE CROWD THEY POINT TO</text>
      <text x="792" y="34" fontFamily={MONO} fontSize="12" fill={BLUE_INK} letterSpacing="0.09em">THE FEW WHO STAND OUT</text>
      <text x="24" y="56" fontFamily={UI} fontSize="13" fill={MUTED}>people we deliberately chose</text>
      <text x="408" y="56" fontFamily={UI} fontSize="13" fill={MUTED}>everyone they follow — kept at arm’s length</text>
      <text x="792" y="56" fontFamily={UI} fontSize="13" fill={MUTED}>where many chosen people point</text>

      {/* the circle — small, dark, deliberate */}
      <rect x="24" y={SP_Y} width="288" height={SP_H} fill={INK} />
      {[
        [96, SP_Y + 70], [168, SP_Y + 56], [236, SP_Y + 84],
        [120, SP_Y + 134], [200, SP_Y + 126], [162, SP_Y + 174],
      ].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={11} fill={BLUE} />
      ))}
      <text x="168" y={SP_Y + SP_H - 26} textAnchor="middle" fontFamily={UI} fontSize="13" fill="#fff" opacity="0.85">small on purpose —</text>
      <text x="168" y={SP_Y + SP_H - 8} textAnchor="middle" fontFamily={UI} fontSize="13" fill="#fff" opacity="0.85">every member was a decision</text>

      {/* they look outward */}
      <line x1="318" y1={SP_Y + 124} x2="402" y2={SP_Y + 124} stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#sp-arr)" />
      <text x="360" y={SP_Y + 108} textAnchor="middle" fontFamily={MONO} fontSize="10.5" fill={BLUE_INK}>who do they</text>
      <text x="360" y={SP_Y + 148} textAnchor="middle" fontFamily={MONO} fontSize="10.5" fill={BLUE_INK}>follow?</text>

      {/* the crowd — big, sand, undifferentiated */}
      <rect x="408" y={SP_Y} width="288" height={SP_H} fill={SAND} />
      {CROWD.map(([x, y, hot], i) => (
        <circle key={i} cx={x} cy={y} r={hot ? 7 : 4} fill={hot ? BLUE : '#c9c4b6'} />
      ))}
      <text x="552" y={SP_Y + SP_H - 26} textAnchor="middle" fontFamily={UI} fontSize="13" fill={MUTED}>huge and unvetted — observed,</text>
      <text x="552" y={SP_Y + SP_H - 8} textAnchor="middle" fontFamily={UI} fontSize="13" fill={MUTED}>never mixed into the circle</text>

      {/* ranking singles out */}
      <line x1="702" y1={SP_Y + 124} x2="786" y2={SP_Y + 124} stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#sp-arr)" />
      <text x="743" y={SP_Y + 108} textAnchor="middle" fontFamily={MONO} fontSize="10.5" fill={BLUE_INK}>rank</text>

      {/* the few — ordered, explained */}
      <rect x="792" y={SP_Y} width="264" height={SP_H} fill="#fff" stroke={BLUE_MID} strokeWidth="1.2" />
      {[0, 1, 2].map((i) => (
        <g key={i}>
          <circle cx={824} cy={SP_Y + 54 + i * 46} r={i === 0 ? 11 : i === 1 ? 9 : 7} fill={BLUE} />
          <rect x={848} y={SP_Y + 47 + i * 46} width={150 - i * 34} height={13} fill={SAND} />
        </g>
      ))}
      <text x="812" y={SP_Y + 188} fontFamily={UI} fontSize="13" fill={INK}>followed by many of the circle</text>
      <text x="812" y={SP_Y + 208} fontFamily={UI} fontSize="13" fill={MUTED}>— that consensus is the signal,</text>
      <text x="812" y={SP_Y + 226} fontFamily={UI} fontSize="13" fill={MUTED}>not follower counts</text>

      {/* the one door back in */}
      <path
        d={`M 924 ${SP_Y + SP_H} L 924 ${SP_Y + SP_H + 46} L 168 ${SP_Y + SP_H + 46} L 168 ${SP_Y + SP_H + 8}`}
        fill="none"
        stroke={INK}
        strokeWidth="1.5"
        markerEnd="url(#sp-arr-ink)"
      />
      <rect x="426" y={SP_Y + SP_H + 32} width="240" height="28" fill="#fff" />
      <text x="546" y={SP_Y + SP_H + 51} textAnchor="middle" fontFamily={MONO} fontSize="11" fill={INK} letterSpacing="0.06em">REVIEWED → INVITED IN</text>
      <text x="546" y={SP_Y + SP_H + 78} textAnchor="middle" fontFamily={UI} fontSize="12.5" fill={MUTED}>one reviewed door back into the circle — the crowd never gets in on its own</text>
    </svg>
  )
}

/* ---------- diagram 4: the signal funnel (HTML, not SVG — real text) ---------- */

const FUNNEL = [
  {
    pct: 100,
    count: '~120 items',
    name: 'Collect from the watchlist',
    words:
      'We only listen to people and labs already in the registry — their posts, papers, releases, and blog posts. Never the whole internet.',
    tone: 'sand',
  },
  {
    pct: 68,
    count: '~40 events',
    name: 'Merge duplicates into events',
    words:
      'The same announcement arrives from five directions — a tweet, a blog post, a repo, two reposts. Clustering folds them into one event.',
    tone: 'sand',
  },
  {
    pct: 42,
    count: '~12 new',
    name: 'Keep only what is genuinely new',
    words:
      'Seen before, or a rehash of last week? Dropped here — before a single LLM token is spent on it.',
    tone: 'sand',
  },
  {
    pct: 24,
    count: '12 scored',
    name: 'LLM reads and scores the survivors',
    words:
      'The one expensive step, run only on what made it this far. Every insight keeps its quote, source, and score inputs — so an analyst can disagree with it.',
    tone: 'blue',
  },
  {
    pct: 11,
    count: '2–3 delivered',
    name: 'Deliver what clears your bar',
    words:
      'Each persona sets a threshold. An investor and an AI engineering team read different cuts of the same day.',
    tone: 'ink',
  },
] as const

function Funnel() {
  return (
    <div className="funnel">
      {FUNNEL.map((s, i) => (
        <div key={s.name}>
          {i > 0 && (
            <div className="funnel-row" aria-hidden="true">
              <div className="funnel-track">
                <div className="funnel-lane">
                  <div
                    className="funnel-join"
                    style={{
                      clipPath: `polygon(0 0, ${FUNNEL[i - 1].pct}% 0, ${s.pct}% 100%, 0 100%)`,
                    }}
                  />
                </div>
              </div>
              <div />
            </div>
          )}
          <div className="funnel-row">
            <div className="funnel-track">
              <div className="funnel-lane">
                <div className={`funnel-bar tone-${s.tone}`} style={{ width: `${s.pct}%` }} />
              </div>
              <span className="funnel-count">{s.count}</span>
            </div>
            <div className="funnel-copy">
              <h3 className="funnel-name">{s.name}</h3>
              <p>{s.words}</p>
            </div>
          </div>
        </div>
      ))}
      <p className="funnel-footer">
        “Nothing significant today” is a valid — trust-preserving — output.
      </p>
    </div>
  )
}

/* ---------- ranking methods: three measurements, three different questions ---------- */

function RankingMethods() {
  return (
    <div className="methodology" aria-label="Current ranking formulas">
      <div className="method-row">
        <div className="method-id mono">
          <span>REACH</span>
          <strong>Registry</strong>
        </div>
        <div className="method-main">
          <p className="method-question">How large is the observed X audience?</p>
          <div className="method-pair">
            <div>
              <span className="mono">PERSON</span>
              <strong>X followers</strong>
            </div>
            <div>
              <span className="mono">ORGANIZATION</span>
              <strong>Σ followers across owned X channels</strong>
            </div>
          </div>
        </div>
        <p className="method-limit">Display ordering only. Reach ≠ trust.</p>
      </div>

      <div className="method-row">
        <div className="method-id mono">
          <span>ENTITY-OVERLAP-V2</span>
          <strong>Network support</strong>
        </div>
        <div className="method-main">
          <p className="method-question">How many screened Registry entities point here?</p>
          <div className="method-equation mono">
            support(account) = count(distinct active Registry entities → account)
          </div>
          <div className="method-rules mono">
            <span>1 entity = 1 vote</span>
            <span>rejected = 0 votes</span>
            <span>ties share rank</span>
          </div>
        </div>
        <p className="method-limit">Raw follower count is not an input. Support ≠ relevance.</p>
      </div>

      <div className="method-row method-row--attention">
        <div className="method-id mono">
          <span>ATTENTION-V1</span>
          <strong>Feed ordering</strong>
        </div>
        <div className="method-main">
          <p className="method-question">Which evidence is the network paying attention to today?</p>
          <div className="method-equation method-equation--large mono">
            attention = 100 × (0.55N + 0.25O + 0.20E)
          </div>
          <div className="method-weight" aria-label="Feed attention weights">
            <div className="method-weight-network">
              <b>55%</b><span>Registry attention · N</span>
            </div>
            <div className="method-weight-origin">
              <b>25%</b><span>originator support · O</span>
            </div>
            <div className="method-weight-public">
              <b>20%</b><span>public engagement · E</span>
            </div>
          </div>
          <p className="method-example mono">
            Example: N .92 · O .80 · E .35 → 77.6 attention
          </p>
        </div>
        <p className="method-limit">
          Inputs are day-relative percentiles. Attention ≠ quality.
        </p>
      </div>

    </div>
  )
}

/* ---------- page ---------- */

export default function Architecture() {
  return (
    <div className="page">
      <h1 className="page-title">Architecture</h1>
      <p className="page-sub">
        How public evidence becomes resolved identities, trusted rankings, and
        a noise-suppressed intelligence feed.
      </p>

      <nav className="arch-chapters" aria-label="Architecture chapters">
        <a href="#system-map">
          System map
        </a>
        <a href="#ranking-methods">
          Ranking methods
        </a>
      </nav>

      <section className="arch-section" id="system-map">
        <div className="arch-section-head">
          <h2 className="arch-h">From an X account to the Registry</h2>
          <p className="arch-p">
            Cheap checks run first; every filtered exit keeps a written reason.
          </p>
        </div>
        <div className="arch-canvas">
          <AccountLifecycle />
        </div>
      </section>

      <section className="arch-section">
        <div className="arch-section-head">
          <h2 className="arch-h">One data model underneath</h2>
          <p className="arch-p">
            One identity links every channel to its dated observations and
            source material.
          </p>
        </div>
        <div className="arch-canvas">
          <DataModel />
        </div>
      </section>

      <section className="arch-section">
        <div className="arch-section-head">
          <h2 className="arch-h">Discovery keeps its distance</h2>
          <p className="arch-p">
            The Registry observes the wider graph without treating discovery
            as membership.
          </p>
        </div>
        <div className="arch-canvas">
          <StoragePlanes />
        </div>
      </section>

      <section className="arch-section">
        <div className="arch-section-head">
          <h2 className="arch-h">The graph surfaces who deserves attention</h2>
          <p className="arch-p">
            Source consensus and personalized PageRank determine trust;
            follower count remains reach, not trust.
          </p>
        </div>
        <div className="arch-canvas">
          <GraphPlane />
        </div>
      </section>

      <section className="arch-section" style={{ marginBottom: 72 }}>
        <div className="arch-section-head">
          <h2 className="arch-h">The funnel suppresses noise</h2>
          <p className="arch-p">
            Only survivors reach the LLM, and every score keeps its evidence.
          </p>
        </div>
        <div className="arch-canvas">
          <Funnel />
        </div>
      </section>

      <section className="arch-section arch-section--methods" id="ranking-methods">
        <div className="arch-section-head">
          <h2 className="arch-h">The numbers answer different questions</h2>
          <p className="arch-p">
            Reach, network support, and attention are distinct; their formulas
            stay visible so each ranking can be challenged.
          </p>
        </div>
        <div className="arch-canvas arch-canvas--methods">
          <RankingMethods />
        </div>
      </section>
    </div>
  )
}
