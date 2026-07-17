import { Navigate, NavLink, Route, Routes } from 'react-router-dom'
import Architecture from '../features/architecture/ArchitecturePage'
import Artifacts from '../features/evidence/ArtifactsPage'
import Evidence from '../features/evidence/EvidenceLayout'
import Feed from '../features/evidence/FeedPage'
import Insights from '../features/insights/InsightsPage'
import AddProfile from '../features/network/AddProfilePage'
import Network from '../features/network/NetworkLayout'
import Ranking from '../features/network/RankingPage'
import Registry from '../features/network/RegistryPage'
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
          <NavLink to="/network">Network</NavLink>
          <NavLink to={evidencePath}>Evidence</NavLink>
          <NavLink to={insightsPath}>Insights</NavLink>
          <NavLink to="/architecture">Architecture</NavLink>
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/network/registry" replace />} />
          <Route path="/network" element={<Network />}>
            <Route index element={<Navigate to="registry" replace />} />
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
          <Route path="/architecture" element={<Architecture />} />
          <Route path="*" element={<Navigate to="/network/registry" replace />} />
        </Routes>
      </main>
    </div>
  )
}
