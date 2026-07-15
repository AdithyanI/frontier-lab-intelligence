import { NavLink, Outlet } from 'react-router-dom'

export default function Evidence() {
  return (
    <div className="page evidence-page">
      <header className="evidence-head">
        <h1 className="page-title">Evidence</h1>
        <p className="page-sub">
          Inspect what the tracked network amplified and the primary sources
          those posts revealed.
        </p>
        <nav className="evidence-tabs" aria-label="Evidence views">
          <NavLink to="/evidence/feed">Feed</NavLink>
          <NavLink to="/evidence/artifacts">Primary artifacts</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
