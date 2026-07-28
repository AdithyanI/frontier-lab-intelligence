import { NavLink, Outlet } from 'react-router-dom'

export default function BitLensLayout() {
  return (
    <div className="page bit-lens-page">
      <header className="bit-lens-head">
        <h1 className="page-title">BIT Lens</h1>
        <p className="page-sub">
          The public client context used to translate frontier evidence into
          company-specific investment questions.
        </p>
        <nav className="ruled-nav bit-lens-tabs" aria-label="BIT Lens views">
          <NavLink to="/bit-lens/companies">Company universe</NavLink>
          <NavLink to="/bit-lens/research">Research brief</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
