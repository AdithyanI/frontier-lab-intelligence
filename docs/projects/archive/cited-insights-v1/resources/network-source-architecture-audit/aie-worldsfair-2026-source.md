# AI Engineer World's Fair Registry Source — Implementation Contract

Date: 2026-07-14

Status: requested 2026 + 2024 cohort imported; network refresh complete.

Decision context: `project-brief.md` Decision Addendum.

## Product role

The official AI Engineer World's Fair speaker directories are a curated
Registry admission source. They help seed the product with working AI
researchers, builders, and organizations that the original bootstrap may have
missed. They do not confer authority, prominence, network support, or a ranking
bonus.

Admission and voting are separate:

- **Registry admission:** the person is a source the product may monitor.
- **Profile reconciliation:** the listed X account resolves to a stable public
  provider identity.
- **Snapshot membership:** that stable X account is frozen into a particular
  outgoing-follow collection.
- **Voting:** the corresponding active canonical entity has complete outgoing
  evidence in that snapshot.

The UI and derived analysis must never collapse these states.

## Accepted source scope

Admit every unique X-addressable speaker from:

- AI Engineer World's Fair 2026: 315 X-addressable records.
- AI Engineer World's Fair 2024: 134 X-addressable records.

Together these resolve to 423 unique people because 26 occur in both years.
Europe 2026 and Summit 2023 remain raw-only until a separate product decision.

The pre-admission audit is preserved in
`aie-conference-import-2026-07-14.md`: 96 of the 423 identities were already
active and 327 were new.

## Canonical data boundary

Deterministically parse from stored official snapshots, never from a live page
during import. Resolve by exact normalized X handle; never merge by name alone.

For each person, keep only:

- canonical name and exact personal X channel;
- one best available source-bound role;
- one best available source-bound bio;
- one listed company label, plus an affiliation only when the organization is
  independently channel-addressable;
- the source/date/evidence needed to audit those claims.

When both years contain a claim, prefer the newer 2026 observation. The full
event history remains in raw snapshots. Do not canonicalize talk titles,
LinkedIn, personal websites, conference frequency, or speculative organization
X handles. Do not retain repeated year-specific copies of the same role, bio,
company, or affiliation.

The raw company label alone is not enough to create a Registry organization.
Create or link an organization only when the label matches an existing
channel-backed identity or the official conference record supplies a website;
otherwise retain the label only on the person. A conference listing does not
establish an organization X account and does not alter organization voting
weight.

## Provider reconciliation

Fetch only profiles missing a stable X ID or follower observation. Persist the
complete provider response to the ignored resumable cache before updating the
tracked Registry. Exact provider identity must match the requested handle.

Provider-confirmed missing or suspended handles receive a reason-bearing
Registry rejection. They remain auditable but are excluded from active
monitoring and future cohort freezes. Retryable transport failures never become
rejections.

The accepted run resolved 330 newly needed public profiles and rejected 13
unavailable identities. A cached rerun makes no external calls.

## Incremental following snapshot

Create a new frozen cohort for the complete active Registry, not a
conference-only graph. The child snapshot may reuse a finalized parent only
when the stable source X ID occurs in both cohorts. Copy terminal source state,
raw profile/page evidence, normalized accounts, and edges without changing
their original observation timestamps. New sources remain pending.

Record parent path, checksum, copy time, and copied row counts in
`snapshot_lineage`. The resulting snapshot has one explicit current membership
denominator but mixed evidence dates; documentation and analysis must say so.

Seed the already cached conference profile responses into the mutable child
before collection. Then collect only pending sources, finalize only when every
source is terminal, and validate before deriving rankings.

The completed child is
`registry-following-2026-07-14-aie-worldsfair-v2`: 2,564 frozen source
accounts, 2,558 complete sources, 2,832,858 edges, and 557,363 discovered
targets. `entity-overlap-v3` resolves those sources to 2,521 voting entities
and materializes entity-union support for 2,527 active stable-X Registry
identities, including 38 explicit zero-support rows. Full lineage and checksums
live in the tracked snapshot manifest.

## Validation

- Parser coverage for both official JSON and historical `__NEXT_DATA__`.
- Exact-handle de-duplication, idempotent import, newest-fact consolidation,
  rejection preservation, and no ambiguous organization X candidates.
- Profile cache identity checks, zero-call replay, terminal-failure caching,
  and reason-bearing unavailable-account rejection.
- Parent reuse validation, idempotency, shared-source intersection semantics,
  preserved timestamps, and new-source pending state.
- Frozen cohort, child snapshot, and derived analysis checksums recorded in
  tracked manifests.
- Old/new denominator and rank movement reported separately from public reach.
- `bash scripts/check-fast.sh` plus a live Network UI proof before handoff.

## Non-goals

- No claim that these are the best 423 people in AI.
- No conference-frequency or year-count feature.
- No recursive Registry expansion from every discovered follow target.
- No blanket person/organization weighting.
- No LinkedIn scraping, talk ingestion, or speculative organization channel
  attachment.
