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

/* ---------- diagram 1: one supplied X account to classified Registry entity ---------- */

function AccountLifecycle() {
  return (
    <svg
      viewBox="0 0 1120 360"
      role="img"
      aria-label="X account lifecycle: a supplied handle is profiled, checked for eligibility, classified from profile, posts, and bounded web research as needed, then stored in the Registry"
    >
      <defs>
        <marker id="account-arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>

      <text x="40" y="44" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.1em">YOU PROVIDE</text>
      <rect x="40" y="104" width="144" height="116" fill={INK} />
      <text x="60" y="139" fontFamily={MONO} fontSize="10.5" fill={BLUE}>X ACCOUNT</text>
      <text x="60" y="174" fontFamily={UI} fontSize="20" fontWeight="600" fill="#fff">@handle</text>
      <text x="60" y="199" fontFamily={UI} fontSize="12" fill="#fff" opacity="0.72">one account ID</text>

      <line x1="184" y1="162" x2="230" y2="162" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#account-arr)" />

      <text x="248" y="44" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.1em">FETCH + CHECK</text>
      <rect x="248" y="76" width="234" height="172" fill={SAND} />
      <text x="268" y="108" fontFamily={UI} fontSize="17" fontWeight="600" fill={INK}>X profile</text>
      <text x="268" y="134" fontFamily={UI} fontSize="12.5" fill={MUTED}>name · bio · followers · protection</text>
      <line x1="268" y1="151" x2="462" y2="151" stroke={MUTED} strokeWidth="1" opacity="0.35" />
      <text x="268" y="178" fontFamily={MONO} fontSize="10.5" fill={INK}>&lt;1,000</text>
      <text x="352" y="178" fontFamily={UI} fontSize="12.5" fill={MUTED}>not added</text>
      <text x="268" y="207" fontFamily={MONO} fontSize="10.5" fill={INK}>PROTECTED</text>
      <text x="352" y="207" fontFamily={UI} fontSize="12.5" fill={MUTED}>rejected with reason</text>
      <text x="268" y="235" fontFamily={MONO} fontSize="10.5" fill={BLUE_INK}>PUBLIC + 1K+</text>
      <text x="378" y="235" fontFamily={UI} fontSize="12.5" fill={INK}>continue</text>

      <line x1="482" y1="162" x2="538" y2="162" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#account-arr)" />

      <text x="556" y="44" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.1em">CLASSIFY</text>
      <rect x="556" y="60" width="286" height="204" fill="#fff" stroke={BLUE_MID} strokeWidth="1.2" />
      <text x="576" y="92" fontFamily={UI} fontSize="17" fontWeight="600" fill={INK}>Person or organization?</text>

      <circle cx="590" cy="130" r="13" fill={INK} />
      <text x="590" y="134" textAnchor="middle" fontFamily={MONO} fontSize="10" fill="#fff">1</text>
      <text x="616" y="135" fontFamily={UI} fontSize="14" fontWeight="600" fill={INK}>Profile</text>

      <line x1="590" y1="143" x2="590" y2="174" stroke={BLUE_MID} strokeWidth="1" markerEnd="url(#account-arr)" />
      <text x="610" y="167" fontFamily={MONO} fontSize="10" fill={MUTED}>IF UNSURE</text>
      <circle cx="590" cy="190" r="13" fill={BLUE} />
      <text x="590" y="194" textAnchor="middle" fontFamily={MONO} fontSize="10" fill={INK}>2</text>
      <text x="616" y="195" fontFamily={UI} fontSize="14" fontWeight="600" fill={INK}>20 authored posts</text>

      <line x1="590" y1="203" x2="590" y2="234" stroke={BLUE_MID} strokeWidth="1" markerEnd="url(#account-arr)" />
      <text x="610" y="227" fontFamily={MONO} fontSize="10" fill={MUTED}>IF STILL UNSURE</text>
      <circle cx="590" cy="250" r="13" fill="#fff" stroke={BLUE_MID} strokeWidth="1.2" />
      <text x="590" y="254" textAnchor="middle" fontFamily={MONO} fontSize="10" fill={BLUE_INK}>3</text>
      <text x="616" y="255" fontFamily={UI} fontSize="14" fontWeight="600" fill={INK}>Bounded web research</text>

      <line x1="842" y1="162" x2="906" y2="162" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#account-arr)" />

      <text x="924" y="44" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.1em">PERSIST</text>
      <rect x="924" y="92" width="156" height="140" fill={INK} />
      <text x="944" y="123" fontFamily={MONO} fontSize="10.5" fill={BLUE}>REGISTRY</text>
      <text x="944" y="156" fontFamily={UI} fontSize="13.5" fontWeight="600" fill="#fff">Person</text>
      <text x="944" y="184" fontFamily={UI} fontSize="13.5" fontWeight="600" fill="#fff">Organization</text>
      <text x="944" y="212" fontFamily={UI} fontSize="13.5" fontWeight="600" fill="#fff">Unsure</text>

      <line x1="40" y1="312" x2="1080" y2="312" stroke={MUTED} strokeWidth="1" opacity="0.3" />
      <text x="40" y="338" fontFamily={UI} fontSize="12.5" fill={MUTED}>One account in, one persisted outcome out. The reason, evidence, and cost stay attached.</text>
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

/* ---------- page ---------- */

export default function Architecture() {
  return (
    <div className="page">
      <div className="page-kicker">HOW IT WORKS</div>
      <h1 className="page-title">Architecture</h1>
      <p className="page-sub">
        Four views: how entities enter, where evidence lives, how attention
        ranks, and how the system keeps only signal.
      </p>

      <section className="arch-section">
        <div className="arch-section-head">
          <span className="arch-no">01</span>
          <h2 className="arch-h">From an X account to the Registry</h2>
          <p className="arch-p">
            Give the system one X handle. It fetches the profile, applies the
            eligibility rules, resolves the actor in bounded stages, and makes
            the result visible immediately.
          </p>
        </div>
        <div className="arch-canvas">
          <AccountLifecycle />
          <div className="arch-caption">profile first · 20 authored posts only if unsure · bounded web research only if still unsure · result appears in the Registry</div>
        </div>
      </section>

      <section className="arch-section">
        <div className="arch-section-head">
          <span className="arch-no">02</span>
          <h2 className="arch-h">One data model underneath</h2>
          <p className="arch-p">
            One spine holds everything: a <em>who</em>, the <em>wheres</em> we
            watch them, and <em>what</em> we saw — over time.
          </p>
        </div>
        <div className="arch-canvas">
          <DataModel />
          <div className="arch-caption">entities ↔ entity_channels (evidence + confidence) ↔ channels → channel_observations + raw_items · graph evidence comes only from explicit trusted-follow snapshots</div>
        </div>
      </section>

      <section className="arch-section">
        <div className="arch-section-head">
          <span className="arch-no">03</span>
          <h2 className="arch-h">The graph decides who matters</h2>
          <p className="arch-p">
            Attention, not follower count: being followed by several trusted
            channels can matter more than a large generic audience. The active
            graph starts small and grows only through explicit snapshots.
          </p>
        </div>
        <div className="arch-canvas">
          <GraphPlane />
          <div className="arch-caption">current graph: empty · next: isolated trusted-seed snapshots · Digg ranking retained offline for comparison only</div>
        </div>
      </section>

      <section className="arch-section" style={{ marginBottom: 72 }}>
        <div className="arch-section-head">
          <span className="arch-no">04</span>
          <h2 className="arch-h">The funnel suppresses noise</h2>
          <p className="arch-p">
            Cheap mechanical checks first, the expensive LLM last — only on what
            survives. Every score keeps its evidence, so you can disagree.
          </p>
        </div>
        <div className="arch-canvas">
          <Funnel />
          <div className="arch-caption">volumes are an illustrative day — ingestion is not live yet · every surviving insight keeps its citation</div>
        </div>
      </section>
    </div>
  )
}
