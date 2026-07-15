import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const addProfile = readFileSync(
  new URL('../src/pages/AddProfile.tsx', import.meta.url),
  'utf8',
)
const api = readFileSync(new URL('../src/api.ts', import.meta.url), 'utf8')
const css = readFileSync(new URL('../src/app.css', import.meta.url), 'utf8')

test('Add Profile exposes both audited X profile admission paths', () => {
  assert.match(addProfile, /Add Profile/)
  assert.match(addProfile, /Screen normally/)
  assert.match(addProfile, /Add directly/)
  assert.match(addProfile, /Why override the normal screen\?/)
  assert.match(addProfile, /Protected profiles remain ineligible/)
  assert.doesNotMatch(addProfile, /Operator token|type="password"/)
})

test('intake posts structured JSON without embedding feature authentication', () => {
  assert.match(api, /export async function postJSON/)
  assert.match(api, /'Content-Type': 'application\/json'/)
  assert.doesNotMatch(api, /Authorization:|Bearer/)
})

test('intake uses the Registry editorial control vocabulary', () => {
  assert.match(css, /\.registry-intake \{/)
  assert.match(css, /\.registry-intake-modes label\.is-selected/)
  assert.match(css, /border-top: 1px solid var\(--border-strong\)/)
})
