import { NavLink, Outlet } from 'react-router-dom'

export default function System() {
  return (
    <div className="page system-page">
      <header className="system-head">
        <h1 className="page-title">System</h1>
        <p className="page-sub">
          Follow the system from the original brief to the current published
          product, then inspect the technical detail and live checkpoint.
        </p>
        <nav className="ruled-nav system-tabs" aria-label="System views">
          <NavLink to="/system/how-it-works">How it works</NavLink>
          <NavLink to="/system/architecture">Architecture</NavLink>
          <NavLink to="/system/status">Status</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
