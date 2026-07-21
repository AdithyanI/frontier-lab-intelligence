import assert from 'node:assert/strict'
import test from 'node:test'
import { readSource, readStyles } from './source-files.mjs'

const architecture = readSource('features/architecture/ArchitecturePage.tsx')
const appStyles = readStyles()

test('Architecture chapters share the ruled secondary navigation primitive', () => {
  assert.match(architecture, /className="ruled-nav arch-chapters"/)
  assert.match(architecture, /window\.location\.hash/)
  assert.match(architecture, /scrollIntoView\(\{ block: 'start' \}\)/)
  assert.match(appStyles, /\.ruled-nav \{[\s\S]*?width: 100%;[\s\S]*?border-top: 1px solid var\(--border-strong\);[\s\S]*?border-bottom: 1px solid var\(--border\);/)
  assert.doesNotMatch(appStyles, /\.arch-chapters a\.active/)
})

test('Architecture chapters are separated by one full-width structural rule', () => {
  assert.match(appStyles, /\.arch-section:not\(\.arch-section--lead\) \{[\s\S]*?margin-top: 32px;[\s\S]*?padding-top: 32px;[\s\S]*?border-top: 1px solid var\(--border-strong\);/)
})

test('Architecture starts with one complete day before opening the implementation', () => {
  assert.match(architecture, /One completed day, end to end/)
  assert.match(architecture, /function EvidenceInputMap/)
  assert.match(architecture, /function DailyIntelligenceMap/)
  assert.ok(architecture.indexOf('id="overview"') < architecture.indexOf('id="stack"'))
  assert.ok(architecture.indexOf('id="stack"') < architecture.indexOf('id="models"'))
  assert.ok(architecture.indexOf('href="#overview"') < architecture.indexOf('href="#stack"'))
})

test('Architecture exposes the current deployed stack after the daily path', () => {
  assert.match(architecture, /function SystemOverview/)
  assert.match(architecture, /Public sources/)
  assert.match(architecture, /title: 'Python pipeline'/)
  assert.match(architecture, /title: 'SQLite'/)
  assert.match(architecture, /LiteLLM \+ Codex/)
  assert.match(architecture, /title: 'FastAPI \+ React'/)
  assert.match(architecture, /Cloudflare Tunnel/)
  assert.match(architecture, /public reviewer URL/)
  assert.match(architecture, /Deterministic first\. Every model judgment stays auditable\./)
  assert.match(architecture, /The deployed system underneath it/)
})

test('Architecture maps routed evidence into the persisted daily Codex workflow', () => {
  assert.match(architecture, /function EvidenceInputMap/)
  assert.match(architecture, /function DailyIntelligenceMap/)
  assert.match(architecture, /ONE DATE · ONE CHECKPOINTED DAILY RUN/)
  assert.match(architecture, /title: 'Daily workspace'/)
  assert.match(architecture, /title: 'Persisted Codex task'/)
  assert.match(architecture, /title: 'FLI daily agent'/)
  assert.match(architecture, /title: 'Strict draft gate'/)
  assert.match(architecture, /title: 'Two daily briefs'/)
  assert.match(architecture, /Without --launch-codex, run-day stops/)
  assert.doesNotMatch(architecture, /Citation-bound insight engine|INDEPENDENT AUDIT|SEPARATE VIEW/)
})

test('Architecture exposes the evaluated model choice for each judgment task', () => {
  assert.match(architecture, /function ModelTable/)
  assert.match(architecture, /Entity classification/)
  assert.match(architecture, /Audience routing/)
  assert.match(architecture, /model: 'gpt-5\.6-luna'/)
  assert.match(architecture, /model: 'gpt-5\.4-mini'/)
  assert.match(architecture, /task: 'FLI daily-intelligence agent'/)
  assert.match(architecture, /model: 'gpt-5\.6-sol'/)
  assert.doesNotMatch(architecture, /Per-Event working annotations|Registry relevance audit|gpt-5\.6-terra/)
  assert.doesNotMatch(architecture, /\$0\.01638 per surface-or-suppress decision/)
})

test('Architecture explains fallback and resume behavior without changing frozen inputs', () => {
  assert.match(architecture, /function RecoveryTable/)
  assert.match(architecture, /LiteLLM handles retries, backoff, and provider fallback/)
  assert.match(architecture, /resumes the same persisted Codex task/)
  assert.match(architecture, /No partial brief replaces the last complete product state/)
  assert.ok(architecture.indexOf('id="recovery"') > architecture.indexOf('id="ranking-methods"'))
})

test('Architecture does not publish stale proof counts or describe audience delivery as future', () => {
  assert.doesNotMatch(architecture, /4 verified insights/)
  assert.doesNotMatch(architecture, /Investor \+ engineer delivery/)
  assert.doesNotMatch(architecture, /Delivery is planned next/)
  assert.doesNotMatch(architecture, /GitHub and arXiv are planned|PLANNED/)
  assert.match(architecture, /plane: 'GitHub', role: 'IDENTITY LINK'/)
  assert.match(architecture, /plane: 'Papers', role: 'IDENTITY LINK'/)
})
