import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const artifactSource = await readFile(
  new URL('../src/pages/Artifacts.tsx', import.meta.url),
  'utf8',
)
const feedSource = await readFile(new URL('../src/pages/Feed.tsx', import.meta.url), 'utf8')

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
})

test('Artifacts inherit Feed rank while keeping source time secondary', () => {
  assert.match(artifactSource, /<span>Feed rank<\/span>/)
  assert.match(artifactSource, /item\.best_source_rank/)
  assert.match(artifactSource, /<span>Source time<\/span>/)
  assert.match(artifactSource, /item\.source_published_at/)
})

test('Artifact provenance deep-links to the exact ranked Feed envelope', () => {
  assert.match(artifactSource, /source_event_id/)
  assert.match(artifactSource, /Feed envelope/)
  assert.match(artifactSource, /\/feed\?date=/)
  assert.match(feedSource, /useSearchParams/)
  assert.match(feedSource, /event_id:/)
  assert.match(feedSource, /targetEventId/)
  assert.match(feedSource, /event-row--focused/)
})
