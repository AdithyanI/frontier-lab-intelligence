import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8')
const networkSource = await readFile(
  new URL('../src/pages/Network.tsx', import.meta.url),
  'utf8',
)
const registrySource = await readFile(
  new URL('../src/pages/Registry.tsx', import.meta.url),
  'utf8',
)
const addProfileSource = await readFile(
  new URL('../src/pages/AddProfile.tsx', import.meta.url),
  'utf8',
)
const rankingSource = await readFile(
  new URL('../src/pages/Ranking.tsx', import.meta.url),
  'utf8',
)
const appStyles = await readFile(new URL('../src/app.css', import.meta.url), 'utf8')

test('Network owns Registry, Ranking, and Add Profile as explicit subviews', () => {
  assert.match(appSource, /<NavLink to="\/network">Network<\/NavLink>/)
  assert.match(appSource, /<Route path="\/network" element=\{<Network \/>\}>/)
  assert.match(appSource, /<Route path="ranking" element=\{<Ranking \/>\} \/>/)
  assert.match(appSource, /<Route path="registry" element=\{<Registry \/>\} \/>/)
  assert.match(appSource, /<Route path="add-profile" element=\{<AddProfile \/>\} \/>/)
  assert.doesNotMatch(appSource, /<NavLink to="\/ranking">Ranking<\/NavLink>/)
  assert.match(networkSource, /The Registry defines the screened source set/)
  assert.match(networkSource, /<NavLink to="\/network\/registry">Registry<\/NavLink>[\s\S]*?<NavLink to="\/network\/ranking">Ranking<\/NavLink>[\s\S]*?<NavLink to="\/network\/add-profile">Add Profile<\/NavLink>/)
  assert.match(addProfileSource, /id="add-profile-title">Add Profile<\/h2>/)
})

test('Network defaults to Registry while preserving Ranking and reach', () => {
  assert.match(appSource, /<Navigate to="\/network\/registry" replace \/>/)
  assert.match(appSource, /<Route index element=\{<Navigate to="registry" replace \/>\} \/>/)
  assert.match(rankingSource, /<h2 className="network-view-title" id="ranking-title">/)
  assert.match(registrySource, /<h2 className="network-view-title" id="registry-title">Registry<\/h2>/)
  assert.match(registrySource, /X reach/)
  assert.match(registrySource, /entity\.reach_rank/)
  assert.match(registrySource, /fmtCompact/)
  assert.match(registrySource, /ent-reach-separator/)
  assert.match(registrySource, /Network support/)
  assert.match(registrySource, /entity\.network_rank/)
  assert.match(registrySource, /entity\.network_follow_count/)
  assert.match(registrySource, /entity\.network_source_total/)
  assert.match(registrySource, /verified Registry X accounts/)
  assert.match(registrySource, /active Registry entities with stable X identity/)
  assert.match(registrySource, /sortField/)
  assert.doesNotMatch(registrySource, /Registry follows/)
})

test('Network subviews use one ruled secondary navigation language', () => {
  assert.match(appStyles, /\.network-tabs \{[\s\S]*?border-top: 1px solid var\(--border-strong\);[\s\S]*?border-bottom: 1px solid var\(--border\);/)
  assert.match(appStyles, /\.network-tabs a\.active \{[\s\S]*?background: var\(--ink\);[\s\S]*?color: #fff;/)
  assert.match(appStyles, /\.network-view \{ margin-top: 36px; \}/)
})
