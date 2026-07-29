import { NavLink, Outlet } from 'react-router-dom'

export default function BitLensLayout() {
  return (
    <div className="page bit-lens-page">
      <header className="bit-lens-head">
        <h1 className="page-title">BIT Lens</h1>
        <p className="page-sub">
          The public client context on both sides: the companies and standing
          bets used for investment questions, and the research platform BIT&rsquo;s
          AI team operates.
        </p>
        <nav className="ruled-nav bit-lens-tabs" aria-label="BIT Lens views">
          <NavLink to="/bit-lens/companies">Company universe</NavLink>
          <NavLink to="/bit-lens/aion">Aion stack</NavLink>
          <NavLink to="/bit-lens/research">Research brief</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
