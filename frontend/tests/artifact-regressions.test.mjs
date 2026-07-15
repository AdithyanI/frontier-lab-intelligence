import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const artifactSource = await readFile(
  new URL('../src/pages/Artifacts.tsx', import.meta.url),
  'utf8',
)
const feedSource = await readFile(new URL('../src/pages/Feed.tsx', import.meta.url), 'utf8')
const evidenceSource = await readFile(
  new URL('../src/pages/Evidence.tsx', import.meta.url),
  'utf8',
)
const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8')

test('Feed and Primary artifacts are separate views of one Evidence workspace', () => {
  assert.match(appSource, /useAuditDatePath\('\/evidence\/feed'\)/)
  assert.match(appSource, /<NavLink to=\{evidencePath\}>Evidence<\/NavLink>/)
  assert.match(appSource, /<Route path="\/evidence" element=\{<Evidence \/>\}>/)
  assert.match(appSource, /<Route index element=\{<Navigate to="feed" replace \/>\} \/>/)
  assert.match(appSource, /<Route path="feed" element=\{<Feed \/>\} \/>/)
  assert.match(appSource, /<Route path="artifacts" element=\{<Artifacts \/>\} \/>/)
  assert.doesNotMatch(appSource, /<NavLink to="\/feed">Feed<\/NavLink>/)
  assert.doesNotMatch(appSource, /<NavLink to="\/artifacts">Artifacts<\/NavLink>/)
  assert.match(evidenceSource, /Inspect what the tracked network amplified/)
  assert.match(evidenceSource, /useAuditDatePath\('\/evidence\/feed'\)/)
  assert.match(evidenceSource, /useAuditDatePath\('\/evidence\/artifacts'\)/)
  assert.match(evidenceSource, /<NavLink to=\{feedPath\}>Feed<\/NavLink>/)
  assert.match(evidenceSource, /<NavLink to=\{artifactsPath\}>Primary artifacts<\/NavLink>/)
})

test('Feed and Artifacts share the same seven-date navigator', () => {
  assert.match(feedSource, /<DateNavigator/)
  assert.match(artifactSource, /<DateNavigator/)
  assert.match(artifactSource, /ariaLabel="Artifact source date"/)
  assert.match(artifactSource, /moveDateWindow\('older'\)/)
  assert.match(artifactSource, /moveDateWindow\('newer'\)/)
})

test('Artifacts defaults from source dates and guards stale paginated responses', () => {
  assert.match(artifactSource, /getJSON<ArtifactDates>\('\/api\/artifacts\/dates'\)/)
  assert.match(artifactSource, /payload\.latest_date/)
  assert.match(artifactSource, /activeViewKeyRef\.current !== viewKey/)
  assert.match(artifactSource, /activeViewKeyRef\.current !== baseKey/)
  assert.match(artifactSource, /data\.matching_total/)
})

test('Artifacts search is debounced and visible source dates are prefetched', () => {
  assert.match(artifactSource, /setTimeout\(\(\) => setDebouncedQuery\(query\), 180\)/)
  assert.match(artifactSource, /for \(const value of visibleDates\)/)
  assert.match(artifactSource, /Search title, host, or URL/)
})

test('Artifact retrieval state is disclosed only in expanded provenance', () => {
  assert.doesNotMatch(artifactSource, /artifact-state/)
  assert.doesNotMatch(artifactSource, /<span>Retrieval<\/span>/)
  assert.match(artifactSource, /<dt>Retrieval<\/dt>/)
  assert.match(artifactSource, /fetchLabels\[item\.fetch_state\]/)
  assert.match(artifactSource, /Extracted content/)
  assert.match(artifactSource, /Open full text/)
  assert.match(artifactSource, /\/api\/artifacts\/\$\{encodeURIComponent\(item\.artifact_id\)\}\/text/)
  assert.match(artifactSource, /<details className="artifact-extracted" onToggle=\{loadExtractedText\}>/)
  assert.doesNotMatch(artifactSource, /className=\{rowClassName\} onToggle/)
})

test('Artifacts inherit Feed rank while keeping source time secondary', () => {
  assert.match(artifactSource, /<span>Feed rank<\/span>/)
  assert.match(artifactSource, /item\.best_source_rank/)
  assert.match(artifactSource, /<span>Source time<\/span>/)
  assert.match(artifactSource, /item\.source_published_at/)
  assert.match(artifactSource, /compareArtifactsByFeedRank/)
  assert.match(artifactSource, /left\.best_source_rank - right\.best_source_rank/)
  assert.match(artifactSource, /normalizeArtifactPage\(payload\)/)
  assert.match(artifactSource, /requestArtifactPage\(request, \{ refresh: true \}\)/)
  assert.match(artifactSource, /sortArtifactsByFeedRank\(\[\.\.\.current, \.\.\.payload\.items\]\)/)
})

test('Artifacts from one exact Feed envelope share one visual rank rail', () => {
  assert.match(artifactSource, /previousGroup\?\.\[0\]\.source_event_id === item\.source_event_id/)
  assert.match(artifactSource, /rankIsContinuation=\{index > 0\}/)
  assert.match(artifactSource, /continuesRankGroup=\{index < group\.length - 1\}/)
  assert.match(artifactSource, /!rankIsContinuation && <strong>#\{item\.best_source_rank\}<\/strong>/)
})

test('Artifact provenance deep-links to the exact ranked Feed envelope', () => {
  assert.match(artifactSource, /source_event_id/)
  assert.match(artifactSource, /Feed envelope/)
  assert.match(artifactSource, /\/evidence\/feed\?date=/)
  assert.match(feedSource, /useSearchParams/)
  assert.match(feedSource, /event_id:/)
  assert.match(feedSource, /targetEventId/)
  assert.match(feedSource, /event-row--focused/)
})
