/* The architecture, explained visually: three hand-built diagrams that
   teach the system — the graph plane, the entity/channel layering, and
   the signal funnel. Real handles, real colors, no generic doc dump. */

const INK = '#151515'
const MUTED = '#6b6b68'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
const SAND = '#f4f1ea'
const MONO = "'IBM Plex Mono', monospace"
const UI = "'Inter', system-ui, sans-serif"

/* ---------- diagram 1: the graph plane ---------- */

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
      <text x="28" y="332" fontFamily={UI} fontSize="13" fill={MUTED}>Node size = attention received by X channels. Arrows = observed “top follower of”.</text>
    </svg>
  )
}

/* ---------- diagram 2: channels → entity ---------- */

function EntityLayers() {
  const acc = [
    { x: 80, label: '@karpathy', plane: 'X · Digg rank #1' },
    { x: 320, label: 'github.com/karpathy', plane: 'GitHub · nanoGPT, llm.c' },
    { x: 560, label: 'A. Karpathy', plane: 'arXiv · 12 papers' },
  ]
  return (
    <svg viewBox="0 0 760 400" role="img" aria-label="Channels resolve to one real-world entity">
      {/* plane band */}
      <rect x="24" y="252" width="712" height="120" fill={SAND} />
      <text x="40" y="278" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">CHANNELS — WHERE WE OBSERVE</text>
      {acc.map((a, i) => (
        <g key={i}>
          <rect x={a.x} y={294} width={192} height={56} fill="#fff" stroke={INK} strokeWidth="1" />
          <text x={a.x + 14} y={317} fontFamily={MONO} fontSize="13" fill={INK}>{a.label}</text>
          <text x={a.x + 14} y={337} fontFamily={UI} fontSize="12" fill={MUTED}>{a.plane}</text>
        </g>
      ))}
      {/* entity card */}
      <rect x="270" y="40" width="220" height="72" fill={INK} />
      <text x="292" y="72" fontFamily={UI} fontSize="16" fontWeight="600" fill="#fff">Andrej Karpathy</text>
      <text x="292" y="94" fontFamily={MONO} fontSize="11" fill={BLUE}>ENTITY · PERSON</text>
      {/* entity-channel links */}
      {acc.map((a, i) => {
        const x1 = a.x + 96, y1 = 294
        const x2 = 292 + i * 80, y2 = 112
        const conf = ['0.99', '0.95', '0.85'][i]
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2
        return (
          <g key={i}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={BLUE_MID} strokeWidth="1.4" />
            <rect x={mx - 30} y={my - 12} width={60} height={22} fill="#fff" stroke={BLUE_MID} strokeWidth="1" rx="11" />
            <text x={mx} y={my + 3} textAnchor="middle" fontFamily={MONO} fontSize="11" fill={BLUE_INK}>{conf}</text>
          </g>
        )
      })}
      <text x="512" y="66" fontFamily={UI} fontSize="12.5" fill={MUTED}>One real-world person.</text>
      <text x="512" y="84" fontFamily={UI} fontSize="12.5" fill={MUTED}>Created only after review.</text>
      <text x="40" y="56" fontFamily={UI} fontSize="12.5" fill={MUTED}>Entity-channel links carry evidence +</text>
      <text x="40" y="74" fontFamily={UI} fontSize="12.5" fill={MUTED}>confidence. Wrong match = one</text>
      <text x="40" y="92" fontFamily={UI} fontSize="12.5" fill={MUTED}>deletable link, not poisoned data.</text>
    </svg>
  )
}

/* ---------- diagram 3: the signal funnel (HTML, not SVG — real text) ---------- */

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
        Three ideas carry the whole system: a social graph decides who is worth
        watching, an entity/channel layer connects every observation plane,
        and a funnel makes sure only signal reaches a human.
      </p>

      <section className="arch-section">
        <div className="arch-section-head">
          <span className="arch-no">01</span>
          <h2 className="arch-h">The graph decides who matters</h2>
          <p className="arch-p">
            2,315 X channels and 361,225 observed follow relationships, pulled
            from Digg's ranking of the AI community. Attention flows through
            edges: being followed by ten important channels beats a thousand
            random followers. That is PageRank — and it turns a raw social
            graph into a ranked list of people worth reviewing.
          </p>
        </div>
        <div className="arch-canvas">
          <GraphPlane />
          <div className="arch-caption">graph_edges · source: digg · relationship: top_follower_of · every edge carries its evidence URL</div>
        </div>
      </section>

      <section className="arch-section">
        <div className="arch-section-head">
          <span className="arch-no">02</span>
          <h2 className="arch-h">Entities connect the planes</h2>
          <p className="arch-p">
            The same person exists on X, GitHub, and arXiv under different
            names. Each source stays a separate channel — what the data
            literally shows. A reviewed entity sits above them, linked by
            entity-channel records that carry evidence and confidence. Every
            future signal (a post, a release, a paper) lands on a channel and is read
            through its entity.
          </p>
        </div>
        <div className="arch-canvas">
          <EntityLayers />
          <div className="arch-caption">channels → entity_channels (evidence + confidence) → entities · promotion requires curation</div>
        </div>
      </section>

      <section className="arch-section" style={{ marginBottom: 72 }}>
        <div className="arch-section-head">
          <span className="arch-no">03</span>
          <h2 className="arch-h">The funnel suppresses noise</h2>
          <p className="arch-p">
            Each stage lets less through. The cheap, mechanical checks run
            first; the expensive LLM judgment runs last, only on what
            survives. Every score shows its inputs — including evidence
            against our own thesis — so an analyst can always disagree with
            the machine.
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
