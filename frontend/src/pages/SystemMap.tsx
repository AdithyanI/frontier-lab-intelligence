import { useEffect, useState } from 'react'
import { getJSON, type Stage } from '../api'

function findStat(stages: Stage[], stageId: string, label: string): number {
  const s = stages.find((x) => x.id === stageId)
  return s?.stats.find((st) => st.label === label)?.value ?? 0
}

export default function SystemMap() {
  const [stages, setStages] = useState<Stage[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getJSON<{ stages: Stage[] }>('/api/status')
      .then((d) => setStages(d.stages))
      .catch((e) => setError(String(e)))
  }, [])

  if (error) return <div className="page"><div className="error-note">Could not load status: {error}</div></div>
  if (!stages) {
    return (
      <div className="page" aria-busy="true">
        <div className="skeleton" style={{ width: '40%', height: 40 }} />
      </div>
    )
  }

  const edges = findStat(stages, 'sources', 'graph edges')
  const candidates = findStat(stages, 'registry', 'candidate accounts')
  const entities = findStat(stages, 'registry', 'confirmed entities')

  return (
    <div className="hero">
      <div className="hero-left">
        <div className="hero-kicker">FRONTIER LAB INTELLIGENCE</div>
        <h1 className="hero-title">Watching the people who build the frontier.</h1>
        <p className="hero-sub">
          A social-graph-derived registry of frontier-AI labs and their key
          people — their public output extracted, scored, and delivered as
          signal, not noise.
        </p>
        <div className="hero-numbers">
          <div className="big-stat">
            <span className="v">{edges.toLocaleString('en-US')}</span>
            <span className="l">observed follow edges</span>
          </div>
          <div className="big-stat">
            <span className="v">{candidates.toLocaleString('en-US')}</span>
            <span className="l">candidate accounts</span>
          </div>
          <div className="big-stat">
            <span className="v">{entities.toLocaleString('en-US')}</span>
            <span className="l">confirmed entities</span>
          </div>
        </div>
      </div>
      <ol className="rail" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {stages.map((s) => (
          <li key={s.id} className="rail-stage" data-state={s.state}>
            <div className="rail-gutter">
              <span className="rail-node" aria-hidden="true" />
            </div>
            <div className="rail-body">
              <div className="rail-head">
                <span className="rail-name">{s.name}</span>
                <span className="rail-state" data-state={s.state}>{s.state}</span>
              </div>
              <p className="rail-summary">{s.summary}</p>
              {s.stats.length > 0 && (
                <div className="rail-stats">
                  {s.stats.map((st) => (
                    <div key={st.label}>
                      <span className="stat-v">{st.value.toLocaleString('en-US')}</span>{' '}
                      <span className="stat-l">{st.label}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
