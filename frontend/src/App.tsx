import { useEffect } from 'react'
import { Navigate, NavLink, Route, Routes } from 'react-router-dom'
import { getCachedJSON, type Rankings } from './api'
import Network from './pages/Network'
import Registry from './pages/Registry'
import Ranking from './pages/Ranking'
import Feed from './pages/Feed'
import Artifacts from './pages/Artifacts'
import Insights from './pages/Insights'
import Architecture from './pages/Architecture'

export default function App() {
  useEffect(() => {
    const timer = window.setTimeout(() => {
      getCachedJSON<Rankings>('/api/rankings?limit=300').catch(() => undefined)
    }, 600)
    return () => window.clearTimeout(timer)
  }, [])

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          Frontier Lab Intelligence
        </div>
        <nav aria-label="Main">
          <NavLink to="/network">Network</NavLink>
          <NavLink to="/feed">Feed</NavLink>
          <NavLink to="/artifacts">Artifacts</NavLink>
          <NavLink to="/insights">Insights</NavLink>
          <NavLink to="/architecture">Architecture</NavLink>
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/network/ranking" replace />} />
          <Route path="/network" element={<Network />}>
            <Route index element={<Navigate to="ranking" replace />} />
            <Route path="ranking" element={<Ranking />} />
            <Route path="registry" element={<Registry />} />
          </Route>
          <Route path="/feed" element={<Feed />} />
          <Route path="/artifacts" element={<Artifacts />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/architecture" element={<Architecture />} />
          <Route path="*" element={<Navigate to="/network/ranking" replace />} />
        </Routes>
      </main>
    </div>
  )
}
