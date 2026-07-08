import { useEffect, useState } from 'react'
import { getJSON, type Stage } from '../api'

export default function SystemMap() {
  const [stages, setStages] = useState<Stage[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getJSON<{ stages: Stage[] }>('/api/status')
      .then((d) => setStages(d.stages))
      .catch((e) => setError(String(e)))
  }, [])

  return (
    <>
      <h1 className="page-title">System</h1>
      <p className="page-sub">
        The pipeline as it actually stands: live counts from the database, not
        a diagram of intentions. Grey stages are designed but not built.
      </p>
      {error && <div className="error-note">Could not load status: {error}</div>}
      {!stages && !error && (
        <div className="map" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="skeleton" style={{ width: '60%', marginBottom: 24 }} />
          ))}
        </div>
      )}
      {stages && (
        <ol className="map" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {stages.map((s) => (
            <li key={s.id} className="stage" data-state={s.state}>
              <div className="stage-rail">
                <span className="stage-dot" data-state={s.state} aria-hidden="true" />
                <span className="stage-line" aria-hidden="true" />
              </div>
              <div className="stage-body">
                <div className="stage-head">
                  <h2 className="stage-name">{s.name}</h2>
                  <span className="stage-state" data-state={s.state}>
                    {s.state}
                  </span>
                </div>
                <p className="stage-summary">{s.summary}</p>
                {s.stats.length > 0 && (
                  <div className="stage-stats">
                    {s.stats.map((st) => (
                      <div key={st.label} className="stat">
                        <span className="stat-value">
                          {st.value.toLocaleString('en-US')}
                        </span>
                        <span className="stat-label">{st.label}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </>
  )
}
