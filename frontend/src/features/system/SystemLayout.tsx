import { NavLink, Outlet } from 'react-router-dom'

export default function System() {
  return (
    <div className="page system-page">
      <header className="system-head">
        <h1 className="page-title">System</h1>
        <p className="page-sub">
          Inspect how evidence becomes audience-specific intelligence, then
          check the current published checkpoint.
        </p>
        <nav className="ruled-nav system-tabs" aria-label="System views">
          <NavLink to="/system/architecture">Architecture</NavLink>
          <NavLink to="/system/status">Status</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
