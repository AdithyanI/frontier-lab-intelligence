import assert from 'node:assert/strict'
import test from 'node:test'
import { readSource, readStyles } from './source-files.mjs'

const app = readSource('app/App.tsx')
const layout = readSource('features/system/SystemLayout.tsx')
const status = readSource('features/system/StatusPage.tsx')
const styles = readStyles()

test('System opens with the reviewer walkthrough and keeps technical views together', () => {
  assert.match(app, /<NavLink to="\/system">System<\/NavLink>/)
  assert.match(app, /<Route path="\/system" element=\{<System \/>\}>/)
  assert.match(app, /<Route index element=\{<Navigate to="how-it-works" replace \/>\} \/>/)
  assert.match(app, /<Route path="how-it-works" element=\{<HowItWorks \/>\} \/>/)
  assert.match(app, /<Route path="status" element=\{<Status \/>\} \/>/)
  assert.match(app, /<Route path="architecture" element=\{<Architecture \/>\} \/>/)
  assert.doesNotMatch(app, /<NavLink to="\/architecture">Architecture<\/NavLink>/)
  assert.match(layout, /<NavLink to="\/system\/how-it-works">How it works<\/NavLink>[\s\S]*?<NavLink to="\/system\/architecture">Architecture<\/NavLink>[\s\S]*?<NavLink to="\/system\/status">Status<\/NavLink>/)
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
