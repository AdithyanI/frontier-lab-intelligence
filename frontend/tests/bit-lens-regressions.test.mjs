import assert from 'node:assert/strict'
import test from 'node:test'
import { readSource, readStyles } from './source-files.mjs'

const app = readSource('app/App.tsx')
const layout = readSource('features/bit-lens/BitLensLayout.tsx')
const lens = readSource('features/bit-lens/BitLensPage.tsx')
const universe = readSource('features/bit-lens/CompanyUniversePage.tsx')
const data = readSource('features/bit-lens/bitLensData.ts')
const styles = readStyles()

test('BIT Lens keeps research and company context in one ruled workspace', () => {
  assert.ok(app.indexOf('>Insights</NavLink>') < app.indexOf('>BIT Lens</NavLink>'))
  assert.ok(app.indexOf('>BIT Lens</NavLink>') < app.indexOf('>System</NavLink>'))
  assert.match(app, /path="\/bit-lens" element=\{<BitLensLayout \/>\}/)
  assert.match(app, /<Route index element=\{<BitLensPage \/>\} \/>/)
  assert.match(app, /<Route path="companies" element=\{<CompanyUniversePage \/>\} \/>/)
  assert.match(layout, /className="ruled-nav bit-lens-tabs"/)
  assert.match(layout, />Research brief<\/NavLink>/)
  assert.match(layout, />Company universe<\/NavLink>/)
  assert.match(lens, /<article className="lens-reading">/)
})

test('BIT Lens preserves the detailed research in one reading order', () => {
  assert.match(lens, /The flagship fund and its mandate/)
  assert.match(lens, /What the dated portfolio disclosures show/)
  assert.match(lens, /How to read the current top ten/)
  assert.match(lens, /How BIT appears to build and test investment theses/)
  assert.match(lens, /Aion, data infrastructure, and the human boundary/)
  assert.match(lens, /What this means for Frontier Lab Intelligence/)
  assert.match(lens, /Contradictions, uncertainties, and missing information/)
  assert.match(lens, /Source ledger/)
})

test('Flagship facts stay dated and current exposure is not overstated', () => {
  assert.match(lens, /Latest public snapshot<\/dt><dd>30 June 2026/)
  assert.match(lens, /Fund assets<\/dt><dd>€1\.594 billion/)
  assert.match(lens, /Top-ten concentration<\/dt><dd>60\.7%/)
  assert.match(lens, /No authoritative public source found in this research exposes the other 18 current/)
  assert.match(lens, /These percentages describe only the disclosed top ten/)
  assert.match(lens, /Latest complete audited holdings: 31 December 2025/)
  assert.equal((data.match(/^  \['/gm) ?? []).length, 34)
})

test('The current top ten is complete and public thesis evidence stays graded', () => {
  for (const name of ['Amazon', 'Micron', 'IREN', 'SanDisk', 'Robinhood', 'Marvell', 'TSMC', 'Infineon', 'Hinge Health', 'Oscar Health']) {
    assert.match(data, new RegExp(`name: '${name}'`))
  }
  assert.match(data, /export type EvidenceGrade = 'BIT thesis' \| 'BIT commentary' \| 'Analyst inference'/)
  assert.equal((data.match(/grade: 'BIT thesis'/g) ?? []).length, 3)
  assert.equal((data.match(/grade: 'BIT commentary'/g) ?? []).length, 3)
  assert.equal((data.match(/grade: 'Analyst inference'/g) ?? []).length, 4)
  assert.match(lens, /the interpretations below are analyst inference and must never be/)
})

test('Research process explains thesis formation, data, weighting, and challenge', () => {
  assert.match(lens, /Thesis →\s*Edge → Signal → Key Move/)
  assert.match(lens, /Volume × Price ×\s*Mix × Margin/)
  assert.match(lens, /Alternative data is not presented as an indiscriminate stock screener/)
  assert.match(lens, /Duolingo example/)
  assert.match(lens, /Carvana example/)
  assert.match(lens, /Devil’s Advocate process for positions above 5% of NAV/)
  assert.match(lens, /Bottom-up selection coexists with top-down exposure control/)
})

test('BIT Lens states the Aion and human decision boundary', () => {
  assert.match(lens, /production AI platform <strong>Aion<\/strong>/)
  assert.match(lens, /scores, alerts,\s*signals, and insights/)
  assert.match(lens, /The decision boundary remains human/)
  assert.match(lens, /does not expose its exact\s*current scale or effectiveness/)
})

test('FLI comparison standard remains source-to-action rather than a trade call', () => {
  for (const label of ['Development.', 'Exposure.', 'Operating driver.', 'Expectation gap.', 'Opportunity and downside.', 'Horizon.', 'Next evidence.', 'Human action.']) {
    assert.match(lens, new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))
  }
  assert.match(lens, /KPI and P&amp;L translation\./)
  assert.match(lens, /Worked example: frontier context growth → Micron/)
  assert.match(lens, /not an automatic buy or sell/)
})

test('The redesign is text-first and removes the diagram-heavy UI', () => {
  assert.match(styles, /\.lens-reading \{[\s\S]*?margin-top: 48px/)
  assert.match(styles, /\.lens-reading p,[\s\S]*?max-width: 72ch/)
  assert.match(styles, /\.lens-reading p,[\s\S]*?font-size: 1rem;[\s\S]*?line-height: 1\.7/)
  assert.doesNotMatch(lens, /<svg|<details|lens-canvas|lens-theme-bar/)
  assert.doesNotMatch(styles, /\.lens-canvas|\.lens-svg-|\.lens-theme-bar/)
})

test('Company universe exposes the canonical context without implying automatic scope', () => {
  assert.match(universe, /getCachedJSON<InvestmentCompanyUniverse>\('\/api\/bit-lens\/companies'\)/)
  assert.match(universe, /not automatic inclusion in an Investment output/)
  assert.doesNotMatch(universe, /The context behind each company/)
  assert.doesNotMatch(universe, /company-universe-facts/)
  assert.match(universe, /Context used by the agent/)
  assert.match(universe, /starting hypotheses, not a closed list/i)
  assert.match(universe, /The Event must\s+establish a defensible connection/)
  assert.match(universe, /BIT’s public view/)
  assert.match(universe, /Research limits/)
  assert.match(universe, /Company sources/)
  assert.match(universe, /Disclosure history/)
  assert.match(universe, /Open visible/)
  assert.doesNotMatch(universe, /AI channel count/)
  assert.doesNotMatch(universe, /AI \{company\.analyst_context\.frontier_ai_channels\.length/)
  assert.match(universe, /Public evidence/)
  assert.doesNotMatch(universe, /const companies = \[/)
})

test('Company universe uses the existing flat research-ledger grammar', () => {
  assert.match(styles, /\.company-ledger \{[\s\S]*?border-top: 1px solid var\(--border-strong\)/)
  assert.match(styles, /\.company-ledger > details > summary \{[\s\S]*?display: grid/)
  assert.match(styles, /\.company-detail \{[\s\S]*?background: var\(--surface\)/)
  assert.match(styles, /\.company-agent-context \{[\s\S]*?display: grid/)
  assert.match(styles, /\.company-supporting-context \{[\s\S]*?grid-column: 2/)
  assert.match(styles, /\.company-evidence-grade\.is-explicit_thesis/)
  assert.doesNotMatch(styles, /\.company-[^{]*\{[^}]*box-shadow/)
})
