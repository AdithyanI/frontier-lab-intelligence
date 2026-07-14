import { NavLink, Outlet } from 'react-router-dom'

export default function Network() {
  return (
    <div className="page network-page">
      <header className="network-head">
        <h1 className="page-title">Network</h1>
        <p className="page-sub">
          The Registry defines the screened source set. Ranking shows which
          accounts that set follows.
        </p>
        <nav className="network-tabs" aria-label="Network views">
          <NavLink to="/network/ranking">Ranking</NavLink>
          <NavLink to="/network/registry">Registry</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
