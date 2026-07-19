import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { readStyles } from './source-files.mjs'

const appSource = await readFile(new URL('../src/app/App.tsx', import.meta.url), 'utf8')
const networkSource = await readFile(
  new URL('../src/features/network/NetworkLayout.tsx', import.meta.url),
  'utf8',
)
const registrySource = await readFile(
  new URL('../src/features/network/RegistryPage.tsx', import.meta.url),
  'utf8',
)
const addProfileSource = await readFile(
  new URL('../src/features/network/AddProfilePage.tsx', import.meta.url),
  'utf8',
)
const rankingSource = await readFile(
  new URL('../src/features/network/RankingPage.tsx', import.meta.url),
  'utf8',
)
const appStyles = readStyles()

test('Network owns Registry, Ranking, and Add Profile as explicit subviews', () => {
  assert.match(appSource, /<NavLink to="\/network">Network<\/NavLink>/)
  assert.match(appSource, /<Route path="\/network" element=\{<Network \/>\}>/)
  assert.match(appSource, /<Route path="ranking" element=\{<Ranking \/>\} \/>/)
  assert.match(appSource, /<Route path="registry" element=\{<Registry \/>\} \/>/)
  assert.match(appSource, /<Route path="add-profile" element=\{<AddProfile \/>\} \/>/)
  assert.doesNotMatch(appSource, /<NavLink to="\/ranking">Ranking<\/NavLink>/)
  assert.match(networkSource, /Ranking shows which accounts the screened source set follows/)
  assert.match(networkSource, /<NavLink to="\/network\/ranking">Ranking<\/NavLink>[\s\S]*?<NavLink to="\/network\/registry">Registry<\/NavLink>[\s\S]*?<NavLink to="\/network\/add-profile">Add Profile<\/NavLink>/)
  assert.match(addProfileSource, /id="add-profile-title">Add Profile<\/h2>/)
})

test('Network defaults to Ranking while the product lands on Insights', () => {
  assert.match(appSource, /<Route path="\/" element=\{<Navigate to="\/insights" replace \/>\} \/>/)
  assert.match(appSource, /<Route path="\*" element=\{<Navigate to="\/insights" replace \/>\} \/>/)
  assert.match(appSource, /<Route index element=\{<Navigate to="ranking" replace \/>\} \/>/)
  assert.match(rankingSource, /<h2 className="network-view-title" id="ranking-title">/)
  assert.match(registrySource, /<h2 className="network-view-title" id="registry-title">Registry<\/h2>/)
  assert.match(registrySource, /X reach/)
  assert.match(registrySource, /entity\.reach_rank/)
  assert.match(registrySource, /fmtCompact/)
  assert.match(registrySource, /ent-metric-rank/)
  assert.match(registrySource, /ent-metric-detail/)
  assert.match(registrySource, /registry-card-metrics/)
  assert.doesNotMatch(registrySource, /ent-reach-separator/)
  assert.doesNotMatch(registrySource, /ent-network-separator/)
  assert.match(registrySource, /Network support/)
  assert.match(registrySource, /entity\.network_rank/)
  assert.match(registrySource, /entity\.network_follow_count/)
  assert.match(registrySource, /entity\.network_source_total/)
  assert.match(registrySource, /screened Registry entities follow this entity/)
  assert.match(registrySource, /combined X followers/)
  assert.match(registrySource, /sortField/)
  assert.match(registrySource, /useState<SortField>\('network'\)/)
  assert.match(registrySource, /useRef\('all\\0network\\0asc'\)/)
  assert.doesNotMatch(registrySource, /Registry follows/)
})

test('Network filters and entity details expose honest control semantics', () => {
  assert.match(rankingSource, /type="search"/)
  assert.match(rankingSource, /aria-label="Search ranked accounts"/)
  assert.match(rankingSource, /role="group" aria-label="Filter by kind"/)
  assert.match(registrySource, /role="group" aria-label="Filter Registry"/)
  assert.doesNotMatch(rankingSource, /role="tab"|role="tablist"/)
  assert.doesNotMatch(registrySource, /role="tab"|role="tablist"/)
  assert.match(registrySource, /className="ent-name-button"/)
  assert.match(registrySource, /aria-label=\{`Open \$\{entity\.name\}`\}/)
  assert.doesNotMatch(registrySource, /tabIndex=\{0\}/)
})

test('Network subviews use one ruled secondary navigation language', () => {
  assert.match(networkSource, /className="ruled-nav network-tabs"/)
  assert.match(appStyles, /\.ruled-nav \{[\s\S]*?width: 100%;[\s\S]*?border-top: 1px solid var\(--border-strong\);[\s\S]*?border-bottom: 1px solid var\(--border\);/)
  assert.match(appStyles, /\.network-tabs a\.active,[\s\S]*?\.evidence-tabs a\.active \{[\s\S]*?background: var\(--ink\);[\s\S]*?color: #fff;/)
  assert.match(appStyles, /\.network-view \{ margin-top: 36px; \}/)
})
