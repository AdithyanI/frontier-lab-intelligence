# Artifact Store v1 — Adversarial Data-Model Review

## Verdict

The source/artifact split is correct: X posts remain independently addressable
evidence, outbound primary pages become shared artifacts, and event IDs remain
a derived join rather than ownership. The proposed four-table model is close,
but it is not yet safe to implement unchanged. Three boundaries need tightening:
immutable source identity, URL resolution/merge behavior, and terminal fetch
snapshots.

This review treats the store as a durable local catalog whose inputs are
rebuildable but whose fetched bytes must be reusable. It does **not** recommend
a generic connector framework, semantic deduplication, or a UI.

## P0 fixes before implementation

### 1. Version canonicalization and define redirect convergence

`artifact_id = SHA-256(canonical_url)` is deterministic, but it makes identity
dependent on the canonicalization rules. Persist a `canonicalization_contract`
or schema version and include it in every import run. The v1 normalizer should
be deliberately narrow: lowercase scheme/host, remove a default port and
fragment, normalize an empty path, remove only an explicit tracking-parameter
allowlist, retain other query parameters, and apply only reviewed host rules
such as arXiv `pdf` to `abs`. Do not merge HTTP with HTTPS, bodies with identical
hashes, or cross-host declared canonicals automatically.

The store must also define what happens when two locally distinct candidates
redirect to the same final URL. This is the main canonical-library use case.
Resolve the final URL to its deterministic artifact ID, then transactionally
move aliases and observations to that winner. Preserve the losing canonical URL
as an alias. If an alias already points to a different artifact and convergence
cannot be proven by the current redirect, fail closed and record a conflict;
never silently reassign it. A plain `alias_url PRIMARY KEY` is acceptable only
with this explicit conflict behavior.

### 2. Point observations at an immutable X snapshot, not only a post ID

`(source_provider, source_external_id)` identifies the logical X post, but the
normalized `x_post` row is refreshed in place. The existing immutable boundary
is `x_post_observation` / `feed_post.raw_sha256`. Add
`source_snapshot_sha256` (the Feed `raw_sha256`) to every artifact observation.
That proves which exact provider payload contained the URL.

The proposed uniqueness constraint also loses provenance when one source post
contains two observed aliases that converge to the same artifact. Make the
observation identity include the exact `observed_url` (or introduce a separate
observation-URL relation). A suitable v1 key is:

```text
source_kind + source_provider + source_external_id +
source_snapshot_sha256 + observed_url + relation
```

`artifact_id` is then the current deterministic resolution of that immutable
observation. This keeps repeated imports idempotent while retaining every URL
form actually seen in the source.

### 3. Record unresolved/rejected candidates, not only accepted artifacts

Some input URLs cannot produce an `artifact_id`: malformed URLs, non-HTTP
schemes, ordinary X status/profile/media URLs, unsupported X article shapes,
or canonicalization conflicts. They currently disappear before any of the four
tables can represent them. Add a small import-item/candidate ledger (or allow a
status-bearing observation with nullable `artifact_id`) containing source
snapshot identity, observed and provider-expanded URL, decision
`accepted | excluded | failed`, a stable reason code, normalizer contract, and
timestamps. This is necessary for the stated “explicit failure records” and
for proving that an idempotent replay did not merely skip inputs silently.

Keep reason codes mechanical (`ordinary_x_status`, `profile_url`,
`unsupported_scheme`, `invalid_url`, `alias_conflict`); do not add topic
categories.

### 4. Make one fetch attempt resumable and its terminal evidence complete

`artifact_fetch` needs more than nullable HTTP fields. Persist at least:

```text
fetch_id, artifact_id, requested_url, status,
started_at, completed_at, attempt_count,
final_url, redirect_chain_json, http_status,
content_type, charset, content_length,
raw_sha256, raw_snapshot_ref,
extractor_contract, extracted_title,
text_sha256, text_snapshot_ref, text_length, text_truncated,
error_code, error_message, retryable
```

A row may move from `pending/in_progress` to one terminal state, then becomes
immutable. Claim work in a short `BEGIN IMMEDIATE` transaction, perform network
I/O outside that transaction, write content-addressed files atomically, and
finish the row in another short transaction. A stable request/idempotency key
must prevent two workers from fetching the same artifact for the same fetch
policy simultaneously. Treat interrupted `in_progress` rows as reclaimable
leases, not permanent success or failure.

The raw and clean-text paths must both be stored; a text hash without a text
snapshot reference does not satisfy replay. Title belongs first on the fetch
snapshot because pages are mutable. `artifact.title` may be a convenience
projection from the latest explicitly chosen successful fetch, not the sole
historical record.

### 5. Freeze batch provenance and make replay a logical no-op

Add a compact `artifact_import_run` (and, if fetching is separate, a fetch-run
record) with the source Feed/Event/triage run IDs, canonicalization contract,
input fingerprint, selection policy, expected/accepted/excluded/failed counts,
and lifecycle timestamps. This is not a generic job framework; it is the audit
record that explains which corrected kept-envelope cohort was imported.

All source-level inserts should be one transaction. Timestamps must derive from
source observation or the frozen run, not move on every replay. Use `INSERT OR
IGNORE`/conditional updates so importing the exact same fingerprint changes no
logical row. Enable foreign keys, WAL, and a busy timeout as existing stores do.

## Required indexes

Besides primary/unique indexes:

- `artifact_alias(artifact_id, alias_kind, alias_url)`
- `artifact_observation(artifact_id, observed_at, source_kind,
  source_provider, source_external_id)`
- `artifact_observation(source_kind, source_provider, source_external_id,
  source_snapshot_sha256)`
- candidate/import items by `(import_run_id, decision, reason_code)` and by
  immutable source snapshot identity
- `artifact_fetch(artifact_id, status, completed_at DESC, fetch_id)`
- a partial or equivalent index for latest successful fetches
- reclaim lookup by `(status, lease_expires_at)` if leases are persisted

Index the actual inspection/read queries; do not add event IDs or topic tags to
the canonical schema.

## Publication and read semantics

Do **not** add a global publication pointer yet. Unlike the Feed/Event read
model, this library is additive and has no product reader in v1. Inspection may
show accepted catalog rows plus only terminal fetches. A later cited-insight run
must freeze an explicit `artifact_id + fetch_id + text_sha256`; it must never
mean “whatever the latest fetch is.” Add a publication pointer only when a
consumer needs an atomically switched artifact cohort.

## Migration and rebuild semantics

- Persist one schema/canonicalization contract and reject unsupported versions
  with a clear rebuild/migration message; do not dual-read old and new layouts.
- Raw X evidence and source observations are replay inputs. Raw/text artifact
  snapshots are content-addressed durable evidence and must survive a catalog
  rebuild.
- Rebuilding the catalog must be possible from the frozen import manifest plus
  source X snapshots and existing fetch/snapshot metadata without refetching
  successful content.
- A future rule change that splits or merges canonical URLs is an explicit
  migration/rebuild, never an opportunistic write during a read.

## Future RSS/GitHub compatibility (schema test only)

The proposed `source_kind`, `source_provider`, `source_external_id`,
`source_url`, and `relation` fields are sufficient for future adapters once the
immutable `source_snapshot_sha256` is added. A GitHub release can use
`relation=self_publishes`; an RSS entry can use `links_to`. Neither requires a
new artifact identity rule. Do not add adapter tables, generic payload JSON, or
source-specific columns now.

## Deliberate deferrals

- semantic duplicate/mirror detection and same-body auto-merge
- topic/category/tag assignment
- cross-host declared-canonical trust
- conditional HTTP refresh policy and retention pruning beyond what the v1
  bounded fetch needs
- artifact UI, artifact publication pointer, RSS/GitHub ingestion, and cited
  insights

With the P0 changes above, the store remains small and X-first while preserving
the two properties later stages cannot recover: exactly where a URL was seen
and exactly which fetched bytes/text were used.
