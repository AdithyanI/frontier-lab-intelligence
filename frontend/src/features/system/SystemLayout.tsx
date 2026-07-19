import { NavLink, Outlet } from 'react-router-dom'

export default function System() {
  return (
    <div className="page system-page">
      <header className="system-head">
        <h1 className="page-title">System</h1>
        <p className="page-sub">
          The technical detail behind the product: the architecture and the
          live checkpoint. For the story of the pipeline, start with How it
          works.
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
