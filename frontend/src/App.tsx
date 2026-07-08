import { NavLink, Route, Routes } from 'react-router-dom'
import SystemMap from './pages/SystemMap'
import Accounts from './pages/Accounts'
import Architecture from './pages/Architecture'

export default function App() {
  return (
    <div className="shell">
      <nav className="nav" aria-label="Main">
        <div className="brand">Frontier Lab Intelligence</div>
        <NavLink to="/" end>System</NavLink>
        <NavLink to="/accounts">Accounts</NavLink>
        <NavLink to="/architecture">Architecture</NavLink>
        <span className="nav-soon">Registry</span>
        <span className="nav-soon">Insights</span>
        <span className="nav-soon">Reports</span>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<SystemMap />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/architecture" element={<Architecture />} />
        </Routes>
      </main>
    </div>
  )
}
