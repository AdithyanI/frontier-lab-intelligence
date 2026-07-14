import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { getDateWindow, shiftDateWindow } from '../src/dateWindow.ts'

const feedSource = await readFile(new URL('../src/pages/Feed.tsx', import.meta.url), 'utf8')
const dateNavigatorSource = await readFile(
  new URL('../src/components/DateNavigator.tsx', import.meta.url),
  'utf8',
)
const appStyles = await readFile(new URL('../src/app.css', import.meta.url), 'utf8')

test('Feed uses semantic classes for optional menu and triage content', () => {
  assert.match(feedSource, /className="feed-menu-option-count mono"/)
  assert.match(feedSource, /className="event-triage-decision"/)
  assert.doesNotMatch(appStyles, /feed-menu-panel button > span:last-child/)
  assert.doesNotMatch(appStyles, /event-triage-heading span:first-child/)
})

test('Feed search matches the compact ruled control language', () => {
  assert.match(appStyles, /grid-template-columns: minmax\(320px, 400px\) 1fr/)
  assert.match(appStyles, /\.feed-controls \{[\s\S]*?justify-self: end;[\s\S]*?gap: 8px;/)
  assert.match(appStyles, /@media \(max-width: 760px\)/)
  assert.match(appStyles, /\.feed-search \{[\s\S]*?min-height: 44px;[\s\S]*?border: 1px solid var\(--border-strong\);[\s\S]*?border-radius: 0;/)
})

test('Feed preserves daily rank across audit filters and discloses score on demand', () => {
  assert.match(feedSource, /<strong>#\{rank\}<\/strong>/)
  assert.match(feedSource, /rank=\{item\.daily_rank\}/)
  assert.match(feedSource, /Daily rank #\{rank\} of \{total\.toLocaleString/)
  assert.doesNotMatch(feedSource, /rank=\{index \+ 1\}/)
  assert.match(feedSource, /Daily score \{basis\.attention_score\.toFixed\(1\)\}/)
  assert.match(feedSource, /aria-expanded=\{open\}/)
  assert.match(feedSource, /Higher than \{\(row\.percentile \* 100\)\.toFixed\(1\)\}%/)
  assert.match(feedSource, /Scores from different\s+days are not directly comparable/)
  assert.doesNotMatch(feedSource, /<span>attention<\/span>/)
})

test('Feed exposes the selected date and guards paginated responses by view identity', () => {
  assert.match(dateNavigatorSource, /aria-pressed=\{value\.day === selectedDate\}/)
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
  assert.match(feedSource, /dates=\{visibleDates\}/)
  assert.match(dateNavigatorSource, /dates\.map/)
  assert.match(dateNavigatorSource, /disabled=\{!canShowOlderDates\}/)
  assert.match(dateNavigatorSource, /disabled=\{!canShowNewerDates\}/)
  assert.match(dateNavigatorSource, /aria-label="Show previous 7 available days"/)
  assert.match(dateNavigatorSource, /aria-label="Show next 7 available days"/)
  assert.match(feedSource, /for \(const value of visibleDates\)/)
  assert.doesNotMatch(appStyles, /\.feed-days button span:last-child/)
})
