import assert from 'node:assert/strict'
import test from 'node:test'
import { readSource, readStyles } from './source-files.mjs'

const app = readSource('app/App.tsx')
const layout = readSource('features/system/SystemLayout.tsx')
const howItWorks = readSource('features/system/HowItWorksPage.tsx')
const status = readSource('features/system/StatusPage.tsx')
const styles = readStyles()

test('How it works is a top-level page and System keeps the technical views', () => {
  assert.match(app, /<NavLink to="\/how">How it works<\/NavLink>/)
  assert.match(app, /<Route path="\/how" element=\{<HowItWorks \/>\} \/>/)
  assert.match(app, /<NavLink to="\/system">System<\/NavLink>/)
  assert.match(app, /<Route path="\/system" element=\{<System \/>\}>/)
  assert.match(app, /<Route index element=\{<Navigate to="architecture" replace \/>\} \/>/)
  assert.match(app, /<Route path="how-it-works" element=\{<Navigate to="\/how" replace \/>\} \/>/)
  assert.match(app, /<Route path="status" element=\{<Status \/>\} \/>/)
  assert.match(app, /<Route path="architecture" element=\{<Architecture \/>\} \/>/)
  assert.doesNotMatch(app, /<NavLink to="\/architecture">Architecture<\/NavLink>/)
  assert.match(layout, /<NavLink to="\/system\/architecture">Architecture<\/NavLink>[\s\S]*?<NavLink to="\/system\/status">Status<\/NavLink>/)
  assert.doesNotMatch(layout, /how-it-works/)
})

test('How it works describes the implemented evidence and operator boundaries', () => {
  assert.match(howItWorks, /complete observed X days/)
  assert.match(howItWorks, /successful text snapshots are frozen/)
  assert.match(howItWorks, /retrieval gaps stay visible/)
  assert.match(howItWorks, /A person starts each dated run/)
  assert.match(howItWorks, /published SQLite models produced by the same pipeline/)
  assert.doesNotMatch(howItWorks, /window\.scrollTo/)
  assert.doesNotMatch(howItWorks, /Everything the cohort publishes/)
  assert.doesNotMatch(howItWorks, /every paper, repo, or model card they cite is fetched and frozen/)
  assert.doesNotMatch(howItWorks, /same database as the pipeline/)
})

test('Status derives a checkpoint from existing read APIs without claiming host health', () => {
  assert.match(status, /getJSON<Registry>\('\/api\/registry\?limit=1'\)/)
  assert.match(status, /getJSON<FeedDates>\('\/api\/events\/dates'\)/)
  assert.match(status, /getJSON<ArtifactLibrary>\('\/api\/artifacts\?limit=1'\)/)
  assert.match(status, /\/api\/insights\/dates\?audience=investment/)
  assert.match(status, /\/api\/insights\/dates\?audience=ai_engineering/)
  assert.match(status, /Checkpoint freshness is not a continuous SLA/)
  assert.match(status, /does not infer host, disk, scheduler, or process health/)
  assert.doesNotMatch(status, /Database healthy|All systems operational/)
})

test('Status uses one ruled table and textual states instead of metric cards', () => {
  assert.match(status, /<table className="status-table">/)
  assert.match(status, /<StatusState state=\{row\.state\} label=\{row\.stateLabel\} \/>/)
  assert.match(styles, /\.status-table-wrap \{[\s\S]*?border-top: 1px solid var\(--border-strong\);/)
  assert.match(styles, /\.system-state\.is-available/)
  assert.doesNotMatch(styles, /\.status-card/)
})
