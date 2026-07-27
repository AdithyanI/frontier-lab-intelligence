import { Navigate, NavLink, Route, Routes } from 'react-router-dom'
import Architecture from '../features/architecture/ArchitecturePage'
import BitLensLayout from '../features/bit-lens/BitLensLayout'
import BitLensPage from '../features/bit-lens/BitLensPage'
import CompanyUniversePage from '../features/bit-lens/CompanyUniversePage'
import Artifacts from '../features/evidence/ArtifactsPage'
import Evidence from '../features/evidence/EvidenceLayout'
import Feed from '../features/evidence/FeedPage'
import Insights from '../features/insights/InsightsPage'
import AddProfile from '../features/network/AddProfilePage'
import Network from '../features/network/NetworkLayout'
import Ranking from '../features/network/RankingPage'
import Registry from '../features/network/RegistryPage'
import Status from '../features/system/StatusPage'
import HowItWorks from '../features/system/HowItWorksPage'
import System from '../features/system/SystemLayout'
import { useAuditDatePath } from '../shared/date/auditDateStore'

export default function App() {
  const evidencePath = useAuditDatePath('/evidence/feed')
  const insightsPath = useAuditDatePath('/insights')

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          Frontier Lab Intelligence
        </div>
        <nav aria-label="Main">
          <NavLink to={insightsPath}>Insights</NavLink>
          <NavLink to={evidencePath}>Evidence</NavLink>
          <NavLink to="/network">Network</NavLink>
          <NavLink to="/how">How it works</NavLink>
          <NavLink to="/bit-lens">BIT Lens</NavLink>
          <NavLink to="/system">System</NavLink>
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/insights" replace />} />
          <Route path="/network" element={<Network />}>
            <Route index element={<Navigate to="ranking" replace />} />
            <Route path="registry" element={<Registry />} />
            <Route path="ranking" element={<Ranking />} />
            <Route path="add-profile" element={<AddProfile />} />
          </Route>
          <Route path="/evidence" element={<Evidence />}>
            <Route index element={<Navigate to="feed" replace />} />
            <Route path="feed" element={<Feed />} />
            <Route path="artifacts" element={<Artifacts />} />
          </Route>
          <Route path="/insights" element={<Insights />} />
          <Route path="/how" element={<HowItWorks />} />
          <Route path="/bit-lens" element={<BitLensLayout />}>
            <Route index element={<BitLensPage />} />
            <Route path="companies" element={<CompanyUniversePage />} />
          </Route>
          <Route path="/system" element={<System />}>
            <Route index element={<Navigate to="architecture" replace />} />
            <Route path="how-it-works" element={<Navigate to="/how" replace />} />
            <Route path="status" element={<Status />} />
            <Route path="architecture" element={<Architecture />} />
          </Route>
          <Route path="*" element={<Navigate to="/insights" replace />} />
        </Routes>
      </main>
    </div>
  )
}
