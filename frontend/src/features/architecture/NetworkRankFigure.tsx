/* X follow graph figure: why an account ranks higher. Shared by the
   Architecture numbers section and the How-it-works stage 1 write-up. */

const INK = '#151515'
const MUTED = '#6b6b68'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
const MONO = "'IBM Plex Mono', monospace"
const UI = "'Inter', system-ui, sans-serif"

function ArrowDefs({ id }: { id: string }) {
  return (
    <defs>
      <marker id={id} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L8,4 L0,8 z" fill={BLUE_MID} />
      </marker>
    </defs>
  )
}

export default function NetworkRankFigure() {
  const leftFollowerField = Array.from({ length: 15 }, (_, index) => ({
    x: 82 + (index % 3) * 24,
    y: 108 + Math.floor(index / 3) * 24,
  }))
  const leftScreenedIndices = new Set([0, 4, 8, 10, 14])
  const rightFollowerField = Array.from({ length: 35 }, (_, index) => ({
    x: 582 + (index % 7) * 24,
    y: 108 + Math.floor(index / 7) * 24,
  }))
  const rightScreenedIndex = 25
  const supportTicks = [0, 1, 2, 3, 4]
  return (
    <svg
      viewBox="0 0 1080 288"
      role="img"
      aria-label="X follow graph and network support, observed as a slow-moving snapshot: Account A has fewer public followers but five screened Registry followers, while Account B has many public followers but only one screened Registry follower. The five screened signals count, public audience size does not."
    >
      <ArrowDefs id="rank-arrow" />
      <text x="30" y="34" fontFamily={MONO} fontSize="11" fill={BLUE_INK} letterSpacing="0.08em">X FOLLOW GRAPH · WHY AN ACCOUNT RANKS HIGHER</text>
      <text x="1050" y="34" textAnchor="end" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">SLOW-MOVING SNAPSHOT</text>
      <line x1="540" y1="60" x2="540" y2="276" stroke={MUTED} strokeWidth="1" opacity="0.22" />

      <text x="70" y="72" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">FEWER FOLLOWERS OVERALL</text>
      <text x="70" y="90" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.05em">BUT 5 SCREENED FOLLOWERS</text>
      {leftFollowerField.map((node, index) => (
        leftScreenedIndices.has(index) ? null : (
          <line key={`a-public-line-${index}`} x1={node.x + 6} y1={node.y} x2="286" y2="168" stroke={MUTED} strokeWidth="0.9" strokeDasharray="2 5" opacity="0.2" />
        )
      ))}
      {leftFollowerField.map((node, index) => (
        leftScreenedIndices.has(index) ? (
          <line key={`a-screened-line-${index}`} x1={node.x + 7} y1={node.y} x2="286" y2="168" stroke={BLUE_MID} strokeWidth="1.2" opacity="0.72" markerEnd="url(#rank-arrow)" />
        ) : null
      ))}
      {leftFollowerField.map((node, index) => (
        <circle
          key={`a-follower-${index}`}
          cx={node.x}
          cy={node.y}
          r="4.5"
          fill={leftScreenedIndices.has(index) ? BLUE : '#fff'}
          stroke={leftScreenedIndices.has(index) ? BLUE : MUTED}
          strokeWidth={leftScreenedIndices.has(index) ? 0 : 1}
          opacity={leftScreenedIndices.has(index) ? 1 : 0.52}
        />
      ))}
      <rect x="296" y="138" width="174" height="60" fill={INK} />
      <text x="320" y="174" fontFamily={UI} fontSize="15" fontWeight="600" fill="#fff">Entity A</text>
      <text x="296" y="222" fontFamily={MONO} fontSize="9" fill={BLUE_INK} letterSpacing="0.06em">COUNTED SUPPORT</text>
      {supportTicks.map((tick) => (
        <rect key={`a-tick-${tick}`} x={296 + tick * 29} y="232" width="23" height="8" fill={BLUE} />
      ))}
      <text x="296" y="264" fontFamily={UI} fontSize="12.5" fontWeight="600" fill={INK}>5 of the voter set → higher support</text>

      <text x="582" y="72" fontFamily={MONO} fontSize="9.5" fill={MUTED} letterSpacing="0.06em">MANY FOLLOWERS OVERALL</text>
      <text x="582" y="90" fontFamily={MONO} fontSize="9.5" fill={BLUE_INK} letterSpacing="0.05em">BUT ONLY 1 SCREENED FOLLOWER</text>
      {rightFollowerField.map((node, index) => (
        index === rightScreenedIndex ? null : (
          <line key={`crowd-line-${index}`} x1={node.x + 6} y1={node.y} x2="794" y2="168" stroke={MUTED} strokeWidth="0.9" strokeDasharray="2 5" opacity="0.2" />
        )
      ))}
      {rightFollowerField.map((node, index) => (
        <circle
          key={`crowd-node-${index}`}
          cx={node.x}
          cy={node.y}
          r="4.5"
          fill={index === rightScreenedIndex ? BLUE : '#fff'}
          stroke={index === rightScreenedIndex ? BLUE : MUTED}
          strokeWidth={index === rightScreenedIndex ? 0 : 1}
          opacity={index === rightScreenedIndex ? 1 : 0.52}
        />
      ))}
      <line
        x1={rightFollowerField[rightScreenedIndex].x + 7}
        y1={rightFollowerField[rightScreenedIndex].y}
        x2="794"
        y2="168"
        stroke={BLUE_MID}
        strokeWidth="1.4"
        markerEnd="url(#rank-arrow)"
      />
      <rect x="804" y="138" width="174" height="60" fill="#fff" stroke={MUTED} strokeWidth="1.2" />
      <text x="828" y="174" fontFamily={UI} fontSize="15" fontWeight="600" fill={INK}>Entity B</text>
      <text x="804" y="222" fontFamily={MONO} fontSize="9" fill={MUTED} letterSpacing="0.06em">COUNTED SUPPORT</text>
      {supportTicks.map((tick) => (
        <rect
          key={`b-tick-${tick}`}
          x={804 + tick * 29}
          y="232"
          width="23"
          height="8"
          fill={tick === 0 ? BLUE : '#fff'}
          stroke={tick === 0 ? BLUE : MUTED}
          strokeWidth={tick === 0 ? 0 : 1}
          opacity={tick === 0 ? 1 : 0.38}
        />
      ))}
      <text x="804" y="264" fontFamily={UI} fontSize="12.5" fill={INK}>1 of the voter set → lower support</text>
    </svg>
  )
}
