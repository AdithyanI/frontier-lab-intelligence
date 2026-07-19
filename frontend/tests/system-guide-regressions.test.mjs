import assert from 'node:assert/strict'
import test from 'node:test'
import { readSource, readStyles } from './source-files.mjs'

const guide = readSource('features/system/HowItWorksPage.tsx')
const styles = readStyles()

test('How it works follows the assignment from cohort to published brief', () => {
  assert.match(guide, /From public output to a decision-ready brief/)
  const stages = [
    'Choose who is worth watching',
    'Build one complete evidence day',
    'Rank attention without calling it truth',
    'Ask two different questions of the same evidence',
    'Publish only what clears the audience bar',
  ]
  for (const stage of stages) assert.match(guide, new RegExp(stage))
  for (let index = 1; index < stages.length; index += 1) {
    assert.ok(guide.indexOf(stages[index - 1]) < guide.indexOf(stages[index]))
  }
})

test('How it works sends reviewers into every proof surface', () => {
  assert.match(guide, /to="\/network\/ranking"/)
  assert.match(guide, /to="\/network\/registry"/)
  assert.match(guide, /to=\{feedPath\}/)
  assert.match(guide, /to=\{artifactsPath\}/)
  assert.match(guide, /to=\{insightsPath\}/)
  assert.match(guide, /to="\/system\/architecture#ranking-methods"/)
  assert.match(guide, /to="\/system\/status"/)
})

test('How it works states the shipped source and automation boundary honestly', () => {
  assert.match(guide, /The current scheduled source is X/)
  assert.match(guide, /linked first-party documents/)
  assert.match(guide, /Unattended scheduling/)
  assert.match(guide, /Source-native recurring collectors for GitHub, arXiv, blogs, and conference video/)
  assert.doesNotMatch(guide, /fully automated alerts|scheduled multi-source ingestion/)
})

test('How it works uses one flat ordered narrative rather than a card dashboard', () => {
  assert.match(guide, /<ol className="how-journey">/)
  assert.match(guide, /<ol className="audit-path">/)
  assert.match(styles, /\.how-step \{[\s\S]*?display: grid;[\s\S]*?border-bottom: 1px solid var\(--border-strong\);/)
  assert.doesNotMatch(styles, /\.how-(?:card|metric)/)
  assert.doesNotMatch(guide, /—/)
})
