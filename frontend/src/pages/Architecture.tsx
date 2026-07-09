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

/* ---------- diagram 2: the data model — who / where / what over time ---------- */

const DM_CHANNELS = [
  { x: 88, label: '@karpathy', plane: 'X · Digg rank #1', conf: '0.99', fan: 340 },
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

      {/* channels (where) — and the stream each writes into the store */}
      {DM_CHANNELS.map((c, i) => (
        <g key={`chan-${i}`}>
          <rect x={c.x} y={DM_CH_TOP} width={DM_CW} height={DM_CH_H} fill="#fff" stroke={INK} strokeWidth="1" />
          <text x={c.x + 14} y={DM_CH_TOP + 24} fontFamily={MONO} fontSize="12.5" fill={INK}>{c.label}</text>
          <text x={c.x + 14} y={DM_CH_TOP + 43} fontFamily={UI} fontSize="12" fill={MUTED}>{c.plane}</text>
          <line
            x1={c.x + DM_CW / 2}
            y1={DM_CH_TOP + DM_CH_H}
            x2={380 + (i - 1) * 8}
            y2={298}
            stroke={BLUE_MID}
            strokeWidth="1.2"
            opacity="0.5"
            markerEnd="url(#dm-arr)"
          />
        </g>
      ))}

      {/* what we see there — the dated store */}
      <rect x={64} y={300} width={632} height={156} fill={SAND} />
      <text x={84} y={328} fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">WHAT WE SEE THERE — OVER TIME</text>
      <text x={614} y={328} fontFamily={MONO} fontSize="11" fill={MUTED}>time →</text>

      {/* lane 1 — measured observations */}
      <text x={84} y={368} fontFamily={MONO} fontSize="12" fill={INK}>channel_observations</text>
      <text x={84} y={384} fontFamily={UI} fontSize="11" fill={MUTED}>rank · followers · pagerank, dated</text>
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
        Three ideas carry the whole system: one data model lays out who we
        track, where we watch them, and what we saw; a social graph decides who
        is worth watching in the first place; and a funnel makes sure only
        signal reaches a human.
      </p>

      <section className="arch-section">
        <div className="arch-section-head">
          <span className="arch-no">01</span>
          <h2 className="arch-h">One data model underneath</h2>
          <p className="arch-p">
            Start here — everything else reads through this. Everything the
            system stores fits a single spine. An entity is a
            <em> who</em> — a lab or a person. It is watched through
            <em> channels</em> — its X account, GitHub org, arXiv author, blog —
            and evidence-and-confidence links resolve many channels to one
            entity. Each channel then carries a dated stream of
            <em> what</em> we saw there: measured observations and the raw
            content itself. Read it top to bottom: who, where, and what — over
            time.
          </p>
        </div>
        <div className="arch-canvas">
          <DataModel />
          <div className="arch-caption">entities ↔ entity_channels (evidence + confidence) ↔ channels → channel_observations + raw_items · the legacy Digg/X follow-graph is one bootstrap source feeding channels + observations</div>
        </div>
      </section>

      <section className="arch-section">
        <div className="arch-section-head">
          <span className="arch-no">02</span>
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
