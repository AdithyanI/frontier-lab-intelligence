import { NavLink, Outlet } from 'react-router-dom'
import { useAuditDatePath } from '../auditDateStore'

export default function Evidence() {
  const feedPath = useAuditDatePath('/evidence/feed')
  const artifactsPath = useAuditDatePath('/evidence/artifacts')

  return (
    <div className="page evidence-page">
      <header className="evidence-head">
        <h1 className="page-title">Evidence</h1>
        <p className="page-sub">
          Inspect what the tracked network amplified and the primary sources
          those posts revealed.
        </p>
        <nav className="ruled-nav evidence-tabs" aria-label="Evidence views">
          <NavLink to={feedPath}>Feed</NavLink>
          <NavLink to={artifactsPath}>Primary artifacts</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
