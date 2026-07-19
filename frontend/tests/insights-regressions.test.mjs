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
  assert.match(apiSource, /content_kind: 'candidate_decisions'/)
  assert.match(apiSource, /content_kind: 'daily_editorial'/)
  assert.match(insightSource, /payload\.content_kind === 'daily_editorial'/)
})

test('Insights reuses the Feed week strip without explanatory reader clutter', () => {
  assert.match(insightSource, /<DateNavigator/)
  assert.match(insightSource, /itemLabel=\{copy\.itemLabel\}/)
  assert.doesNotMatch(insightSource, /Day pills count/)
  assert.doesNotMatch(insightSource, /className="insight-tools"/)
  assert.match(appStyles, /\.insight-calendar \.feed-day:only-child \{ grid-column: 7; \}/)
})

test('Insights keeps status in the audit URL without exposing a reader control strip', () => {
  assert.match(insightSource, /const status = parseStatus\(searchParams\.get\('status'\)\)/)
  assert.match(insightSource, /nextParams\.set\('status', nextStatus\)/)
  assert.doesNotMatch(insightSource, /InsightStatusMenu/)
  assert.doesNotMatch(insightSource, /role="menuitemradio"/)
})

test('Insights inherits Feed rank and links every decision to its exact Event', () => {
  assert.match(insightSource, /<strong>#\{item\.feed_rank\}<\/strong>/)
  assert.match(insightSource, /<span>Feed rank ↗<\/span>/)
  assert.doesNotMatch(insightSource, /Editorial rank/)
  assert.match(insightSource, /const eventUrl = `\/evidence\/feed\?date=\$\{item\.day\}&event_id=\$\{encodeURIComponent\(item\.event_id\)\}`/)
  assert.match(insightSource, /<CopyEventId eventId=\{item\.event_id\} \/>/)
  assert.match(insightSource, /Open Event ↗/)
  assert.match(insightSource, /Open source ↗/)
  assert.match(insightSource, /Read artifact ↗/)
  assert.match(appStyles, /\.insight-rank strong \{[\s\S]*?font-size: 30px;/)
})

test('Insights shows an explicit rationale for legacy decisions without interpreting source markup', () => {
  assert.match(insightSource, /item\.decision_reason/)
  assert.match(insightSource, /'Why it matters' : 'Why suppressed'/)
  assert.match(insightSource, /const title = item\.title/)
  assert.doesNotMatch(insightSource, /Suppressed at the final editorial gate/)
  assert.match(insightSource, /<h3 className="mono">Summary<\/h3>/)
  assert.match(insightSource, /decodeTextEntities\(item\.summary\)/)
  assert.match(insightSource, /item\.action_label/)
  assert.match(insightSource, /decodeTextEntities\(item\.action\)/)
  assert.match(insightSource, /item\.next_step/)
  assert.doesNotMatch(insightSource, /Exact source passage/)
  assert.doesNotMatch(insightSource, /citation\.quote/)
  assert.doesNotMatch(insightSource, /dangerouslySetInnerHTML/)
  assert.match(appStyles, /\.insight-decision-reason--suppressed/)
})

test('Insights renders canonical daily editorial judgments as a ranked, cited brief', () => {
  assert.match(apiSource, /export interface EditorialInsightItem/)
  assert.match(apiSource, /rank_rationale: string/)
  assert.match(apiSource, /what_changed: string/)
  assert.match(apiSource, /interpretation: string/)
  assert.match(apiSource, /scope: InvestmentEntityScope/)
  assert.match(apiSource, /impact: InvestmentImpactDirection/)
  assert.match(apiSource, /mechanism: string/)
  assert.match(apiSource, /key_uncertainty: string/)
  assert.match(apiSource, /export interface EngineeringEditorialAnalysis \{\s*decision_rule: string\s*\}/)
  assert.doesNotMatch(apiSource, /export type EngineeringAction/)
  assert.doesNotMatch(apiSource, /system_surface: string/)
  assert.doesNotMatch(apiSource, /technical_implication: string/)
  assert.doesNotMatch(apiSource, /recommended_action: EngineeringAction/)
  assert.doesNotMatch(apiSource, /root_url: string/)
  assert.match(apiSource, /portfolio_reference: EditorialPortfolioReference \| null/)
  assert.doesNotMatch(apiSource, /impact_chain: string\[\]/)
  assert.doesNotMatch(apiSource, /evidence_limitations: string\[\]/)
  assert.doesNotMatch(insightSource, /className="editorial-insight-date mono"/)
  assert.doesNotMatch(insightSource, />Selected<\/div>/)
  assert.doesNotMatch(insightSource, /run\.agent\.model/)
  assert.doesNotMatch(insightSource, /run\.agent\.skill_version/)
  assert.match(apiSource, /events: EditorialEventLink\[\]/)
  assert.match(apiSource, /citations: EditorialCitation\[\]/)
  assert.match(insightSource, /Brief rank/)
  assert.match(insightSource, /Copy reference/)
  assert.match(insightSource, /ID: \$\{item\.insight_id\}/)
  assert.match(insightSource, /Brief #\$\{item\.rank\}/)
  assert.match(insightSource, /aria-expanded=\{rankExplanationOpen\}/)
  assert.match(insightSource, /decodeTextEntities\(item\.rank_rationale\)/)
  assert.match(insightSource, /decision consequence/)
  assert.match(insightSource, /It is not/)
  assert.match(insightSource, /What changed/)
  assert.match(insightSource, /Investment interpretation/)
  assert.doesNotMatch(insightSource, /Impact chain/)
  assert.match(insightSource, /Company read-through/)
  assert.match(insightSource, /Portfolio companies/)
  assert.match(insightSource, /Outside the disclosed portfolio/)
  assert.match(insightSource, /INVESTMENT_IMPACT_COPY/)
  assert.match(insightSource, /editorial-entity-impact-icon/)
  assert.doesNotMatch(insightSource, /Overall: \{titleCase\(analysis\.thesis_effect\)\}/)
  assert.match(insightSource, /What would confirm or challenge this/)
  assert.match(insightSource, /Key uncertainty/)
  assert.match(insightSource, /What to do next/)
  assert.match(insightSource, /Decision rule/)
  assert.match(insightSource, /analysis\.decision_rule/)
  assert.doesNotMatch(insightSource, /Engineering decision/)
  assert.doesNotMatch(insightSource, /Experiment details/)
  assert.doesNotMatch(insightSource, /Original post ↗/)
  assert.doesNotMatch(insightSource, /Evidence limitations/)
  assert.doesNotMatch(insightSource, /Evidence and full analysis/)
  assert.match(insightSource, /<div className="editorial-source-columns">/)
  assert.match(insightSource, /Original feed/)
  assert.match(insightSource, /Artifacts &amp; context/)
  assert.match(insightSource, /citation\.url !== portfolioSourceUrl/)
  assert.match(insightSource, /portfolioSourceUrl=\{editorialData\.portfolio_reference\?\.source_url\}/)
  assert.doesNotMatch(insightSource, /\{index \+ 1\}\. \{decodeTextEntities\(citation\.title\)\}/)
  assert.doesNotMatch(insightSource, /As of \{entity\.as_of\}/)
  assert.match(insightSource, /Feed #\{event\.feed_rank\} ↗/)
  assert.match(insightSource, /citation\.supports/)
  assert.doesNotMatch(insightSource, /citation\.excerpt/)
  assert.match(appStyles, /\.editorial-insight-row/)
  assert.match(appStyles, /\.editorial-rank button:focus-visible/)
  assert.match(appStyles, /\.editorial-rank-explanation/)
  assert.match(appStyles, /\.editorial-decision \{[^}]*border-top: 0;/)
  assert.match(appStyles, /\.editorial-watch \{[^}]*border-top: 0;/)
  assert.match(appStyles, /\.editorial-source-columns \{[^}]*display: grid;/)
  assert.match(appStyles, /\.editorial-validation-grid \{[^}]*grid-template-columns:/)
  assert.match(appStyles, /\.editorial-entities li \{[^}]*grid-template-columns: minmax\(138px, 0\.22fr\) minmax\(138px, 0\.18fr\) minmax\(0, 1fr\);/)
  assert.doesNotMatch(appStyles, /\.editorial-section-heading/)
  assert.doesNotMatch(appStyles, /\.editorial-thesis-effect/)
  assert.doesNotMatch(appStyles, /\.editorial-citation-links \{[^}]*border-top:/)
  assert.doesNotMatch(appStyles, /\.editorial-insight-row\s*\{[\s\S]*?border-radius:/)
  assert.doesNotMatch(appStyles, /\.editorial-insight-row\s*\{[\s\S]*?box-shadow:/)
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

test('Insights exposes a production PDF download for the complete selected daily brief', () => {
  assert.match(insightSource, /function DailyBriefDownload/)
  assert.match(
    insightSource,
    /`\/api\/insights\/report\.pdf\?audience=\$\{audience\}&date=\$\{encodeURIComponent\(day\)\}`/,
  )
  assert.match(insightSource, /Accept: 'application\/pdf'/)
  assert.match(insightSource, /new AbortController\(\)/)
  assert.match(insightSource, /requestRef\.current\?\.abort\(\)/)
  assert.match(insightSource, /signal: controller\.signal/)
  assert.match(insightSource, /response\.headers\.get\('content-disposition'\)/)
  assert.match(insightSource, /URL\.createObjectURL\(blob\)/)
  assert.match(insightSource, /URL\.revokeObjectURL\(objectUrl\)/)
  assert.match(insightSource, /window\.setTimeout\(\(\) => URL\.revokeObjectURL\(objectUrl\), 0\)/)
  assert.match(insightSource, /anchor\.download = reportFilename\(response, audience, day\)/)
  assert.match(insightSource, /aria-busy=\{state === 'generating'\}/)
  assert.match(insightSource, /Preparing PDF…/)
  assert.match(insightSource, /Download again/)
  assert.match(insightSource, /PDF export is available for complete kept daily briefs\./)
  assert.match(insightSource, /available=\{Boolean\(editorialData\?\.available\)\}/)
  assert.match(appStyles, /\.insight-page-head \{[^}]*grid-template-columns: minmax\(0, 1fr\) auto;/)
  assert.match(appStyles, /\.insight-report-button \{[^}]*min-height: 44px;/)
  assert.match(appStyles, /\.insight-report-button:focus-visible/)
  assert.doesNotMatch(appStyles, /\.insight-report-button \{[^}]*box-shadow:/)
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
