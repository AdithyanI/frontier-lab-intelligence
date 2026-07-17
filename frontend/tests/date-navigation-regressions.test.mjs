import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import {
  readAuditDate,
  setAuditDateParam,
  withAuditDate,
} from '../src/shared/date/auditDate.ts'
import { getDateWindowEndForSelection } from '../src/shared/date/dateWindow.ts'

const appSource = await readFile(new URL('../src/app/App.tsx', import.meta.url), 'utf8')
const evidenceSource = await readFile(
  new URL('../src/features/evidence/EvidenceLayout.tsx', import.meta.url),
  'utf8',
)
const feedSource = await readFile(new URL('../src/features/evidence/FeedPage.tsx', import.meta.url), 'utf8')
const artifactSource = await readFile(
  new URL('../src/features/evidence/ArtifactsPage.tsx', import.meta.url),
  'utf8',
)
const insightSource = await readFile(
  new URL('../src/features/insights/InsightsPage.tsx', import.meta.url),
  'utf8',
)

test('audit date paths preserve only the shared date filter', () => {
  assert.equal(withAuditDate('/evidence/feed', '2026-07-13'), '/evidence/feed?date=2026-07-13')
  assert.equal(
    withAuditDate('/insights?audience=investment', '2026-07-13'),
    '/insights?audience=investment&date=2026-07-13',
  )
  assert.equal(withAuditDate('/architecture#ranking', ''), '/architecture#ranking')
  assert.equal(readAuditDate('?date=2026-07-12&event=abc'), '2026-07-12')

  const next = setAuditDateParam(
    new URLSearchParams('date=2026-07-12&event=abc'),
    '2026-07-13',
    ['event'],
  )
  assert.equal(next.toString(), 'date=2026-07-13')
})

test('a restored older date opens the seven-day window that contains it', () => {
  assert.equal(getDateWindowEndForSelection(16, 15), 16)
  assert.equal(getDateWindowEndForSelection(16, 8), 9)
  assert.equal(getDateWindowEndForSelection(16, 1), 2)
  assert.equal(getDateWindowEndForSelection(9, 0), 2)
  assert.equal(getDateWindowEndForSelection(9, -1), 9)
})

test('all date-based views and their navigation use the shared audit date', () => {
  assert.match(appSource, /useAuditDatePath\('\/evidence\/feed'\)/)
  assert.match(appSource, /useAuditDatePath\('\/insights'\)/)
  assert.match(evidenceSource, /useAuditDatePath\('\/evidence\/feed'\)/)
  assert.match(evidenceSource, /useAuditDatePath\('\/evidence\/artifacts'\)/)
  assert.match(feedSource, /readAuditDate\(initialSearchParams\.current\)/)
  assert.match(feedSource, /setAuditDateParam\(urlSearchParams, day, \['event'\]\)/)
  assert.match(feedSource, /const selectedDateIsAvailable = availableDates\.some/)
  assert.match(feedSource, /No complete Feed view is available for \$\{selectedDateLabel\}/)
  assert.match(feedSource, /This audit date remains preserved across views/)
  assert.match(artifactSource, /readAuditDate\(initialSearchParams\.current\)/)
  assert.match(artifactSource, /setAuditDateParam\(urlSearchParams, day\)/)
  assert.match(insightSource, /const nextDate = linkedDate \|\| payload\.latest_date \|\| ''/)
  assert.match(insightSource, /selectedDateUnavailable/)
})
