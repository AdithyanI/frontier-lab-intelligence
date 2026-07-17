import { NavLink, Outlet } from 'react-router-dom'

export default function System() {
  return (
    <div className="page system-page">
      <header className="system-head">
        <h1 className="page-title">System</h1>
        <p className="page-sub">
          Check the current published checkpoint, then inspect how evidence
          becomes audience-specific intelligence.
        </p>
        <nav className="ruled-nav system-tabs" aria-label="System views">
          <NavLink to="/system/status">Status</NavLink>
          <NavLink to="/system/architecture">Architecture</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
