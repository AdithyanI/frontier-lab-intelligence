import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { getDateWindow, shiftDateWindow } from '../src/dateWindow.ts'
import { initialFeedRoutingFilter } from '../src/feedState.ts'

const feedSource = await readFile(new URL('../src/pages/Feed.tsx', import.meta.url), 'utf8')
const dateNavigatorSource = await readFile(
  new URL('../src/components/DateNavigator.tsx', import.meta.url),
  'utf8',
)
const copyEnvelopeSource = await readFile(
  new URL('../src/components/CopyEnvelopeId.tsx', import.meta.url),
  'utf8',
)
const appStyles = await readFile(new URL('../src/app.css', import.meta.url), 'utf8')

test('Feed uses semantic classes for optional menu and routing content', () => {
  assert.match(feedSource, /className="feed-menu-option-count mono"/)
  assert.match(feedSource, /className="event-routing-status"/)
  assert.doesNotMatch(appStyles, /feed-menu-panel button > span:last-child/)
  assert.doesNotMatch(appStyles, /event-routing-heading span:first-child/)
})

test('Feed keeps routing secondary and exposes the exact envelope ID', () => {
  assert.ok(feedSource.indexOf('<EventEvidenceDetails') < feedSource.indexOf('<RoutingNote item={item} />'))
  assert.match(feedSource, /<CopyEnvelopeId envelopeId=\{item\.event_id\} \/>/)
  assert.match(copyEnvelopeSource, /navigator\.clipboard\.writeText\(envelopeId\)/)
  assert.match(copyEnvelopeSource, /Copy envelope ID/)
  assert.match(copyEnvelopeSource, /aria-live="polite"/)
})

test('Feed shows audience marks and keeps both routing reasons auditable', () => {
  assert.match(feedSource, /routing\.ai_engineering\.relevant/)
  assert.match(feedSource, /className="event-audience-mark" aria-hidden="true">ENG</)
  assert.match(feedSource, /routing\.investment\.relevant/)
  assert.match(feedSource, /className="event-audience-mark" aria-hidden="true">INV</)
  assert.match(feedSource, /Relevant to Engineering/)
  assert.match(feedSource, /Relevant to Investment/)
  assert.match(feedSource, /Engineering · \{routing\.ai_engineering\.relevant \? 'Relevant' : 'Not relevant'\}/)
  assert.match(feedSource, /Investment · \{routing\.investment\.relevant \? 'Relevant' : 'Not relevant'\}/)
  assert.doesNotMatch(feedSource, /Feed triage|Kept for extraction|Dropped before extraction/)
  assert.match(appStyles, /\.event-audience-mark \{[\s\S]*?border: 1px solid var\(--border\);/)
})

test('Feed exposes one mutually exclusive routing Status control', () => {
  assert.match(feedSource, /label="STATUS"/)
  assert.match(feedSource, /value: 'all', label: 'All'/)
  assert.match(feedSource, /value: 'relevant'/)
  assert.match(feedSource, /value: 'not_relevant'/)
  assert.match(feedSource, /value: 'not_evaluated'/)
  assert.match(feedSource, /routing: request\.routingFilter/)
  assert.doesNotMatch(feedSource, /label="AUDIT"|label="AUDIENCE"/)
  assert.doesNotMatch(feedSource, /value: 'engineering'|value: 'investment'|value: 'both'/)
  assert.doesNotMatch(feedSource, /triageFilter|triage_counts|auditFilter|audienceFilter/)
})

test('Feed exact-envelope links reveal the target outside the default Relevant filter', () => {
  assert.equal(initialFeedRoutingFilter(new URLSearchParams()), 'relevant')
  assert.equal(
    initialFeedRoutingFilter(new URLSearchParams('event=exact-envelope-id')),
    'all',
  )
  assert.match(feedSource, /initialFeedRoutingFilter\(initialSearchParams\.current\)/)
  assert.match(feedSource, /This exact Feed envelope is not available/)
})

test('Feed search matches the compact ruled control language', () => {
  assert.match(appStyles, /grid-template-columns: minmax\(320px, 400px\) 1fr/)
  assert.match(appStyles, /\.feed-controls \{[\s\S]*?justify-self: end;[\s\S]*?gap: 8px;/)
  assert.match(appStyles, /@media \(max-width: 760px\)/)
  assert.match(appStyles, /\.feed-search \{[\s\S]*?min-height: 44px;[\s\S]*?border: 1px solid var\(--border-strong\);[\s\S]*?border-radius: 0;/)
})

test('Feed preserves daily rank across search and discloses score on demand', () => {
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

test('Feed prioritizes the visible page before background work', () => {
  assert.match(feedSource, /const PAGE_SIZE = 20/)
  assert.match(feedSource, /getCachedJSON<FeedDates>\('\/api\/events\/dates'\)/)
  assert.match(feedSource, /loading \|\|[\s\S]*?for \(const value of visibleDates\)/)
  assert.match(feedSource, /}, 1200\)/)
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

test('Feed keeps date navigation stable while loading and compact at narrower desktops', () => {
  assert.match(feedSource, /loading=\{dates === null\}/)
  assert.match(dateNavigatorSource, /loading\?: boolean/)
  assert.match(dateNavigatorSource, /Array\.from\(\{ length: 7 \}/)
  assert.match(dateNavigatorSource, /className="feed-day-placeholder"/)
  assert.match(dateNavigatorSource, /itemLabel = 'posts'/)
  assert.match(
    dateNavigatorSource,
    /aria-label=\{`\$\{fullDateLabel\}, \$\{itemCountLabel\} \$\{itemLabel\}`\}/,
  )
  assert.match(appStyles, /@media \(max-width: 1100px\)/)
  assert.match(appStyles, /\.feed-day-label-long \{ display: none; \}/)
  assert.match(appStyles, /\.feed-day-label-compact \{ display: inline; \}/)
})
