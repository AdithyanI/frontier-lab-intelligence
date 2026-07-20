/* Decision figures for the How-it-works write-up. Each one justifies a
   design choice at one funnel stage, in the same visual language as the
   architecture diagrams: mono kickers, hairlines, blue accents. */

const INK = '#151515'
const MUTED = '#6b6b68'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
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
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">ONE SOURCE FIRST, DONE DEEPLY</text>

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
        ANNOUNCED AND ARGUED HERE ANYWAY
      </text>

      <rect x="420" y="204" width="240" height="118" fill={INK} />
      <text x="444" y="238" fontFamily={MONO} fontSize="9.5" fill={BLUE} letterSpacing="0.08em">CHOSEN FIRST</text>
      <text x="444" y="272" fontFamily={UI} fontSize="21" fontWeight="600" fill="#fff">X</text>
      <text x="444" y="300" fontFamily={UI} fontSize="12.5" fill="#fff" opacity="0.78">the front page of AI</text>

      <text x="684" y="290" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">
        RESEARCHERS UP TO CEOS WRITE HERE THEMSELVES
      </text>

      <line x1="30" y1="352" x2="1050" y2="352" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="378" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        When something lands in any of these, it lands on X at the same moment, in one place. The other classes plug in later as channels.
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
      aria-label="A wide field of grey dots stands for all observed X accounts. A dashed boundary holds a small set of blue dots: the screened Registry of 2,591 identities kept out of 557,363 observed accounts."
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

      <text x="60" y="322" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">557,363 ACCOUNTS OBSERVED</text>
      <text x="760" y="322" textAnchor="middle" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.06em">THE REGISTRY · 2,591 SCREENED IDENTITIES</text>

      <line x1="30" y1="336" x2="1050" y2="336" stroke={MUTED} strokeWidth="1" strokeDasharray="4 5" opacity="0.35" />
      <text x="30" y="356" fontFamily={UI} fontSize="11.5" fill={MUTED}>
        Only what the blue set posts gets collected. Every admission or rejection keeps its reason.
      </text>
    </svg>
  )
}
