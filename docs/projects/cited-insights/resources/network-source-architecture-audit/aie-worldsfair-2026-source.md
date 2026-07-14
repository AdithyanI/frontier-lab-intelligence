# AIE World's Fair 2026 Speaker Source — Implementation Spec

Date: 2026-07-14
Status: initial 20-person cohort imported; expansion remains reversible.
Owner decision context: `project-brief.md` Decision Addendum.

## What and why

Ingest the speaker directory of the AI Engineer World's Fair 2026
(https://www.ai.engineer/worldsfair/2026) as a new Registry candidate source
with **bounded direct admission**. Each speaker entry carries name, exact role,
employer, bio, and often an X profile link — three assets at once:

1. A curated candidate list from the premier AI-engineering conference, same
   architectural class as the existing `digg` / `smol_ai` / AI High Signal
   source facts.
2. Free structured affiliation data ("Member of Technical Staff, Anthropic")
   — the cheap version of lab-employee extraction, feeding the role/affiliation
   plan.
3. **An independent, non-circular validation cohort for the network audit** —
   the only external label set available before the deadline. This is the
   highest-value use and it constrains the execution order below.

Adi's accepted trust policy: conference curation is a useful candidate screen,
not a ranking weight. The first import is deliberately limited to the first 20
unique X-addressable speakers in the official World's Fair 2026 response.
Expansion requires another explicit bounded import; wrong admissions remain
cheap to reject without discarding their source evidence.

## Hard ordering constraint

**Run the coverage query before any insertion.** The statement "our trusted
network already independently surfaced N% of AIE World's Fair speakers" is the
audit's non-circular validation evidence. Admitting first makes coverage
trivially 100% and destroys the experiment permanently. Sequence:

1. Snapshot raw directory.
2. Parse + resolve identities (read-only against the Registry).
3. Compute and persist the coverage/miss report.
4. Then admit.

## Implementation steps

### 1. Raw snapshot (data-first)

- Fetch the official structured speaker response. World's Fair 2026 and Europe
  2026 publish `speakers.json`; World's Fair 2024 and Summit 2023 preserve
  structured `__NEXT_DATA__` in their official pages.
- Preserve the as-fetched payloads under the repo's raw-data conventions
  (follow the pattern of existing sources under `data/raw/`; one dated,
  immutable snapshot directory with a manifest: URL, fetched_at, content
  hash). Parsing runs from the stored snapshot, never live.

### 2. Parse and normalize

The canonical import is intentionally lean: `name`, `role_title`, `employer`,
`bio`, `x_handle` (nullable), source ID, observation date, and evidence URL.
Talk titles, LinkedIn, and personal website/blog fields remain only in the raw
snapshot. Lowercase X handles per `accounts.handle` convention.

### 3. Identity resolution (mechanical, not a review gate)

- Match against existing entities by X handle → `channels` (`kind='x'`, `key`)
  → `entity_channels`. Do not merge people by name alone.
- Many speakers are already in the 2,197 (e.g., Anthropic/OpenAI/DeepMind
  staff). Do not create duplicates — duplicate entities would corrupt the
  entity-union support aggregation being fixed in the same batch.
- Speakers without X remain preserved in the raw snapshot and are not admitted.
  Do not fabricate handles or introduce LinkedIn as a channel in this batch.

### 4. Coverage/miss report (before admission)

Persist as `resources/network-source-architecture-audit/aie-coverage-report.md`
with reproducible SQL. Predeclared measures:

- Fraction of speakers already in the active Registry.
- Fraction of non-member speakers' X accounts appearing in the 463,180-target
  discovery ranking, with their support counts (evidence the follow-graph
  discovery engine surfaces them independently).
- The misses: speakers with X accounts receiving little/no network support —
  these are the interesting counterexamples either way.
- Per-lab breakdown using parsed employers (coverage of frontier-lab
  employees specifically, per the case prompt's emphasis).

### 5. Bounded direct admission

- Admit the selected X-addressable cohort with provenance:
  source facts per the `account_source_facts` pattern
  (`source='aie_worldsfair_2026'`, facts: `role`, `employer`, `speaker`,
  `evidence_url`), and an admission note naming the source.
- Record `role_title`, bio, and employer as source-bound facts on existing
  entities too. Store the listed person-to-organization relationship in
  `entity_affiliations`; it does not imply a permanent/current employment fact.
- Create or reuse the listed organization. Attach an organization website only
  where the official source clearly identifies it; never infer an organization
  X account from a speaker's personal profile.
- New admits join daily X collection like any other Registry member.
- **They do not vote.** The immutable following snapshot
  (`registry-following-2026-07-11-v1`) predates them; voting eligibility
  arrives only with a future snapshot v2 collection (post-submission). Ensure
  derived views keep denominators honest (support denominators reference the
  snapshot's 2,197 voting entities, not the enlarged Registry).

### 6. Validation

- Focused tests for parser behavior, stable limit/de-duplication, idempotent
  source facts and affiliations, and preservation of prior rejections.
- Reconcile counts: speakers parsed = matched + newly admitted +
  unresolvable(listed).
- `bash scripts/check-fast.sh`; verify the Registry UI shows new members with
  their provenance at `http://127.0.0.1:8797` (always-on server; rebuild
  frontend only if UI changes are involved).
- Record spend/telemetry if any LLM assist is used for parsing (prefer none —
  the page is structured; deterministic parsing beats extraction here).

## Non-goals

- No cohort cutoff, tiering, or re-ranking based on this list.
- No recursive expansion from speakers' follow graphs.
- No new following-snapshot collection in this batch.
- No LinkedIn storage or scraping, talk/session ingestion, or personal-site
  canonicalization.
- Do not let this displace cited-insights delivery work; this is a bounded
  side batch (~half a day target).

## Initial result

The official snapshots contain 945 conference records across four supported
events, resolving to 528 unique X handles. Before insertion, 101 of those
handles were already present and active; none were rejected. The accepted
first batch selected exactly 20 World's Fair 2026 handles in source order:
4 matched existing people and 16 created new people. It wrote 19 listed
affiliations, reused or created 18 organizations (15 new), and retained role,
bio, company, source, date, and evidence URL. The other 508 X-addressable
records and all non-X records remain snapshot-only until a later decision.
