import { useEffect } from 'react'
import { Navigate, NavLink, Route, Routes } from 'react-router-dom'
import { getCachedJSON, type Rankings } from './api'
import Registry from './pages/Registry'
import Ranking from './pages/Ranking'
import Feed from './pages/Feed'
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
          <NavLink to="/" end>Registry</NavLink>
          <NavLink to="/ranking">Ranking</NavLink>
          <NavLink to="/feed">Feed</NavLink>
          <NavLink to="/architecture">Architecture</NavLink>
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Registry />} />
          <Route path="/ranking" element={<Ranking />} />
          <Route path="/feed" element={<Feed />} />
          <Route path="/architecture" element={<Architecture />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
