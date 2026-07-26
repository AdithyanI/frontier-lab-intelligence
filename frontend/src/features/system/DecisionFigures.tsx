/* Decision figures for the How-it-works write-up. Each one justifies a
   design choice at one funnel stage, in the same visual language as the
   architecture diagrams: mono kickers, hairlines, blue accents. */

const INK = '#151515'
const MUTED = '#6b6b68'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
const SAND = '#f4f1ea'
const MONO = "'IBM Plex Mono', monospace"
const UI = "'Inter', system-ui, sans-serif"

/* Stage 1a: where to look. The other public source classes surface on X
   anyway, and the authors themselves are in the room, so X is the first
   source to go deep on. */
export function SourceChoiceFigure() {
  const sources = [
    { x: 30, title: 'Papers' },
    { x: 235, title: 'Blogs' },
    { x: 440, title: 'GitHub' },
    { x: 645, title: 'Talks' },
    { x: 850, title: 'Model cards' },
  ]
  const targets = [458, 494, 530, 566, 602]
  return (
    <svg
      viewBox="0 0 1080 396"
      role="img"
      aria-label="Six public source classes: papers, blogs, GitHub, talks, model cards, and X. X is chosen first because the other classes get announced and argued there anyway, and the authors write there themselves. The rest plug in later as channels."
    >
      <defs>
        <marker id="source-arrow-muted" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={MUTED} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">WHERE TO LOOK · SIX PUBLIC SOURCE CLASSES</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">WHY X FIRST</text>

      {sources.map((s, i) => (
        <g key={s.title}>
          <rect x={s.x} y={62} width="180" height="54" fill="#fff" stroke={MUTED} strokeWidth="1" opacity="0.9" />
          <text x={s.x + 90} y={94} textAnchor="middle" fontFamily={UI} fontSize="14.5" fontWeight="600" fill={INK} opacity="0.72">
            {s.title}
          </text>
          <line
            x1={s.x + 90}
            y1={120}
            x2={targets[i]}
            y2={198}
            stroke={MUTED}
            strokeWidth="1"
            strokeDasharray="3 5"
            opacity="0.55"
            markerEnd="url(#source-arrow-muted)"
          />
        </g>
      ))}

      <text x="540" y="172" textAnchor="middle" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">
        USUALLY ANNOUNCED HERE, WITH THE SOURCE LINK
      </text>

      <rect x="420" y="204" width="240" height="118" fill={INK} />
      <text x="444" y="238" fontFamily={MONO} fontSize="9.5" fill={BLUE} letterSpacing="0.08em">CHOSEN FIRST</text>
      <text x="444" y="272" fontFamily={UI} fontSize="21" fontWeight="600" fill="#fff">X</text>
      <text x="444" y="300" fontFamily={UI} fontSize="12.5" fill="#fff" opacity="0.78">the front page of AI</text>

      <text x="684" y="290" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">
        RESEARCHERS, FOUNDERS, AND LABS SPEAK HERE DIRECTLY
      </text>

      <line x1="30" y1="352" x2="1050" y2="352" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="378" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        X is the starting point. The linked paper, blog, repository, talk, or model card is collected as primary evidence.
      </text>
    </svg>
  )
}

/* Stage 1b: collect the trusted set. Out of everything observable on X,
   screening keeps a small cohort worth listening to: the blue dots. */
export function TrustedSetFigure() {
  const grey: { x: number; y: number }[] = []
  const frac = (v: number) => v - Math.floor(v)
  for (let i = 0; i < 250; i += 1) {
    const x = 36 + frac(Math.sin(i * 12.9898) * 43758.5453) * 1008
    const y = 70 + frac(Math.sin(i * 78.233) * 12543.8567) * 226
    const dx = (x - 760) / 208
    const dy = (y - 186) / 112
    if (dx * dx + dy * dy > 1) grey.push({ x, y })
  }
  const blue: { x: number; y: number }[] = []
  for (let i = 0; i < 26; i += 1) {
    const angle = i * 2.399963
    const radius = Math.sqrt((i + 0.5) / 26)
    blue.push({
      x: 760 + Math.cos(angle) * radius * 158,
      y: 186 + Math.sin(angle) * radius * 80,
    })
  }
  return (
    <svg
      viewBox="0 0 1080 360"
      role="img"
      aria-label="A wide field of grey dots stands for public X accounts. A dashed boundary holds a smaller set of blue dots: the screened people and labs kept in the Registry."
    >
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">WHOM TO COLLECT · SCREENING X INTO A TRUSTED SET</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">FOLLOW GRAPH SNAPSHOT</text>

      {grey.map((dot, index) => (
        <circle key={`g-${index}`} cx={dot.x} cy={dot.y} r="3" fill={MUTED} opacity="0.3" />
      ))}

      <ellipse cx="760" cy="186" rx="196" ry="100" fill="none" stroke={BLUE_MID} strokeWidth="1.2" strokeDasharray="5 5" />
      {blue.map((dot, index) => (
        <circle key={`b-${index}`} cx={dot.x} cy={dot.y} r="4.5" fill={BLUE} />
      ))}

      <text x="60" y="322" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">PUBLIC X ACCOUNTS</text>
      <text x="760" y="322" textAnchor="middle" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">THE REGISTRY · SCREENED PEOPLE AND LABS</text>

      <line x1="30" y1="336" x2="1050" y2="336" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="356" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        Only what the blue set posts gets collected. Every admission or rejection keeps its reason.
      </text>
    </svg>
  )
}

/* Stage 2: preserve before interpreting. Declared reply and quote
   relationships group posts into one exact Event; linked documents are
   frozen alongside. No opinions yet. */
export function CollectFigure() {
  const posts = [
    { y: 70, title: 'Post' },
    { y: 140, title: 'Reply' },
    { y: 210, title: 'Quote' },
  ]
  return (
    <svg
      viewBox="0 0 1080 340"
      role="img"
      aria-label="A post, its reply, and a quote are grouped into one exact Event using only relationships the platform declares. A linked paper or repository is frozen as text and attached to the same Event."
    >
      <defs>
        <marker id="collect-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">COLLECT · PRESERVE BEFORE INTERPRETING</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">ONE OBSERVED DAY AT A TIME</text>

      {posts.map((post) => (
        <g key={post.title}>
          <rect x="70" y={post.y} width="150" height="48" fill="#fff" stroke={MUTED} strokeWidth="1" />
          <text x="94" y={post.y + 30} fontFamily={UI} fontSize="14" fontWeight="600" fill={INK} opacity="0.8">{post.title}</text>
          <line x1="220" y1={post.y + 24} x2="330" y2="164" stroke={MUTED} strokeWidth="1" opacity="0.6" />
        </g>
      ))}
      <text x="118" y="292" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">AS POSTED, UNCHANGED</text>

      <line x1="330" y1="164" x2="416" y2="164" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#collect-arrow)" />
      <text x="290" y="106" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">GROUPED BY DECLARED LINKS</text>

      <rect x="424" y="122" width="230" height="84" fill={INK} />
      <text x="448" y="158" fontFamily={UI} fontSize="16" fontWeight="600" fill="#fff">One exact Event</text>
      <text x="448" y="184" fontFamily={UI} fontSize="12" fill="#fff" opacity="0.78">nothing merged by topic</text>

      <line x1="774" y1="164" x2="662" y2="164" stroke={BLUE_MID} strokeWidth="1.2" strokeDasharray="4 4" markerEnd="url(#collect-arrow)" />
      <rect x="774" y="128" width="240" height="72" fill="#fff" stroke={MUTED} strokeWidth="1.2" strokeDasharray="5 5" />
      <text x="796" y="160" fontFamily={UI} fontSize="14" fontWeight="600" fill={INK}>Linked paper or repo</text>
      <text x="796" y="182" fontFamily={UI} fontSize="12" fill={MUTED}>text frozen for citation checks</text>

      <line x1="30" y1="312" x2="1050" y2="312" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="334" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        Grouping uses only relationships the platform itself declares. No topics, no opinions at this stage.
      </text>
    </svg>
  )
}

/* Stage 3: order the day, do not judge it. The same bars, sorted; the top
   of the ordered day goes to judging. */
export function RankFigure() {
  const heights = [46, 90, 30, 64, 110, 52, 78, 38, 96, 60]
  const sorted = [...heights].sort((a, b) => b - a)
  const baseline = 250
  return (
    <svg
      viewBox="0 0 1080 350"
      role="img"
      aria-label="Left: a day of Events as unordered bars. Right: the same bars ordered by attention, with the top of the day marked as what goes to judging first."
    >
      <defs>
        <marker id="rank-order-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">RANK · ORDER THE DAY, DO NOT JUDGE IT</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">A TRANSPARENT FORMULA</text>

      {heights.map((height, index) => (
        <rect key={`u-${index}`} x={70 + index * 34} y={baseline - height} width="22" height={height} fill={MUTED} opacity="0.35" />
      ))}
      <line x1="70" y1={baseline} x2={70 + 9 * 34 + 22} y2={baseline} stroke={MUTED} strokeWidth="1" />
      <text x="70" y="288" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">A DAY OF EVENTS, AS THEY ARRIVED</text>

      <line x1="460" y1="196" x2="586" y2="196" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#rank-order-arrow)" />
      <text x="472" y="180" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">SCORED</text>

      {sorted.map((height, index) => (
        <rect
          key={`s-${index}`}
          x={620 + index * 34}
          y={baseline - height}
          width="22"
          height={height}
          fill={index < 3 ? BLUE : MUTED}
          opacity={index < 3 ? 1 : 0.35}
        />
      ))}
      <line x1="620" y1={baseline} x2={620 + 9 * 34 + 22} y2={baseline} stroke={MUTED} strokeWidth="1" />
      <rect x="612" y="130" width="112" height="130" fill="none" stroke={BLUE_MID} strokeWidth="1" strokeDasharray="4 4" />
      <text x="612" y="122" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">JUDGED FIRST</text>
      <text x="620" y="288" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">THE SAME DAY, ORDERED BY ATTENTION</text>

      <line x1="30" y1="312" x2="1050" y2="312" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="334" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        The score decides where to look first. It never decides what is true or what matters.
      </text>
    </svg>
  )
}

/* Stage 4: two independent questions. One Event, two separate verdicts,
   never a blended score. */
export function JudgeFigure() {
  return (
    <svg
      viewBox="0 0 1080 340"
      role="img"
      aria-label="One Event is asked two separate questions: does this change an investment position, and should an engineering team act on it. Each gets its own yes or no with reasons. Both, one, or neither can apply."
    >
      <defs>
        <marker id="judge-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">JUDGE · TWO INDEPENDENT QUESTIONS</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">FRESH FIRST-PARTY EVIDENCE ONLY</text>

      <rect x="70" y="140" width="190" height="84" fill={INK} />
      <text x="94" y="176" fontFamily={UI} fontSize="16" fontWeight="600" fill="#fff">One Event</text>
      <text x="94" y="200" fontFamily={UI} fontSize="12" fill="#fff" opacity="0.78">with its evidence</text>

      <line x1="260" y1="168" x2="392" y2="112" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#judge-arrow)" />
      <line x1="260" y1="196" x2="392" y2="252" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#judge-arrow)" />

      <rect x="400" y="76" width="360" height="70" fill="#fff" stroke={BLUE_MID} strokeWidth="1.2" />
      <text x="422" y="106" fontFamily={UI} fontSize="14.5" fontWeight="600" fill={INK}>Does this change an investment position?</text>
      <text x="422" y="130" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">YES OR NO · REASONS ATTACHED</text>

      <rect x="400" y="216" width="360" height="70" fill="#fff" stroke={BLUE_MID} strokeWidth="1.2" />
      <text x="422" y="246" fontFamily={UI} fontSize="14.5" fontWeight="600" fill={INK}>Should an engineering team act on it?</text>
      <text x="422" y="270" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">YES OR NO · REASONS ATTACHED</text>

      <line x1="828" y1="111" x2="828" y2="251" stroke={MUTED} strokeWidth="1" strokeDasharray="4 4" opacity="0.6" />
      <text x="852" y="168" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">THE TWO ANSWERS</text>
      <text x="852" y="186" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">NEVER SHARE A SCORE</text>

      <line x1="30" y1="312" x2="1050" y2="312" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="334" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        An Event can matter to both audiences, to one, or to neither. Each verdict keeps its reasoning.
      </text>
    </svg>
  )
}

/* Stage 5: surface it, or say why not. Every candidate gets one of two
   dispositions; nothing is dropped silently. */
export function PublishFigure() {
  const candidates = [
    { x: 70, y: 118 }, { x: 106, y: 118 }, { x: 142, y: 118 },
    { x: 70, y: 154 }, { x: 106, y: 154 }, { x: 142, y: 154 },
    { x: 70, y: 190 }, { x: 106, y: 190 }, { x: 142, y: 190 },
  ]
  return (
    <svg
      viewBox="0 0 1080 340"
      role="img"
      aria-label="Candidates that survived judging pass through the FLI daily agent. Each one becomes either a cited Insight or a written decline. Nothing is dropped silently."
    >
      <defs>
        <marker id="publish-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">PUBLISH · SURFACE IT, OR SAY WHY NOT</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">NOTHING DROPPED SILENTLY</text>

      {candidates.map((c, i) => (
        <rect key={`c-${i}`} x={c.x} y={c.y} width="20" height="20" fill="#fff" stroke={MUTED} strokeWidth="1" />
      ))}
      <text x="70" y="244" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">EVERY CANDIDATE THAT SURVIVED</text>

      <line x1="188" y1="164" x2="296" y2="164" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#publish-arrow)" />

      <rect x="304" y="122" width="250" height="84" fill={SAND} stroke={BLUE_MID} strokeWidth="1.2" />
      <text x="328" y="158" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>FLI daily agent</text>
      <text x="328" y="182" fontFamily={UI} fontSize="12" fill={MUTED}>must decide, one way or the other</text>

      <line x1="554" y1="148" x2="672" y2="106" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#publish-arrow)" />
      <line x1="554" y1="182" x2="672" y2="246" stroke={MUTED} strokeWidth="1.2" strokeDasharray="4 4" opacity="0.7" />

      <rect x="680" y="70" width="330" height="76" fill={INK} />
      <text x="704" y="102" fontFamily={UI} fontSize="15" fontWeight="600" fill="#fff">Insight</text>
      <text x="704" y="126" fontFamily={UI} fontSize="12" fill="#fff" opacity="0.78">every claim cites its frozen source</text>

      <rect x="680" y="212" width="330" height="76" fill="#fff" stroke={MUTED} strokeWidth="1.2" strokeDasharray="5 5" />
      <text x="704" y="244" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>Declined</text>
      <text x="704" y="268" fontFamily={UI} fontSize="12" fill={MUTED}>the reason is written down</text>

      <line x1="30" y1="312" x2="1050" y2="312" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="334" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        A quote that cannot be matched to the preserved source text does not ship.
      </text>
    </svg>
  )
}
