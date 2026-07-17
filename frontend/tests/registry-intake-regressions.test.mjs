import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { readStyles } from './source-files.mjs'

const addProfile = readFileSync(
  new URL('../src/features/network/AddProfilePage.tsx', import.meta.url),
  'utf8',
)
const api = readFileSync(new URL('../src/shared/api/client.ts', import.meta.url), 'utf8')
const css = readStyles()

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
