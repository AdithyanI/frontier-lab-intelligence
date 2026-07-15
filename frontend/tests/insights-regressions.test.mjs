import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { decodeTextEntities } from '../src/textEntities.ts'

const insightSource = await readFile(
  new URL('../src/pages/Insights.tsx', import.meta.url),
  'utf8',
)
const apiSource = await readFile(new URL('../src/api.ts', import.meta.url), 'utf8')
const appStyles = await readFile(new URL('../src/app.css', import.meta.url), 'utf8')

test('Insights keeps Investment and AI engineering as independent URL-backed views', () => {
  assert.match(apiSource, /export type InsightAudience = 'investment' \| 'ai_engineering'/)
  assert.match(insightSource, /const DEFAULT_AUDIENCE: InsightAudience = 'ai_engineering'/)
  assert.match(
    insightSource,
    /const AUDIENCE_ORDER: InsightAudience\[\] = \['ai_engineering', 'investment'\]/,
  )
  assert.match(insightSource, /label: 'Investment thesis'/)
  assert.match(insightSource, /searchParams\.get\('audience'\)/)
  assert.match(insightSource, /searchParams\.get\('date'\)/)
  assert.match(insightSource, /nextParams\.set\('audience', nextAudience\)/)
  assert.match(insightSource, /nextParams\.set\('date', nextDate\)/)
  assert.match(insightSource, /Investment intelligence/)
  assert.match(insightSource, /AI engineering brief/)
  assert.match(insightSource, /aria-label="Insight audience"/)
})

test('Insights fetches and guards audience-specific date and item responses', () => {
  assert.match(insightSource, /'\/api\/insights\/extracted\/dates'/)
  assert.match(insightSource, /'\/api\/insights\/dates'/)
  assert.match(insightSource, /'\/api\/insights\/extracted'/)
  assert.match(insightSource, /'\/api\/insights'/)
  assert.match(insightSource, /type InsightView = 'extracted' \| 'reviewed'/)
  assert.match(insightSource, /nextParams\.set\('view', nextInsightView\)/)
  assert.match(insightSource, /activeDatesViewRef\.current !== viewKey/)
  assert.match(insightSource, /activeDataViewRef\.current !== viewKey/)
  assert.match(insightSource, /dataView\?\.viewKey === selectedViewKey/)
  assert.match(insightSource, /loading=\{datesLoading\}/)
})

test('Insights makes editorial rank primary and Feed rank secondary provenance', () => {
  assert.match(insightSource, /<strong>#\{item\.editorial_rank\}<\/strong>/)
  assert.match(insightSource, /<span>Editorial rank<\/span>/)
  assert.match(insightSource, /className="insight-feed-rank insight-feed-rank--link"/)
  assert.match(appStyles, /\.insight-rank strong \{[\s\S]*?font-size: 30px;/)
  assert.match(appStyles, /\.insight-feed-rank \{[\s\S]*?color: var\(--muted\);/)
})

test('Insights links every Feed rank to its exact dated Feed envelope', () => {
  assert.match(insightSource, /to=\{`\/evidence\/feed\?date=\$\{item\.day\}&event=\$\{encodeURIComponent\(item\.event_id\)\}`\}/)
  assert.match(insightSource, /Open exact Feed envelope/)
  assert.match(insightSource, /Feed rank ↗/)
  assert.match(insightSource, /const envelopeUrl = `\/evidence\/feed\?date=\$\{item\.day\}&event=\$\{encodeURIComponent\(item\.event_id\)\}`/)
  assert.match(insightSource, /Open the exact Feed envelope for/)
  assert.match(insightSource, /<CopyEnvelopeId envelopeId=\{item\.event_id\} \/>/)
  assert.match(appStyles, /\.insight-feed-link:focus-visible/)
})

test('Insights exposes audience decisions and exact citation evidence in plain language', () => {
  assert.match(insightSource, /investment_implication/)
  assert.match(insightSource, /what_to_watch/)
  assert.match(insightSource, /engineering_action/)
  assert.match(insightSource, /validation_boundary/)
  assert.match(insightSource, /ACTION_TYPE_LABELS/)
  assert.match(insightSource, /DECISION_VALUE_LABELS/)
  assert.match(insightSource, /Exact source passage/)
  assert.match(insightSource, /decodeTextEntities\(item\.citation\.quote\)/)
  assert.match(insightSource, /Open envelope ↗/)
  assert.doesNotMatch(insightSource, /dangerouslySetInnerHTML/)
  assert.doesNotMatch(insightSource, /investment_implication.*engineering_implication/s)
})

test('Insights safely decodes source entities for display without interpreting markup', () => {
  assert.equal(
    decodeTextEntities('A &amp; B: old -&gt; new &#x2192; done'),
    'A & B: old -> new → done',
  )
  assert.equal(decodeTextEntities('&lt;script&gt;alert(1)&lt;/script&gt;'), '<script>alert(1)</script>')
  assert.equal(decodeTextEntities('Microsoft\u0092s model'), 'Microsoft’s model')
  assert.equal(decodeTextEntities('&unknown; stays'), '&unknown; stays')
  assert.equal(decodeTextEntities('invalid &#xD800; value'), 'invalid &#xD800; value')
})

test('Insights gives each analysis region and source link an insight-specific name', () => {
  assert.match(
    insightSource,
    /const accessibleName = `editorial rank \$\{item\.editorial_rank\}: \$\{decodeTextEntities\(item\.claim\)\}`/,
  )
  assert.match(insightSource, /aria-label=\{`Investment analysis for \$\{accessibleName\}`\}/)
  assert.match(insightSource, /aria-label=\{`AI engineering analysis for \$\{accessibleName\}`\}/)
  assert.match(insightSource, /aria-label=\{`Open the exact Feed envelope for \$\{accessibleName\}`\}/)
})

test('Insights has honest audience-aware loading, error, and thin-day states', () => {
  assert.match(insightSource, /Insight dates are unavailable/)
  assert.match(insightSource, /This brief did not load/)
  assert.match(insightSource, /No useful investment insight was extracted today/)
  assert.match(insightSource, /No useful engineering insight was extracted today/)
  assert.match(insightSource, /No citation-bound insight is available for this day/)
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
