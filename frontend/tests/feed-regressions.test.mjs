import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { getDateWindow, shiftDateWindow } from '../src/shared/date/dateWindow.ts'
import { initialFeedRoutingFilter } from '../src/features/evidence/feedState.ts'
import { readStyles } from './source-files.mjs'

const feedSource = await readFile(new URL('../src/features/evidence/FeedPage.tsx', import.meta.url), 'utf8')
const dateNavigatorSource = await readFile(
  new URL('../src/shared/components/DateNavigator.tsx', import.meta.url),
  'utf8',
)
const copyEventSource = await readFile(
  new URL('../src/shared/components/CopyEventId.tsx', import.meta.url),
  'utf8',
)
const evidenceApiSource = await readFile(
  new URL('../src/shared/api/evidence.ts', import.meta.url),
  'utf8',
)
const appStyles = readStyles()

test('Feed uses semantic classes for optional menu and routing content', () => {
  assert.match(feedSource, /className="feed-menu-option-count mono"/)
  assert.match(feedSource, /className="event-routing-status"/)
  assert.doesNotMatch(appStyles, /feed-menu-panel button > span:last-child/)
  assert.doesNotMatch(appStyles, /event-routing-heading span:first-child/)
})

test('Feed keeps routing secondary and exposes stable Development and exact Event IDs', () => {
  assert.ok(feedSource.indexOf('<DevelopmentEvidenceDetails') < feedSource.indexOf('<RoutingNote item={item} />'))
  assert.match(feedSource, /<CopyEventId eventId=\{item\.development_id\} label="Copy ID" \/>/)
  assert.match(feedSource, /<CopyEventId eventId=\{source\.event_id\} \/>/)
  assert.match(copyEventSource, /navigator\.clipboard\.writeText\(eventId\)/)
  assert.match(copyEventSource, /label = 'Copy Event ID'/)
  assert.match(copyEventSource, /\{label\}/)
  assert.match(copyEventSource, /aria-live="polite"/)
})

test('Feed previews the exact semantic packet without starting audience generation', () => {
  assert.match(feedSource, /developmentAnalysisPacketUrl/)
  assert.match(feedSource, /Preview what audience analysis reads/)
  assert.match(feedSource, /Sent for meaning/)
  assert.match(feedSource, /Used for rank only/)
  assert.match(feedSource, /View the exact model input/)
  assert.match(feedSource, /opening this preview does not run audience analysis/)
  assert.match(evidenceApiSource, /\/api\/developments\/analysis-packet/)
})

test('Feed shows audience marks and keeps both routing reasons auditable', () => {
  assert.match(feedSource, /routing\.ai_engineering\.relevant/)
  assert.match(feedSource, /className="event-audience-mark" aria-hidden="true">ENG</)
  assert.match(feedSource, /routing\.investment\.relevant/)
  assert.match(feedSource, /className="event-audience-mark" aria-hidden="true">INV</)
  assert.match(feedSource, /Relevant to AI Engineering/)
  assert.match(feedSource, /Relevant to Investment/)
  assert.match(feedSource, /AI Engineering · \{routing\.ai_engineering\.relevant \? 'Relevant' : 'Not relevant'\}/)
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
  assert.match(evidenceApiSource, /routing: routingFilter/)
  assert.doesNotMatch(feedSource, /label="AUDIT"|label="AUDIENCE"/)
  assert.doesNotMatch(feedSource, /value: 'engineering'|value: 'investment'|value: 'both'/)
  assert.doesNotMatch(feedSource, /triageFilter|triage_counts|auditFilter|audienceFilter/)
})

test('Feed exact-Event links reveal the target outside the default Relevant filter', () => {
  assert.equal(initialFeedRoutingFilter(new URLSearchParams()), 'relevant')
  assert.equal(
    initialFeedRoutingFilter(new URLSearchParams('date=2026-07-28')),
    'relevant',
  )
  assert.equal(
    initialFeedRoutingFilter(new URLSearchParams('event_id=exact-event-id')),
    'all',
  )
  assert.match(feedSource, /initialFeedRoutingFilter\(initialSearchParams\.current\)/)
  assert.match(feedSource, /This source Event is not available/)
  assert.match(feedSource, /Check the date or Event ID/)
})

test('Feed search matches the compact ruled control language', () => {
  assert.match(appStyles, /grid-template-columns: minmax\(320px, 400px\) 1fr/)
  assert.match(appStyles, /\.feed-controls \{[\s\S]*?justify-self: end;[\s\S]*?gap: 8px;/)
  assert.match(appStyles, /@media \(max-width: 760px\)/)
  assert.match(appStyles, /\.feed-search \{[\s\S]*?min-height: 44px;[\s\S]*?border: 1px solid var\(--border-strong\);[\s\S]*?border-radius: 0;/)
})

test('Feed preserves daily rank across search and discloses its layers on demand', () => {
  assert.match(feedSource, /href="\/how#why-rank"/)
  assert.match(feedSource, /<strong>#\{rank\}<\/strong>/)
  assert.match(feedSource, /rank=\{item\.daily_rank\}/)
  assert.match(feedSource, /Daily rank #\{rank\} of \{total\.toLocaleString/)
  assert.doesNotMatch(feedSource, /rank=\{index \+ 1\}/)
  assert.match(feedSource, /components\.trusted_attention/)
  assert.match(feedSource, /components\.mean_participant_position/)
  assert.match(feedSource, /components\.public_interactions/)
  assert.match(feedSource, /mean_participant_position\.toFixed\(6\)/)
  assert.match(feedSource, /trusted people and organizations posted, quoted, or reposted this Development/)
  assert.match(feedSource, /Original posters count/)
  assert.match(feedSource, /rank above \$\{meanParticipantPercent\}% of the Registry/)
  assert.match(feedSource, /Entities with equal support share the same position/)
  assert.match(feedSource, /first difference from the Development beside it/)
  assert.match(feedSource, /The most-engaged post received/)
  assert.match(feedSource, /Compare ranks only within the same day/)
  assert.doesNotMatch(feedSource, /source entity excluded after union/)
  assert.doesNotMatch(feedSource, /Mean entity percentile/)
  assert.doesNotMatch(feedSource, /decided the adjacent tie/)
  assert.doesNotMatch(feedSource, /mean_participant_position\.toFixed\(3\)/)
  assert.match(feedSource, /aria-expanded=\{open\}/)
  assert.doesNotMatch(feedSource, /attention_score|score_components|score_formula/)
})

test('Feed exposes the selected date and guards paginated responses by view identity', () => {
  assert.match(dateNavigatorSource, /aria-pressed=\{value\.day === selectedDate\}/)
  assert.match(feedSource, /activeViewKeyRef\.current !== viewKey/)
  assert.match(feedSource, /activeViewKeyRef\.current === viewKey/)
  assert.match(feedSource, /setData\(null\)/)
  assert.match(feedSource, /setItems\(\[\]\)/)
})

test('Feed prioritizes the linked day and does no competing date prefetch', () => {
  assert.match(feedSource, /const PAGE_SIZE = 20/)
  assert.match(feedSource, /getCachedJSON<FeedDates>\('\/api\/developments\/dates'\)/)
  assert.match(feedSource, /useState\(\s*\(\) => initialLinkedDate\.current,\s*\)/)
  assert.match(evidenceApiSource, /include_evidence: String\(includeEvidence\)/)
  assert.match(feedSource, /developmentPageUrl\(\{ \.\.\.request, limit: PAGE_SIZE \}\)/)
  assert.match(feedSource, /getCachedJSON<DevelopmentResponse>/)
  assert.match(feedSource, /function requestDevelopmentDetail/)
  assert.match(feedSource, /includeEvidence: true/)
  assert.match(feedSource, /const counts = item\.relationship_counts/)
  assert.doesNotMatch(feedSource, /for \(const value of visibleDates\)/)
})

test('Feed exact-Event loading stays focused on the requested row', () => {
  assert.match(feedSource, /targetEventId \? 1 : 5/)
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
  assert.doesNotMatch(feedSource, /for \(const value of visibleDates\)/)
  assert.doesNotMatch(appStyles, /\.feed-days button span:last-child/)
})

test('Feed keeps date navigation stable while loading and compact at narrower desktops', () => {
  assert.match(feedSource, /loading=\{dates === null\}/)
  assert.match(dateNavigatorSource, /loading\?: boolean/)
  assert.match(dateNavigatorSource, /Array\.from\(\{ length: 7 \}/)
  assert.match(dateNavigatorSource, /className="feed-day-placeholder"/)
  assert.match(dateNavigatorSource, /itemLabel = 'items'/)
  assert.match(feedSource, /itemLabel="Developments"/)
  assert.match(
    dateNavigatorSource,
    /aria-label=\{`\$\{fullDateLabel\}, \$\{itemCountLabel\} \$\{itemLabel\}`\}/,
  )
  assert.match(appStyles, /@media \(max-width: 1100px\)/)
  assert.match(appStyles, /\.feed-day-label-long \{ display: none; \}/)
  assert.match(appStyles, /\.feed-day-label-compact \{ display: inline; \}/)
})
