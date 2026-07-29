import assert from 'node:assert/strict'
import test from 'node:test'
import { readSource, readStyles } from './source-files.mjs'

const app = readSource('app/App.tsx')
const howPage = readSource('features/system/HowItWorksPage.tsx')
const howNarrative = readSource('features/system/HowNarrative.tsx')
const howContent = readSource('features/system/howContent.ts')
const figures = readSource('features/architecture/ArchitecturePage.tsx')
const styles = readStyles()

test('How it works owns one compact page index and the technical appendix', () => {
  assert.match(howPage, /className="how-contents" aria-label="On this page"/)
  for (const anchor of [
    '#universe',
    '#how-read-title',
    '#how-showcase-title',
    '#how-map-title',
    '#technical-appendix',
  ]) {
    assert.match(howPage, new RegExp(`href="${anchor}"`))
  }
  assert.match(howPage, /className="how-technical-appendix" id="technical-appendix"/)
  assert.match(howPage, /<SystemOverview \/>/)
  assert.match(howPage, /<ModelTable \/>/)
  assert.match(howPage, /<AccountIntake \/>/)
  assert.match(howPage, /target instanceof HTMLDetailsElement/)
  assert.match(styles, /\.how-contents \{/)
  assert.match(styles, /\.how-technical-appendix \{/)
})

test('The retired System and Status surfaces have no public route or link', () => {
  assert.doesNotMatch(app, />System<\/NavLink>/)
  assert.doesNotMatch(app, /path="\/system"/)
  assert.doesNotMatch(app, /StatusPage|SystemLayout|ArchitecturePage/)
  assert.doesNotMatch(howContent, /\/system/)
  assert.doesNotMatch(howNarrative, /\/system/)
})

test('The appendix keeps only the three selected, current figures', () => {
  assert.match(figures, /export function SystemOverview/)
  assert.match(figures, /export function ModelTable/)
  assert.match(figures, /export function AccountIntake/)
  assert.match(figures, /LiteLLM \+ OpenAI Responses/)
  assert.match(figures, /routing · Investment · Engineering/)
  assert.match(figures, /task: 'Audience routing'[\s\S]*?model: 'gpt-5\.6-luna'[\s\S]*?effort: 'medium'/)
  assert.match(figures, /task: 'Investment agent'[\s\S]*?model: 'gpt-5\.6-terra'[\s\S]*?effort: 'xhigh'/)
  assert.match(figures, /task: 'AI Engineering agent'[\s\S]*?model: 'gpt-5\.6-terra'[\s\S]*?effort: 'high'/)
  assert.match(figures, /WHEN AN X ACCOUNT IS SUPPLIED/)
  assert.match(figures, /Profile gate/)
  assert.match(figures, /Resolve identity/)
})

test('The written model explanation agrees with the appendix', () => {
  assert.match(howNarrative, /gpt-5\.6-luna<\/code> at medium effort/)
  assert.match(howNarrative, /gpt-5\.6-terra<\/code> at xhigh effort/)
  assert.match(howNarrative, /same\s+model at high effort/)
  assert.doesNotMatch(howNarrative, /gpt-5\.4-mini/)
  assert.doesNotMatch(howNarrative, /only 2 model steps/)
})
