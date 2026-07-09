import { NavLink, Route, Routes } from 'react-router-dom'
import Registry from './pages/Registry'
import SystemMap from './pages/SystemMap'
import Accounts from './pages/Accounts'
import Architecture from './pages/Architecture'

export default function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          Frontier Lab Intelligence
        </div>
        <nav aria-label="Main">
          <NavLink to="/" end>Registry</NavLink>
          <NavLink to="/system">System</NavLink>
          <NavLink to="/channels">Channels</NavLink>
          <NavLink to="/architecture">Architecture</NavLink>
          <span className="nav-soon">Insights · Reports — soon</span>
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Registry />} />
          <Route path="/system" element={<SystemMap />} />
          <Route path="/channels" element={<Accounts />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/architecture" element={<Architecture />} />
        </Routes>
      </main>
    </div>
  )
}
