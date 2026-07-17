import { NavLink, Outlet } from 'react-router-dom'

export default function Network() {
  return (
    <div className="page network-page">
      <header className="network-head">
        <h1 className="page-title">Network</h1>
        <p className="page-sub">
          Ranking shows which accounts the screened source set follows. The
          Registry defines that set. Add Profile admits a source through normal
          screening or a direct audited override.
        </p>
        <nav className="ruled-nav network-tabs" aria-label="Network views">
          <NavLink to="/network/ranking">Ranking</NavLink>
          <NavLink to="/network/registry">Registry</NavLink>
          <NavLink to="/network/add-profile">Add Profile</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
