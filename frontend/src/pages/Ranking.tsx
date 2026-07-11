/* Ranking — the trust orbit. Every dot is an account the screened Registry
   cohort collectively follows; distance from center is earned rank, dot size
   is cohort follows. Filled ink = already in the Registry; hollow ring = an
   outsider the inside points at. Click a dot (or a row) to see exactly who
   follows it. Data: /api/rankings over the frozen following snapshot. */

import { useEffect, useMemo, useRef, useState } from 'react'
import {
  getJSON,
  type RankingFollowers,
  type RankingNode,
  type Rankings,
} from '../api'

const INK = '#151515'
const MUTED = '#6b6b68'
const BLUE = '#5bc5f2'
const BLUE_MID = '#4391b4'
const BLUE_INK = '#235165'
const MONO = "'IBM Plex Mono', monospace"

const N_FETCH = 300
const GOLDEN = Math.PI * (3 - Math.sqrt(5))
const SIZE = 720
const C = SIZE / 2
const R_MIN = 14
const R_MAX = 330

const fmt = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US')

type Placed = RankingNode & { x: number; y: number; r: number; angle: number }

function place(nodes: RankingNode[]): Placed[] {
  const n = nodes.length
  if (!n) return []
  const maxC = nodes[0].cohort_follow_count || 1
  const minC = nodes[n - 1].cohort_follow_count || 0
  const span = Math.max(maxC - minC, 1)
  return nodes.map((node, i) => {
    const angle = i * GOLDEN - Math.PI / 2
    const radius = R_MIN + Math.sqrt(i / Math.max(n - 1, 1)) * (R_MAX - R_MIN)
    const t = (node.cohort_follow_count - minC) / span
    return {
      ...node,
      angle,
      x: C + Math.cos(angle) * radius,
      y: C + Math.sin(angle) * radius,
      r: 2.2 + 9.8 * Math.pow(t, 1.6),
    }
  })
}

const nodeName = (n: RankingNode) =>
  n.entity_name || n.display_name || `@${n.handle}`

type StateFilter = 'all' | 'active' | 'unknown'

export default function Ranking() {
  const [data, setData] = useState<Rankings | null>(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<string | null>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const [filter, setFilter] = useState<StateFilter>('all')
  const [query, setQuery] = useState('')
  const [followers, setFollowers] = useState<RankingFollowers | null>(null)
  const rowRefs = useRef(new Map<string, HTMLButtonElement>())
  const selectedFrom = useRef<'orbit' | 'list'>('orbit')

  useEffect(() => {
    getJSON<Rankings>(`/api/rankings?limit=${N_FETCH}`)
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    setFollowers(null)
    if (!selected) return
    let live = true
    getJSON<RankingFollowers>(`/api/rankings/followers/${selected}`)
      .then((f) => live && setFollowers(f))
      .catch(() => undefined)
    return () => {
      live = false
    }
  }, [selected])

  useEffect(() => {
    if (selected && selectedFrom.current === 'orbit')
      rowRefs.current.get(selected)?.scrollIntoView({ block: 'nearest' })
  }, [selected])

  const placed = useMemo(() => place(data?.nodes ?? []), [data])
  const byId = useMemo(
    () => new Map(placed.map((p) => [p.x_id, p])),
    [placed],
  )

  const needle = query.trim().toLowerCase()
  const matches = (n: RankingNode) =>
    (filter === 'all' || n.registry_state === filter) &&
    (!needle ||
      n.handle.toLowerCase().includes(needle) ||
      nodeName(n).toLowerCase().includes(needle))

  const followerSet = useMemo(
    () => new Set((followers?.followers ?? []).map((f) => f.x_id)),
    [followers],
  )
  const visibleArcs = useMemo(() => {
    if (!selected) return []
    const target = byId.get(selected)
    if (!target) return []
    return placed.filter((p) => followerSet.has(p.x_id) && p.x_id !== selected)
  }, [placed, byId, followerSet, selected])

  const sel = selected ? byId.get(selected) : undefined
  const hov = hovered ? byId.get(hovered) : undefined
  const run = data?.run

  const pick = (id: string, from: 'orbit' | 'list') => {
    selectedFrom.current = from
    setSelected((cur) => (cur === id ? null : id))
  }

  if (error || (data && !data.available)) {
    return (
      <div className="page">
        <div className="page-kicker">RANKING</div>
        <h1 className="page-title">Who does the inside trust?</h1>
        <p className="page-sub mono">
          {data?.reason ?? 'Ranking data is unavailable.'}
        </p>
      </div>
    )
  }

  return (
    <div className="page rank-page">
      <div className="page-kicker">
        RANKING · {run ? `${run.algorithm.toUpperCase()} · ${run.snapshot_id.toUpperCase()}` : '…'}
      </div>
      <h1 className="page-title">Who does the inside trust?</h1>
      <p className="page-sub">
        Every account placed by how many of the screened Registry cohort follow
        it — distance from center is earned rank, never raw follower count.
        Filled dots are already in the Registry; hollow rings are outsiders the
        inside collectively points at. Click anyone to see exactly who follows
        them.
      </p>
      {run && (
        <div className="rank-stats mono">
          <span>{fmt(run.sources)} screened sources</span>
          <span>{fmt(run.edges)} follow edges</span>
          <span>{fmt(run.ranked_accounts)} accounts ranked</span>
          <span>{fmt(run.unknown_accounts)} not yet in the Registry</span>
        </div>
      )}

      <div className="rank-split">
        <div className="rank-orbit-wrap">
          <svg
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            role="img"
            aria-label="Trust orbit: accounts arranged by cohort-trust rank, most trusted at the center"
          >
            {/* guide rings with the rank they mark */}
            {[10, 50, 150, N_FETCH].map((rank) => {
              const idx = Math.min(rank - 1, placed.length - 1)
              if (idx < 0) return null
              const rr =
                R_MIN + Math.sqrt(idx / Math.max(placed.length - 1, 1)) * (R_MAX - R_MIN)
              return (
                <g key={rank}>
                  <circle cx={C} cy={C} r={rr} fill="none" stroke={INK} strokeOpacity="0.13" strokeDasharray="2 5" />
                  <text x={C} y={C - rr - 5} textAnchor="middle" fontFamily={MONO} fontSize="10" fill={MUTED} stroke="#ffffff" strokeWidth="3.5" paintOrder="stroke">
                    {rank}
                  </text>
                </g>
              )
            })}

            {/* follow arcs into the selected account */}
            {sel &&
              visibleArcs.map((p) => {
                const mx = (p.x + sel.x) / 2
                const my = (p.y + sel.y) / 2
                const cx = mx + (C - mx) * 0.42
                const cy = my + (C - my) * 0.42
                return (
                  <path
                    key={p.x_id}
                    d={`M ${p.x} ${p.y} Q ${cx} ${cy} ${sel.x} ${sel.y}`}
                    fill="none"
                    stroke={BLUE}
                    strokeWidth="0.9"
                    strokeOpacity="0.5"
                  />
                )
              })}

            {/* dots */}
            {placed.map((p) => {
              const dim = !matches(p)
              const isSel = p.x_id === selected
              const isFollower = selected != null && followerSet.has(p.x_id)
              const active = p.registry_state === 'active'
              return (
                <circle
                  key={p.x_id}
                  cx={p.x}
                  cy={p.y}
                  r={p.r}
                  fill={isSel ? BLUE : active ? INK : '#ffffff'}
                  stroke={isSel ? BLUE_INK : isFollower ? BLUE_MID : INK}
                  strokeWidth={isSel ? 2 : active ? 0 : 1.3}
                  opacity={dim ? 0.08 : selected && !isSel && !isFollower ? 0.3 : 1}
                  style={{ cursor: 'pointer' }}
                  onMouseEnter={() => setHovered(p.x_id)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => pick(p.x_id, 'orbit')}
                >
                  <title>{`#${p.rank} ${nodeName(p)}`}</title>
                </circle>
              )
            })}

            {/* permanent labels for the innermost few, radiating outward */}
            {placed.slice(0, 3).map((p) => {
              const lx = p.x + Math.cos(p.angle) * (p.r + 9)
              const ly = p.y + Math.sin(p.angle) * (p.r + 9)
              const right = Math.cos(p.angle) >= 0
              return (
                <text
                  key={p.x_id}
                  x={lx}
                  y={ly + 3.5}
                  textAnchor={right ? 'start' : 'end'}
                  fontFamily={MONO}
                  fontSize="11"
                  fontWeight="600"
                  fill={INK}
                  stroke="#ffffff"
                  strokeWidth="3.5"
                  paintOrder="stroke"
                  pointerEvents="none"
                >
                  {p.handle}
                </text>
              )
            })}

            {/* hover label */}
            {hov && hov.x_id !== selected && (
              <g pointerEvents="none">
                <text
                  x={hov.x >= C ? hov.x - hov.r - 8 : hov.x + hov.r + 8}
                  y={hov.y + 4}
                  textAnchor={hov.x >= C ? 'end' : 'start'}
                  fontFamily={MONO}
                  fontSize="12"
                  fontWeight="600"
                  fill={INK}
                  stroke="#ffffff"
                  strokeWidth="4"
                  paintOrder="stroke"
                >
                  {`${nodeName(hov)} · #${hov.rank}`}
                </text>
              </g>
            )}

            {/* selected label */}
            {sel && (
              <text
                x={sel.x >= C ? sel.x - sel.r - 9 : sel.x + sel.r + 9}
                y={sel.y + 4}
                textAnchor={sel.x >= C ? 'end' : 'start'}
                fontFamily={MONO}
                fontSize="12.5"
                fontWeight="600"
                fill={BLUE_INK}
                stroke="#ffffff"
                strokeWidth="4"
                paintOrder="stroke"
                pointerEvents="none"
              >
                {`${nodeName(sel)} · #${sel.rank}`}
              </text>
            )}
          </svg>

          <div className="rank-legend mono">
            <span><i className="lg-dot lg-ink" /> in the Registry</span>
            <span><i className="lg-dot lg-hollow" /> not yet — discovered</span>
            <span><i className="lg-dot lg-blue" /> selected</span>
            <span><i className="lg-arc" /> follows it</span>
          </div>
          {sel && followers?.available && (
            <p className="rank-arc-note mono">
              {fmt(followers.total)} of {fmt(run?.sources)} screened sources follow @{sel.handle}
              {' · '}
              {fmt(visibleArcs.length)} of them are in this view
            </p>
          )}
        </div>

        <aside className="rank-side">
          <div className="rank-controls">
            <input
              className="search rank-search"
              placeholder="Find anyone…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="rank-filter" role="tablist" aria-label="Registry state">
              {(
                [
                  ['all', 'All'],
                  ['active', 'In Registry'],
                  ['unknown', 'Discovered'],
                ] as [StateFilter, string][]
              ).map(([value, label]) => (
                <button
                  key={value}
                  role="tab"
                  aria-selected={filter === value}
                  className={filter === value ? 'on' : ''}
                  onClick={() => setFilter(value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {sel && (
            <div className="rank-detail">
              <div className="rank-detail-head">
                <div>
                  <div className="rank-detail-name">{nodeName(sel)}</div>
                  <a
                    className="mono rank-detail-handle"
                    href={`https://x.com/${sel.handle}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    @{sel.handle}
                  </a>
                </div>
                <span className={`rank-pill ${sel.registry_state}`}>
                  {sel.registry_state === 'active' ? 'IN REGISTRY' : 'DISCOVERED'}
                </span>
              </div>
              <div className="rank-detail-grid mono">
                <span className="l">trust rank</span>
                <span>#{sel.rank}</span>
                <span className="l">cohort follows</span>
                <span>{fmt(sel.cohort_follow_count)} · {(sel.cohort_follow_share * 100).toFixed(1)}%</span>
                <span className="l">raw X followers</span>
                <span>{fmt(sel.followers_count)}</span>
              </div>
              {followers?.available && followers.followers && (
                <p className="rank-detail-followers">
                  Followed by{' '}
                  {followers.followers.slice(0, 4).map((f, i) => (
                    <span key={f.x_id}>
                      {i > 0 && ', '}
                      <strong>{f.entity_name || f.display_name || `@${f.handle}`}</strong>
                    </span>
                  ))}
                  {(followers.total ?? 0) > 4 &&
                    ` and ${fmt((followers.total ?? 0) - 4)} more of the cohort.`}
                </p>
              )}
            </div>
          )}

          <ol className="rank-list">
            {placed.filter(matches).map((p) => (
              <li key={p.x_id}>
                <button
                  ref={(el) => {
                    if (el) rowRefs.current.set(p.x_id, el)
                    else rowRefs.current.delete(p.x_id)
                  }}
                  className={`rank-row ${p.x_id === selected ? 'sel' : ''}`}
                  onClick={() => pick(p.x_id, 'list')}
                  onMouseEnter={() => setHovered(p.x_id)}
                  onMouseLeave={() => setHovered(null)}
                >
                  <span className="rk mono">{p.rank}</span>
                  <i
                    className={`lg-dot ${p.registry_state === 'active' ? 'lg-ink' : 'lg-hollow'}`}
                  />
                  <span className="nm">
                    <span className="nm-name">{nodeName(p)}</span>
                    <span className="nm-handle mono">@{p.handle}</span>
                  </span>
                  <span className="sc mono">{fmt(p.cohort_follow_count)}</span>
                  <i
                    className="bar"
                    style={{ width: `${Math.max(p.cohort_follow_share * 100, 2)}%` }}
                  />
                </button>
              </li>
            ))}
          </ol>
        </aside>
      </div>
    </div>
  )
}
