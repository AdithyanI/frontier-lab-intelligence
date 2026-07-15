import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const architecture = readFileSync(new URL('../src/pages/Architecture.tsx', import.meta.url), 'utf8')
const appStyles = readFileSync(new URL('../src/app.css', import.meta.url), 'utf8')

test('Architecture chapters share the ruled secondary navigation primitive', () => {
  assert.match(architecture, /className="ruled-nav arch-chapters"/)
  assert.match(appStyles, /\.ruled-nav \{[\s\S]*?width: 100%;[\s\S]*?border-top: 1px solid var\(--border-strong\);[\s\S]*?border-bottom: 1px solid var\(--border\);/)
  assert.doesNotMatch(appStyles, /\.arch-chapters a\.active/)
})

test('Architecture ends with the current end-to-end stack', () => {
  assert.match(architecture, /function SystemOverview/)
  assert.match(architecture, /Public sources/)
  assert.match(architecture, /title: 'Python'/)
  assert.match(architecture, /title: 'SQLite'/)
  assert.match(architecture, /LiteLLM → models/)
  assert.match(architecture, /title: 'FastAPI'/)
  assert.match(architecture, /title: 'React'/)
  assert.match(architecture, /Deterministic first\. Model judgment stays auditable\./)
  assert.match(architecture, /System at a glance/)
  assert.ok(architecture.indexOf('id="overview"') > architecture.indexOf('id="ranking-methods"'))
  assert.ok(architecture.indexOf('href="#overview"') > architecture.indexOf('href="#ranking-methods"'))
})

test('Architecture maps one evidence core into two independently audited audience views', () => {
  assert.match(architecture, /function EvidenceInputMap/)
  assert.match(architecture, /function InsightGenerationMap/)
  assert.match(architecture, /FROM ACCEPTED EVIDENCE TO DAILY INSIGHTS/)
  assert.match(architecture, /Citation-bound insight engine/)
  assert.match(architecture, />INVESTMENT</)
  assert.match(architecture, />AI ENGINEERING</)
  assert.equal((architecture.match(/INDEPENDENT AUDIT/g) ?? []).length, 2)
  assert.equal((architecture.match(/SEPARATE VIEW/g) ?? []).length, 2)
  assert.match(architecture, /Audience prompts, judgment, audits, and published views do not/)
})

test('Architecture does not publish stale proof counts or describe audience delivery as future', () => {
  assert.doesNotMatch(architecture, /4 verified insights/)
  assert.doesNotMatch(architecture, /Investor \+ engineer delivery/)
  assert.doesNotMatch(architecture, /Delivery is planned next/)
})
