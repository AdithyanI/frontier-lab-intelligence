import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { decodeTextEntities } from '../src/shared/textEntities.ts'
import { readStyles } from './source-files.mjs'

const insightSource = await readFile(
  new URL('../src/features/insights/InsightsPage.tsx', import.meta.url),
  'utf8',
)
const apiSource = await readFile(new URL('../src/shared/api/insights.ts', import.meta.url), 'utf8')
const appStyles = readStyles()

test('Insights defaults to Investment and keeps audience, date, and decision status in the URL', () => {
  assert.match(apiSource, /export type InsightAudience = 'investment' \| 'ai_engineering'/)
  assert.match(apiSource, /export type InsightStatus = 'kept' \| 'suppressed' \| 'all'/)
  assert.match(insightSource, /const DEFAULT_AUDIENCE: InsightAudience = 'investment'/)
  assert.match(insightSource, /const DEFAULT_STATUS: InsightStatus = 'kept'/)
  assert.match(insightSource, /searchParams\.get\('audience'\)/)
  assert.match(insightSource, /searchParams\.get\('date'\)/)
  assert.match(insightSource, /searchParams\.get\('status'\)/)
  assert.match(insightSource, /nextParams\.set\('status', nextStatus\)/)
  assert.match(insightSource, /aria-label="Insight audience"/)
})

test('Insights presents Investment thesis before AI engineering', () => {
  assert.match(
    insightSource,
    /const AUDIENCE_ORDER: InsightAudience\[\] = \['investment', 'ai_engineering'\]/,
  )
})

test('Insights uses the durable successor API and guards status-specific responses', () => {
  assert.match(insightSource, /`\/api\/insights\/dates\?audience=\$\{audience\}`/)
  assert.match(
    insightSource,
    /`\/api\/insights\?audience=\$\{audience\}&date=\$\{selectedDate\}&status=\$\{status\}`/,
  )
  assert.match(insightSource, /dataView\.payload\.status === status/)
  assert.match(insightSource, /activeDatesViewRef\.current !== viewKey/)
  assert.match(insightSource, /activeDataViewRef\.current !== viewKey/)
  assert.match(insightSource, /loading=\{datesLoading\}/)
})

test('Insights reuses the Feed week strip and gives it kept counts', () => {
  assert.match(insightSource, /<DateNavigator/)
  assert.match(insightSource, /Day pills count kept Insights/)
  assert.match(insightSource, /itemLabel=\{copy\.itemLabel\}/)
  assert.match(appStyles, /\.insight-calendar \.feed-day:only-child \{ grid-column: 7; \}/)
})

test('Insights exposes kept, suppressed, and all decisions in a Feed-style status menu', () => {
  assert.match(insightSource, /const STATUS_ORDER: InsightStatus\[\] = \['kept', 'suppressed', 'all'\]/)
  assert.match(insightSource, /<span className="feed-menu-label mono">STATUS<\/span>/)
  assert.match(insightSource, /role="menuitemradio"/)
  assert.match(insightSource, /counts=\{run\?\.counts\}/)
  assert.match(appStyles, /\.insight-tools \.feed-menu > summary \{ min-width: 190px; \}/)
})

test('Insights inherits Feed rank and links every decision to its exact envelope', () => {
  assert.match(insightSource, /<strong>#\{item\.feed_rank\}<\/strong>/)
  assert.match(insightSource, /<span>Feed rank ↗<\/span>/)
  assert.doesNotMatch(insightSource, /Editorial rank/)
  assert.match(insightSource, /const envelopeUrl = `\/evidence\/feed\?date=\$\{item\.day\}&event=\$\{encodeURIComponent\(item\.event_id\)\}`/)
  assert.match(insightSource, /<CopyEnvelopeId envelopeId=\{item\.event_id\} \/>/)
  assert.match(insightSource, /Open envelope ↗/)
  assert.match(insightSource, /Open source ↗/)
  assert.match(insightSource, /Read artifact ↗/)
  assert.match(appStyles, /\.insight-rank strong \{[\s\S]*?font-size: 30px;/)
})

test('Insights shows an explicit rationale for both decisions without reviving quotes', () => {
  assert.match(insightSource, /item\.decision_reason/)
  assert.match(insightSource, /'Why it matters' : 'Why suppressed'/)
  assert.match(insightSource, /const title = item\.title/)
  assert.doesNotMatch(insightSource, /Suppressed at the final editorial gate/)
  assert.match(insightSource, /<h3 className="mono">Summary<\/h3>/)
  assert.match(insightSource, /decodeTextEntities\(item\.summary\)/)
  assert.match(insightSource, /item\.action_label/)
  assert.match(insightSource, /decodeTextEntities\(item\.action\)/)
  assert.doesNotMatch(insightSource, /item\.next_step/)
  assert.doesNotMatch(insightSource, /Exact source passage/)
  assert.doesNotMatch(insightSource, /citation\.quote/)
  assert.doesNotMatch(insightSource, /dangerouslySetInnerHTML/)
  assert.match(appStyles, /\.insight-decision-reason--suppressed/)
})

test('Insights safely decodes model prose without interpreting markup', () => {
  assert.equal(
    decodeTextEntities('A &amp; B: old -&gt; new &#x2192; done'),
    'A & B: old -> new → done',
  )
  assert.equal(decodeTextEntities('&lt;script&gt;alert(1)&lt;/script&gt;'), '<script>alert(1)</script>')
  assert.equal(decodeTextEntities('Microsoft\u0092s model'), 'Microsoft’s model')
  assert.equal(decodeTextEntities('&unknown; stays'), '&unknown; stays')
  assert.equal(decodeTextEntities('invalid &#xD800; value'), 'invalid &#xD800; value')
})

test('Insights keeps honest loading, error, and thin-filter states', () => {
  assert.match(insightSource, /Insight dates are unavailable/)
  assert.match(insightSource, /This brief did not load/)
  assert.match(insightSource, /No useful investment insight was kept today/)
  assert.match(insightSource, /No useful engineering insight was kept today/)
  assert.match(insightSource, /No completed decision matches this status/)
  assert.match(insightSource, /aria-busy="true"/)
})

test('Insights retries failed date and brief requests without reloading the page', () => {
  assert.match(insightSource, /const \[datesRetryKey, setDatesRetryKey\] = useState\(0\)/)
  assert.match(insightSource, /const \[dataRetryKey, setDataRetryKey\] = useState\(0\)/)
  assert.match(insightSource, /setDatesRetryKey\(\(value\) => value \+ 1\)/)
  assert.match(insightSource, /setDataRetryKey\(\(value\) => value \+ 1\)/)
  assert.match(insightSource, />\s*Try again\s*<\/button>/)
  assert.doesNotMatch(insightSource, /window\.location\.reload/)
  assert.match(appStyles, /\.insight-state-action \{[\s\S]*?min-height: 36px;/)
})
