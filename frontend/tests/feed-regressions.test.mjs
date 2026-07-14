import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { getDateWindow, shiftDateWindow } from '../src/dateWindow.ts'

const feedSource = await readFile(new URL('../src/pages/Feed.tsx', import.meta.url), 'utf8')
const appStyles = await readFile(new URL('../src/app.css', import.meta.url), 'utf8')

test('Feed uses semantic classes for optional menu and triage content', () => {
  assert.match(feedSource, /className="feed-menu-option-count mono"/)
  assert.match(feedSource, /className="event-triage-decision"/)
  assert.doesNotMatch(appStyles, /feed-menu-panel button > span:last-child/)
  assert.doesNotMatch(appStyles, /event-triage-heading span:first-child/)
})

test('Feed exposes the selected date and guards paginated responses by view identity', () => {
  assert.match(feedSource, /aria-pressed=\{value\.day === selectedDate\}/)
  assert.match(feedSource, /activeViewKeyRef\.current !== viewKey/)
  assert.match(feedSource, /activeViewKeyRef\.current === viewKey/)
  assert.match(feedSource, /setData\(null\)/)
  assert.match(feedSource, /setItems\(\[\]\)/)
})

test('Feed pages through fixed seven-date windows with explicit boundary controls', () => {
  assert.deepEqual(getDateWindow(9, 9), { start: 2, end: 9 })
  assert.deepEqual(shiftDateWindow(9, 9, 8, 'older'), {
    start: 0,
    end: 2,
    selectedIndex: 1,
  })
  assert.deepEqual(shiftDateWindow(16, 16, 15, 'older'), {
    start: 2,
    end: 9,
    selectedIndex: 8,
  })
  assert.deepEqual(shiftDateWindow(9, 16, 8, 'newer'), {
    start: 9,
    end: 16,
    selectedIndex: 15,
  })
  assert.match(feedSource, /visibleDates\.map/)
  assert.match(feedSource, /disabled=\{!canShowOlderDates\}/)
  assert.match(feedSource, /disabled=\{!canShowNewerDates\}/)
  assert.match(feedSource, /aria-label="Show previous 7 available days"/)
  assert.match(feedSource, /aria-label="Show next 7 available days"/)
  assert.match(feedSource, /for \(const value of visibleDates\)/)
  assert.doesNotMatch(appStyles, /\.feed-days button span:last-child/)
})
