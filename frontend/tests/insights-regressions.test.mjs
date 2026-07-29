import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { decodeTextEntities } from '../src/shared/textEntities.ts'
import { readStyles } from './source-files.mjs'

const insightSource = await readFile(
  new URL('../src/features/insights/InsightsPage.tsx', import.meta.url),
  'utf8',
)
const appSource = await readFile(new URL('../src/app/App.tsx', import.meta.url), 'utf8')
const apiSource = await readFile(new URL('../src/shared/api/insights.ts', import.meta.url), 'utf8')
const appStyles = readStyles()

test('Insights leads the Evidence, Network, and How it works navigation sequence', () => {
  assert.ok(appSource.indexOf('>Insights</NavLink>') < appSource.indexOf('>Evidence</NavLink>'))
  assert.ok(appSource.indexOf('>Evidence</NavLink>') < appSource.indexOf('>Network</NavLink>'))
  assert.ok(appSource.indexOf('>Network</NavLink>') < appSource.indexOf('>How it works</NavLink>'))
  assert.match(appSource, /<Route path="\/" element=\{<Navigate to="\/insights" replace \/>\} \/>/)
  assert.match(appSource, /<Route path="\*" element=\{<Navigate to="\/insights" replace \/>\} \/>/)
})

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
  assert.match(apiSource, /content_kind: 'investment_agent'/)
  assert.match(insightSource, /payload\.content_kind === 'investment_agent'/)
  assert.doesNotMatch(apiSource, /daily_editorial|candidate_decisions/)
  assert.doesNotMatch(insightSource, /editorialData|candidateData/)
})

test('Investment Insights expose a minimal company judgment and memo audit', () => {
  assert.match(apiSource, /export interface InvestmentAgentCompany/)
  assert.match(apiSource, /export interface InvestmentAgentConnection/)
  assert.match(apiSource, /headline: string/)
  assert.match(apiSource, /what_changed: string/)
  assert.match(apiSource, /connections: InvestmentAgentConnection\[\]/)
  assert.match(apiSource, /companies: InvestmentAgentCompany\[\]/)
  assert.match(apiSource, /bet_id: string/)
  assert.match(apiSource, /threshold_met: boolean/)
  assert.match(apiSource, /impact: string/)
  assert.doesNotMatch(apiSource, /InvestmentAgentHorizon/)
  assert.doesNotMatch(apiSource, /InvestmentAgentConfidence/)
  assert.doesNotMatch(apiSource, /InvestmentAgentEvidence/)
  assert.doesNotMatch(apiSource, /rejected_after_memo:/)
  assert.match(apiSource, /why_memo_is_needed: string/)
  assert.match(insightSource, /function InvestmentAgentInsight/)
  assert.match(insightSource, /decodeTextEntities\(item\.headline\)/)
  assert.match(
    insightSource,
    /<nav className="investment-agent-sources-body" aria-label="Evidence links">[\s\S]*?<CopyEventId eventId=\{item\.development_id\} label="Copy ID" \/>/,
  )
  assert.doesNotMatch(
    insightSource,
    /<header className="insight-head investment-agent-head">(?:(?!<\/header>)[\s\S])*?<CopyEventId eventId=\{item\.development_id\} label="Copy ID" \/>/,
  )
  assert.doesNotMatch(insightSource, /item\.source\?\.title \|\|/)
  assert.match(insightSource, /How this reaches companies/)
  assert.match(insightSource, /function InvestmentAgentConnectionView/)
  assert.match(insightSource, /COMPANY_BET_DIRECTION_COPY/)
  assert.match(insightSource, /bet\?\.title/)
  assert.match(insightSource, /bet=\$\{encodeURIComponent\(company\.bet_id\)\}/)
  assert.match(insightSource, /company\.threshold_met \? 'Review thesis' : 'Early signal'/)
  assert.match(insightSource, /Number\(right\.threshold_met\) - Number\(left\.threshold_met\)/)
  assert.match(insightSource, /View Development in Feed ↗/)
  assert.doesNotMatch(insightSource, /item\.prior_assumption/)
  assert.doesNotMatch(insightSource, /The belief this moves/)
  assert.doesNotMatch(insightSource, /Source material reviewed/)
  assert.doesNotMatch(insightSource, /No attributable public thesis/)
  assert.doesNotMatch(insightSource, /Inspect evidence and open questions/)
  assert.match(insightSource, /How the agent got here/)
  assert.match(insightSource, /Why its memo was opened/)
  assert.doesNotMatch(insightSource, /Opened, then rejected/)
  assert.doesNotMatch(insightSource, /company-aware Investment pass/)
  assert.doesNotMatch(insightSource, /source Events/)
  assert.doesNotMatch(insightSource, /tokens reused/)
  assert.doesNotMatch(insightSource, /Run cost/)
  assert.doesNotMatch(insightSource, /Each company was screened against/)
  assert.match(appStyles, /\.investment-agent-mechanism \{/)
  assert.match(appStyles, /\.investment-agent-exposures > li \{/)
  assert.match(appStyles, /\.investment-agent-bet-direction\[data-direction='upside'\]/)
  assert.match(appStyles, /\.investment-agent-bet-link \{/)
  assert.match(appStyles, /\.investment-agent-process \{/)
  assert.doesNotMatch(appStyles, /investment-agent-company/)
  assert.doesNotMatch(appStyles, /\.investment-agent-mechanism \{[^}]*border-radius:/)
  assert.doesNotMatch(appStyles, /\.investment-agent-mechanism \{[^}]*box-shadow:/)
})

test('A directly linked brief loads in parallel with the date index', () => {
  assert.match(insightSource, /currentDates !== null/)
  assert.doesNotMatch(insightSource, /!currentDates\?\.available/)
  assert.match(
    insightSource,
    /`\/api\/insights\?audience=\$\{audience\}&date=\$\{selectedDate\}&status=\$\{status\}`/,
  )
})

test('Insights reuses the Feed week strip without explanatory reader clutter', () => {
  assert.match(insightSource, /<DateNavigator/)
  assert.match(insightSource, /itemLabel=\{copy\.itemLabel\}/)
  assert.doesNotMatch(insightSource, /Day pills count/)
  assert.doesNotMatch(insightSource, /className="insight-tools"/)
  assert.match(appStyles, /\.insight-calendar \.feed-day:only-child \{ grid-column: 7; \}/)
})

test('Insights keeps status in the audit URL and exposes a compact suppression review switch', () => {
  assert.match(insightSource, /const status = parseStatus\(searchParams\.get\('status'\)\)/)
  assert.match(insightSource, /nextParams\.set\('status', nextStatus\)/)
  assert.match(insightSource, /className="insight-status-switch"/)
  assert.match(insightSource, />Brief<\/span>/)
  assert.match(insightSource, />Suppressed<\/span>/)
  assert.match(insightSource, /currentRun\.suppressed_development_count/)
  assert.doesNotMatch(insightSource, /InsightStatusMenu/)
  assert.doesNotMatch(insightSource, /role="menuitemradio"/)
})

test('Investment Insights progressively discloses Feed evidence, the original post, and source artifacts', () => {
  assert.match(insightSource, /<details className="investment-agent-sources">/)
  assert.match(insightSource, /<span>Sources<\/span>/)
  assert.match(insightSource, /View Development in Feed ↗/)
  assert.match(insightSource, /Open original post ↗/)
  assert.match(insightSource, /Read source artifact/)
  assert.doesNotMatch(insightSource, /Primary source ↗/)
  assert.doesNotMatch(insightSource, /className="investment-agent-provenance"/)
  assert.match(apiSource, /original_post:/)
  assert.match(apiSource, /artifacts: Array</)
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
  assert.match(insightSource, /available=\{Boolean\(investmentAgentData\?\.available\)\}/)
  assert.match(appStyles, /\.insight-page-head \{[^}]*grid-template-columns: minmax\(0, 1fr\) auto;/)
  assert.match(appStyles, /\.insight-report-button \{[^}]*min-height: 44px;/)
  assert.match(appStyles, /\.insight-report-button:focus-visible/)
  assert.doesNotMatch(appStyles, /\.insight-report-button \{[^}]*box-shadow:/)
})

test('Insights exposes guarded manual Slack and email delivery beside the PDF action', () => {
  assert.match(apiSource, /export type BriefDeliveryChannel = 'slack' \| 'email'/)
  assert.match(apiSource, /pdf_delivery: 'link' \| 'attachment'/)
  assert.match(insightSource, /function DailyBriefDelivery/)
  assert.match(insightSource, /\/api\/insights\/delivery\?audience=/)
  assert.match(insightSource, /fetch\('\/api\/insights\/delivery'/)
  assert.match(insightSource, /All \$\{status\.total_insight_count\} Insights \+ PDF link/)
  assert.match(insightSource, /with each complete interpretation/)
  assert.doesNotMatch(insightSource, /remainingInsightCount/)
  assert.doesNotMatch(insightSource, /Delivery access key/)
  assert.doesNotMatch(insightSource, /fli-delivery-access-key/)
  assert.match(insightSource, /Confirm delivery/)
  assert.match(insightSource, /Send to Slack/)
  assert.match(insightSource, /Send email/)
  assert.doesNotMatch(insightSource, /hooks\.slack\.com/)
  assert.match(appStyles, /\.insight-brief-actions \{[^}]*display: flex;/)
  assert.match(appStyles, /\.insight-delivery-button \{[^}]*min-height: 44px;/)
  assert.match(appStyles, /\.insight-delivery-panel \{[^}]*border: 1px solid var\(--ink\);/)
  assert.doesNotMatch(appStyles, /\.insight-delivery-panel \{[^}]*box-shadow:/)
})

test('Insights keeps honest loading, error, and thin-filter states', () => {
  assert.match(insightSource, /Insight dates are unavailable/)
  assert.match(insightSource, /This brief did not load/)
  assert.match(insightSource, /No useful investment insight was kept today/)
  assert.match(insightSource, /No useful engineering insight was kept today/)
  assert.match(insightSource, /No completed decision matches this status/)
  assert.match(insightSource, /aria-busy="true"/)
})

test('Investment company columns respond to the Insight body, not the viewport', () => {
  assert.match(appStyles, /\.insight-body \{[\s\S]*?container-type: inline-size;/)
  assert.match(appStyles, /@container \(max-width: 760px\) \{[\s\S]*?\.investment-agent-mechanism > summary \{[\s\S]*?grid-template-columns: minmax\(0, 1fr\);/)
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
