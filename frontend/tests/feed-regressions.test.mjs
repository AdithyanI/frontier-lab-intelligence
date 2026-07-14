import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

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
