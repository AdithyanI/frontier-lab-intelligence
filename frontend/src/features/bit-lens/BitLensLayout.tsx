import { NavLink, Outlet } from 'react-router-dom'

export default function BitLensLayout() {
  return (
    <div className="page bit-lens-page">
      <header className="bit-lens-head">
        <h1 className="page-title">BIT Lens</h1>
        <p className="page-sub">
          Read frontier-lab evidence through the flagship’s dated exposures and
          BIT’s publicly documented research process.
        </p>
        <nav className="ruled-nav bit-lens-tabs" aria-label="BIT Lens views">
          <NavLink to="/bit-lens/flagship">Flagship</NavLink>
          <NavLink to="/bit-lens/research-process">Research Process</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
