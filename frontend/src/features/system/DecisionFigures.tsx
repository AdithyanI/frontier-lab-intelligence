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

/* Stage 2: preserve before interpreting. Posts come only from the accounts
   we chose to track; the platform's own retweet, quote, and reply links
   group them into one exact Event, and linked documents are frozen
   alongside. No opinions yet. */
export function CollectFigure() {
  const relations = [
    { y: 76, title: 'Post', root: true },
    { y: 130, title: 'Retweet', root: false },
    { y: 184, title: 'Quote', root: false },
    { y: 238, title: 'Reply', root: false },
  ]
  return (
    <svg
      viewBox="0 0 1080 392"
      role="img"
      aria-label="Posts come only from the tracked network of 2,431 people and 160 organizations. A post and the retweets, quotes, and replies the platform declares against it are grouped into one exact Event. A linked paper or repository is frozen as text and attached to the same Event."
    >
      <defs>
        <marker id="collect-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">COLLECT · PRESERVE BEFORE INTERPRETING</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">ONE OBSERVED DAY AT A TIME</text>

      <text x="30" y="121" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">TRACKED NETWORK</text>
      <rect x="30" y="135" width="200" height="88" fill="#fff" stroke={BLUE_MID} strokeWidth="1.4" />
      <text x="52" y="169" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>2,431 people</text>
      <text x="52" y="199" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>160 organizations</text>
      <text x="30" y="247" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">WE CHOOSE WHO WE WATCH</text>
      <line x1="230" y1="179" x2="274" y2="179" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#collect-arrow)" />

      <text x="278" y="62" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">DECLARED RELATIONS</text>
      {relations.map((relation) => (
        <g key={relation.title}>
          <rect
            x="278"
            y={relation.y}
            width="132"
            height="44"
            fill="#fff"
            stroke={relation.root ? BLUE_MID : MUTED}
            strokeWidth="1"
          />
          <text x="298" y={relation.y + 28} fontFamily={UI} fontSize="14" fontWeight="600" fill={INK} opacity="0.85">{relation.title}</text>
          <line x1="410" y1={relation.y + 22} x2="470" y2="179" stroke={MUTED} strokeWidth="1" opacity="0.6" />
        </g>
      ))}
      <text x="278" y="308" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">AS POSTED, UNCHANGED</text>

      <line x1="470" y1="179" x2="500" y2="179" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#collect-arrow)" />

      <text x="508" y="121" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">GROUPED BY DECLARED LINKS</text>
      <rect x="508" y="137" width="224" height="84" fill={INK} />
      <text x="530" y="173" fontFamily={UI} fontSize="16" fontWeight="600" fill="#fff">One exact Event</text>
      <text x="530" y="199" fontFamily={UI} fontSize="12" fill="#fff" opacity="0.78">nothing merged by topic</text>

      <line x1="800" y1="179" x2="740" y2="179" stroke={BLUE_MID} strokeWidth="1.2" strokeDasharray="4 4" markerEnd="url(#collect-arrow)" />
      <rect x="800" y="143" width="250" height="72" fill="#fff" stroke={MUTED} strokeWidth="1.2" strokeDasharray="5 5" />
      <text x="822" y="175" fontFamily={UI} fontSize="14" fontWeight="600" fill={INK}>Linked paper or repo</text>
      <text x="822" y="197" fontFamily={UI} fontSize="12" fill={MUTED}>text frozen for citation checks</text>

      <line x1="30" y1="350" x2="1050" y2="350" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="372" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        Every post comes from an account we chose to track. Grouping then uses only relationships the platform itself declares.
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
      aria-label="Left: a day of Events as unordered bars. Right: the same bars ordered by the daily Event ranking rules, with the top of the day marked as what goes to judging first."
    >
      <defs>
        <marker id="rank-order-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">RANK · ORDER THE DAY, DO NOT JUDGE IT</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">TRANSPARENT ORDERING RULES</text>

      {heights.map((height, index) => (
        <rect key={`u-${index}`} x={70 + index * 34} y={baseline - height} width="22" height={height} fill={MUTED} opacity="0.35" />
      ))}
      <line x1="70" y1={baseline} x2={70 + 9 * 34 + 22} y2={baseline} stroke={MUTED} strokeWidth="1" />
      <text x="70" y="288" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">A DAY OF EVENTS, AS THEY ARRIVED</text>

      <line x1="460" y1="196" x2="586" y2="196" stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#rank-order-arrow)" />
      <text x="472" y="180" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">ORDERED</text>

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
      <text x="620" y="288" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">THE SAME DAY, ORDERED BY NETWORK ATTENTION</text>

      <line x1="30" y1="312" x2="1050" y2="312" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="334" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        The rank decides where to look first. It never decides what is true or what matters.
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

/* Stage 3b: how the ordering is decided. Four questions asked in order, each
   one shown as the comparison it actually makes. Nothing is blended, so no
   signal can quietly overpower another. */
export function RankLayersFigure() {
  const dot = (cx: number, cy: number, opacity: number, key: string) => (
    <circle key={key} cx={cx} cy={cy} r="7" fill={BLUE_MID} opacity={opacity} />
  )
  const dots = (count: number, y: number, opacity: number, key: string) =>
    Array.from({ length: count }, (_, i) => dot(688 + i * 21, y, opacity, `${key}-${i}`))

  const rows = [
    { n: '1', title: 'How many voted?', note: 'DISTINCT TRUSTED ENTITIES · QUOTE OR REPOST · ONE EACH' },
    { n: '2', title: 'Tie? Voter network support.', note: 'MEAN TIE-AWARE ENTITY-SUPPORT PERCENTILE' },
    { n: '3', title: 'Tie? Source network support.', note: 'SOURCE-AUTHOR ENTITY-SUPPORT PERCENTILE' },
    { n: '4', title: 'Tie? Public interaction.', note: 'MAX SAME-DAY POST · LIKES · REPLIES · REPOSTS · QUOTES' },
  ]

  return (
    <svg
      viewBox="0 0 1080 580"
      role="img"
      aria-label="The daily rank asks four questions in order instead of blending them into one weighted number. First, how many distinct trusted Registry entities quoted or reposted the complete Event, one vote each and with the source author excluded. If that ties, the average network position of those voters. If that still ties, the network position of the source author. If that still ties, the maximum same-day public interactions on one Event post. Below is a censored check from the current daily-rank-v2 routing cohort: Events with one trusted vote were routing-relevant 34 percent of the time, two votes 54 percent, three to four votes 64 percent, and five or more votes 72 percent."
    >
      <defs>
        <marker id="rank-layer-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
        </marker>
      </defs>

      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">RANK · FOUR QUESTIONS, ASKED IN ORDER</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">NOT A WEIGHTED SUM</text>

      <text x="660" y="66" fontFamily={MONO} fontSize="9" fill={BLUE_INK} letterSpacing="0.06em">▸ THIS ONE GOES FIRST</text>

      {rows.map((row, index) => {
        const y = 82 + index * 104
        const first = y + 30
        const second = y + 66
        const primary = index === 0
        return (
          <g key={row.n}>
            <rect x="60" y={y} width="570" height="88" fill={primary ? INK : '#fff'} stroke={primary ? INK : BLUE_MID} strokeWidth={primary ? 0 : 1.2} />
            <text x="88" y={y + 52} fontFamily={MONO} fontSize="21" fill={primary ? BLUE : BLUE_MID}>{row.n}</text>
            <text x="126" y={y + 42} fontFamily={UI} fontSize="16" fontWeight="600" fill={primary ? '#fff' : INK}>{row.title}</text>
            <text x="126" y={y + 64} fontFamily={MONO} fontSize="9.5" fill={primary ? BLUE : MUTED} letterSpacing="0.06em" opacity={primary ? 0.9 : 1}>{row.note}</text>

            <polygon points={`660,${first - 7} 672,${first} 660,${first + 7}`} fill={BLUE} />

            {index === 0 ? (
              <>
                {dots(3, first, 1, 'r1a')}
                {dots(1, second, 1, 'r1b')}
                <text x="770" y={first + 4} fontFamily={MONO} fontSize="9" fill={MUTED} letterSpacing="0.06em">MORE TRUSTED VOTES</text>
                <text x="770" y={second + 4} fontFamily={MONO} fontSize="9" fill={MUTED} letterSpacing="0.06em">FEWER TRUSTED VOTES</text>
              </>
            ) : null}

            {index === 1 ? (
              <>
                {dots(3, first, 1, 'r2a')}
                {dots(3, second, 0.28, 'r2b')}
                <text x="770" y={first + 4} fontFamily={MONO} fontSize="9" fill={MUTED} letterSpacing="0.06em">HIGH IN THE NETWORK</text>
                <text x="770" y={second + 4} fontFamily={MONO} fontSize="9" fill={MUTED} letterSpacing="0.06em">LOW IN THE NETWORK</text>
              </>
            ) : null}

            {index === 2 ? (
              <>
                {dots(3, first, 0.55, 'r3a')}
                {dots(3, second, 0.55, 'r3b')}
                <rect x="770" y={first - 9} width="150" height="18" fill={BLUE_MID} opacity="0.85" />
                <rect x="770" y={second - 9} width="52" height="18" fill={BLUE_MID} opacity="0.28" />
                <text x="936" y={first + 4} fontFamily={MONO} fontSize="9" fill={MUTED} letterSpacing="0.06em">AUTHOR</text>
              </>
            ) : null}

            {index === 3 ? (
              <>
                {dots(3, first, 0.55, 'r4a')}
                {dots(3, second, 0.55, 'r4b')}
                <rect x="770" y={first - 9} width="132" height="18" fill={MUTED} opacity="0.5" />
                <rect x="770" y={second - 9} width="44" height="18" fill={MUTED} opacity="0.22" />
                <text x="936" y={first + 4} fontFamily={MONO} fontSize="9" fill={MUTED} letterSpacing="0.06em">PUBLIC</text>
              </>
            ) : null}

            {index < rows.length - 1 ? (
              <>
                <line x1="345" y1={y + 88} x2="345" y2={y + 102} stroke={BLUE_MID} strokeWidth="1.5" markerEnd="url(#rank-layer-arrow)" />
                <text x="358" y={y + 100} fontFamily={MONO} fontSize="8.5" fill={MUTED} letterSpacing="0.06em">ONLY IF TIED</text>
              </>
            ) : null}
          </g>
        )
      })}

      <line x1="30" y1="502" x2="1050" y2="502" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="532" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">CURRENT V2 ROUTING · CENSORED CHECK</text>
      <text x="30" y="548" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">MORE VOTES · MORE OFTEN ROUTING-RELEVANT</text>
      {[
        ['1 VOTE', 34],
        ['2 VOTES', 54],
        ['3–4 VOTES', 64],
        ['5+ VOTES', 72],
      ].map(([label, rate], index) => {
        const x = 300 + index * 156
        const height = Number(rate) * 0.42
        return (
          <g key={String(label)}>
            <rect x={x} y={546 - height} width="104" height={height} fill={BLUE} opacity={0.4 + index * 0.2} />
            <text x={x} y="562" fontFamily={MONO} fontSize="9" fill={MUTED} letterSpacing="0.05em">{label}</text>
            <text x={x + 104} y="562" textAnchor="end" fontFamily={MONO} fontSize="10" fill={BLUE_INK}>{rate}%</text>
          </g>
        )
      })}
    </svg>
  )
}
