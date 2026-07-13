/* Ranking — the trust orbit. Every dot is an account the screened Registry
   cohort collectively follows; distance from center is earned rank, dot size
   is cohort follows. Filled ink = already in the Registry; hollow ring = an
   outsider the inside points at. Click a dot (or a row) to see exactly who
   follows it. Data: /api/rankings over the frozen following snapshot. */

import { useEffect, useMemo, useRef, useState } from 'react'
import {
  getCachedJSON,
  getJSON,
  type Entity,
  type RankingFollowers,
  type RankingNode,
  type Rankings,
} from '../api'
import EntityCard from '../components/EntityCard'

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

const isOrg = (n: RankingNode) => n.entity_kind === 'organization'

type Filter = 'all' | 'person' | 'organization' | 'unknown'

/* One mark on the orbit: circle = person/unknown, square = organization. */
function Mark({
  p,
  fill,
  stroke,
  strokeWidth,
  opacity,
  onEnter,
  onLeave,
  onClick,
}: {
  p: Placed
  fill: string
  stroke: string
  strokeWidth: number
  opacity: number
  onEnter: () => void
  onLeave: () => void
  onClick: () => void
}) {
  const common = {
    fill,
    stroke,
    strokeWidth,
    opacity,
    style: { cursor: 'pointer', transition: 'opacity 150ms ease-out' },
    onMouseEnter: onEnter,
    onMouseLeave: onLeave,
    onClick,
  }
  const title = <title>{`#${p.rank} ${nodeName(p)}`}</title>
  if (isOrg(p)) {
    const s = p.r * 1.8
    return (
      <rect x={p.x - s / 2} y={p.y - s / 2} width={s} height={s} {...common}>
        {title}
      </rect>
    )
  }
  return (
    <circle cx={p.x} cy={p.y} r={p.r} {...common}>
      {title}
    </circle>
  )
}

export default function Ranking() {
  const [data, setData] = useState<Rankings | null>(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<string | null>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const [filter, setFilter] = useState<Filter>('all')
  const [query, setQuery] = useState('')
  const [followers, setFollowers] = useState<RankingFollowers | null>(null)
  const [cardOpen, setCardOpen] = useState(false)
  const [profile, setProfile] = useState<Entity | null>(null)
  const rowRefs = useRef(new Map<string, HTMLButtonElement>())
  const selectedFrom = useRef<'orbit' | 'list'>('orbit')

  useEffect(() => {
    getCachedJSON<Rankings>(`/api/rankings?limit=${N_FETCH}`)
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    setFollowers(null)
    if (!selected) return
    let live = true
    getCachedJSON<RankingFollowers>(
      `/api/rankings/followers/${selected}?limit=${N_FETCH}`,
    )
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

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !cardOpen) setSelected(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [cardOpen])

  const placed = useMemo(() => place(data?.nodes ?? []), [data])
  const byId = useMemo(
    () => new Map(placed.map((p) => [p.x_id, p])),
    [placed],
  )

  const needle = query.trim().toLowerCase()
  const matches = (n: RankingNode) => {
    const inFilter =
      filter === 'all' ||
      (filter === 'unknown'
        ? n.registry_state === 'unknown'
        : n.registry_state === 'active' && n.entity_kind === filter)
    return (
      inFilter &&
      (!needle ||
        n.handle.toLowerCase().includes(needle) ||
        nodeName(n).toLowerCase().includes(needle))
    )
  }

  const followerSet = useMemo(
    () => new Set((followers?.followers ?? []).map((f) => f.x_id)),
    [followers],
  )

  const filtered = placed.filter(matches)

  /* ↑/↓ step through the visible ranking once something is selected */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
      const tag = (e.target as HTMLElement | null)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (!selected || !filtered.length) return
      e.preventDefault()
      const idx = filtered.findIndex((p) => p.x_id === selected)
      const next =
        filtered[
          Math.min(
            Math.max(idx + (e.key === 'ArrowDown' ? 1 : -1), 0),
            filtered.length - 1,
          )
        ]
      if (next && next.x_id !== selected) {
        selectedFrom.current = 'orbit'
        setSelected(next.x_id)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })
  const visibleArcs = useMemo(() => {
    if (!selected) return []
    const target = byId.get(selected)
    if (!target) return []
    return placed.filter((p) => followerSet.has(p.x_id) && p.x_id !== selected)
  }, [placed, byId, followerSet, selected])

  const sel = selected ? byId.get(selected) : undefined
  const hov = hovered ? byId.get(hovered) : undefined
  const run = data?.run

  const selectInOrbit = (id: string) => {
    selectedFrom.current = 'orbit'
    setCardOpen(false)
    if (selected === id) {
      setSelected(null)
    } else {
      setSelected(id)
    }
  }

  const openFromList = (id: string) => {
    selectedFrom.current = 'list'
    setSelected(id)
    setCardOpen(true)
  }

  /* profile card follows the selection while it is open */
  useEffect(() => {
    setProfile(null)
    if (!cardOpen || !selected) return
    const node = byId.get(selected)
    if (!node || node.entity_id == null) return
    let live = true
    getJSON<{ entity: Entity }>(`/api/registry/entity/${node.entity_id}`)
      .then((value) => live && setProfile(value.entity))
      .catch(() => undefined)
    return () => {
      live = false
    }
  }, [cardOpen, selected, byId])

  if (error || (data && !data.available)) {
    return (
      <div className="page">
        <h1 className="page-title">Who does the inside trust?</h1>
        <p className="page-sub mono">
          {data?.reason ?? 'Ranking data is unavailable.'}
        </p>
      </div>
    )
  }

  return (
    <div className="page rank-page">
      <h1 className="page-title">Who does the inside trust?</h1>
      <p className="page-sub">
        Accounts are ranked by how many screened Registry sources follow them
        — never by raw follower count.
      </p>
      {run && (
        <div className="rank-context mono">
          <span>
            Top {fmt(N_FETCH)} of {fmt(run.ranked_accounts)} accounts ·{' '}
            {fmt(run.sources)} screened sources
          </span>
          <details className="method-note">
            <summary>Method</summary>
            <p>
              {run.algorithm.toUpperCase()} · {run.snapshot_id.toUpperCase()} ·{' '}
              {fmt(run.edges)} observed follow edges · {fmt(run.unknown_accounts)}
              {' '}accounts not yet in the Registry
            </p>
          </details>
        </div>
      )}

      <div className="rank-split">
        <div className="rank-orbit-wrap">
          <svg
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            role="img"
            aria-label="Trust orbit: accounts arranged by cohort-trust rank, most trusted at the center"
            onClick={(e) => {
              if (e.target === e.currentTarget) setSelected(null)
            }}
          >
            {/* background hit area so clicking empty space deselects */}
            <rect
              x="0" y="0" width={SIZE} height={SIZE} fill="transparent"
              onClick={() => setSelected(null)}
            />
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
                    strokeOpacity={visibleArcs.length > 60 ? 0.35 : 0.55}
                  />
                )
              })}

            {/* hover halo */}
            {hov && hov.x_id !== selected && (
              <circle
                cx={hov.x}
                cy={hov.y}
                r={hov.r + 5}
                fill="none"
                stroke={BLUE_MID}
                strokeWidth="1.2"
                pointerEvents="none"
              />
            )}

            {/* marks: circles = people, squares = organizations */}
            {placed.map((p) => {
              const dim = !matches(p)
              const isSel = p.x_id === selected
              const isFollower = selected != null && followerSet.has(p.x_id)
              const active = p.registry_state === 'active'
              return (
                <Mark
                  key={p.x_id}
                  p={p}
                  fill={isSel ? BLUE : active ? (isOrg(p) ? BLUE_MID : INK) : '#ffffff'}
                  stroke={
                    isSel ? BLUE_INK : isFollower ? BLUE_MID : isOrg(p) ? BLUE_INK : INK
                  }
                  strokeWidth={isSel ? 2 : active ? 0 : 1.3}
                  opacity={dim ? 0.08 : selected && !isSel && !isFollower ? 0.3 : 1}
                  onEnter={() => setHovered(p.x_id)}
                  onLeave={() => setHovered(null)}
                  onClick={() => selectInOrbit(p.x_id)}
                />
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

            {/* selected halo */}
            {sel && (
              <circle
                cx={sel.x}
                cy={sel.y}
                r={Math.max(sel.r, 5) + 6}
                fill="none"
                stroke={BLUE_MID}
                strokeWidth="1.4"
                pointerEvents="none"
              />
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
            <span><i className="lg-dot lg-ink" /> person in the Registry</span>
            <span><i className="lg-sq" /> organization</span>
            <span><i className="lg-dot lg-hollow" /> discovered — not yet in</span>
            <span><i className="lg-dot lg-blue" /> selected</span>
            <span><i className="lg-arc" /> follows it</span>
          </div>
          {sel && followers?.available ? (
            <p className="rank-arc-note mono">
              {fmt(followers.total)} of {fmt(run?.sources)} screened sources follow @{sel.handle}
              {' · '}
              {fmt(visibleArcs.length)} of them are in this view
            </p>
          ) : null}
        </div>

        <aside className="rank-side">
          <div className="rank-controls">
            <input
              className="search rank-search"
              placeholder="Find anyone…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="rank-filter" role="tablist" aria-label="Kind">
              {(
                [
                  ['all', 'All'],
                  ['person', 'People'],
                  ['organization', 'Orgs'],
                  ['unknown', 'Discovered'],
                ] as [Filter, string][]
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

          <ol className="rank-list">
            {filtered.length === 0 && (
              <li className="rank-empty mono">
                No one in the top {N_FETCH} matches — the account may rank
                deeper in the full 463K.
              </li>
            )}
            {filtered.map((p) => (
              <li key={p.x_id}>
                <button
                  ref={(el) => {
                    if (el) rowRefs.current.set(p.x_id, el)
                    else rowRefs.current.delete(p.x_id)
                  }}
                  className={`rank-row ${p.x_id === selected ? 'sel' : ''}`}
                  onClick={() => openFromList(p.x_id)}
                  onMouseEnter={() => setHovered(p.x_id)}
                  onMouseLeave={() => setHovered(null)}
                >
                  <span className="rk mono">{p.rank}</span>
                  <i
                    className={
                      isOrg(p)
                        ? 'lg-sq'
                        : `lg-dot ${p.registry_state === 'active' ? 'lg-ink' : 'lg-hollow'}`
                    }
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
          {(filter !== 'all' || needle) && (
            <p className="rank-shown mono">
              {fmt(filtered.length)} matching in the top {N_FETCH}
            </p>
          )}
        </aside>
      </div>

      <EntityCard
        entity={cardOpen ? profile : null}
        fallback={
          cardOpen && sel && sel.entity_id == null
            ? { name: nodeName(sel), handle: sel.handle }
            : null
        }
        context={
          cardOpen && sel ? (
            <section className="ent-card-rank" aria-label="Trust ranking">
              <div className="ent-card-rank-stats">
                <div className="stat">
                  <span className="v">#{sel.rank}</span>
                  <span className="k">Trust rank</span>
                </div>
                <div className="stat">
                  <span className="v">
                    {fmt(sel.cohort_follow_count)}
                    <span className="sub">
                      {' '}· {(sel.cohort_follow_share * 100).toFixed(1)}%
                    </span>
                  </span>
                  <span className="k">Cohort follows</span>
                </div>
                <div className="stat">
                  <span className="v">{fmt(sel.followers_count)}</span>
                  <span className="k">Raw X followers</span>
                </div>
              </div>
              {followers?.available && followers.followers && (
                <p className="ent-card-rank-followers">
                  Followed by{' '}
                  {followers.followers.slice(0, 4).map((f, i) => (
                    <span key={f.x_id}>
                      {i > 0 && ', '}
                      <strong>
                        {f.entity_name || f.display_name || `@${f.handle}`}
                      </strong>
                    </span>
                  ))}
                  {(followers.total ?? 0) > 4 &&
                    ` and ${fmt((followers.total ?? 0) - 4)} more of the cohort.`}
                </p>
              )}
              {sel.entity_id == null && (
                <a
                  className="ent-card-rank-handle mono"
                  href={`https://x.com/${sel.handle}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  @{sel.handle} on X ↗
                </a>
              )}
            </section>
          ) : undefined
        }
        onClose={() => setCardOpen(false)}
      />
    </div>
  )
}
