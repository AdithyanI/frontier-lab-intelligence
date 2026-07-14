# AIE World's Fair 2026 Speaker Source — Implementation Spec

Date: 2026-07-14
Status: accepted by Adi; ready for engineering review and implementation.
Owner decision context: `project-brief.md` Decision Addendum.

## What and why

Ingest the speaker directory of the AI Engineer World's Fair 2026
(https://www.ai.engineer/worldsfair/2026) as a new Registry candidate source
with **direct admission**. Each speaker entry carries name, exact role,
employer, and often an X and/or LinkedIn profile link — three assets at once:

1. A curated candidate list from the premier AI-engineering conference, same
   architectural class as the existing `digg` / `smol_ai` / AI High Signal
   source facts.
2. Free structured affiliation data ("Member of Technical Staff, Anthropic")
   — the cheap version of lab-employee extraction, feeding the role/affiliation
   plan.
3. **An independent, non-circular validation cohort for the network audit** —
   the only external label set available before the deadline. This is the
   highest-value use and it constrains the execution order below.

Adi's accepted trust policy: conference curation is the relevance screen.
Speakers are admitted without per-person review. Registry admission is
reversible and reason-bearing, so wrong admissions are cheap to correct.

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

- Fetch the speaker directory (and per-speaker detail pages where they carry
  the social links; see screenshots in the session — X/LinkedIn icons appear
  on speaker/talk detail views). Check whether the site ships speaker data as
  JSON (Next.js `__NEXT_DATA__` or an API route) before scraping HTML.
- Preserve the as-fetched payloads under the repo's raw-data conventions
  (follow the pattern of existing sources under `data/raw/`; one dated,
  immutable snapshot directory with a manifest: URL, fetched_at, content
  hash). Parsing runs from the stored snapshot, never live.

### 2. Parse and normalize

Per speaker: `name`, `role_title`, `employer`, `x_handle` (nullable),
`linkedin_url` (nullable), `talk/track context` if cheap, `evidence_url`
(speaker page). Expect a few hundred entries. Lowercase X handles per
`accounts.handle` convention.

### 3. Identity resolution (mechanical, not a review gate)

- Match against existing entities: primary key is X handle → `channels`
  (`kind='x'`, `key`) → `entity_channels`; fallback exact-name match flagged
  for a quick manual scan of ambiguous collisions only.
- Many speakers are already in the 2,197 (e.g., Anthropic/OpenAI/DeepMind
  staff). Do not create duplicates — duplicate entities would corrupt the
  entity-union support aggregation being fixed in the same batch.
- LinkedIn-only speakers: create the identity with the LinkedIn channel
  recorded; they remain dormant for X collection until an X channel is known.
  Do not fabricate handles.

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

### 5. Direct admission

- Admit all resolved speakers not already active, with provenance:
  source facts per the `account_source_facts` pattern
  (`source='aie_worldsfair_2026'`, facts: `role`, `employer`, `speaker`,
  `evidence_url`), and an admission note naming the source.
- Record `role_title`/`employer` as evidenced affiliation facts on existing
  member entities too — the affiliation data is valuable even where admission
  is a no-op.
- New admits join daily X collection like any other Registry member.
- **They do not vote.** The immutable following snapshot
  (`registry-following-2026-07-11-v1`) predates them; voting eligibility
  arrives only with a future snapshot v2 collection (post-submission). Ensure
  derived views keep denominators honest (support denominators reference the
  snapshot's 2,197 voting entities, not the enlarged Registry).

### 6. Validation

- Focused tests for the parser (fixture from the raw snapshot) and identity
  resolution (dedup, casing, LinkedIn-only, name collisions).
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
- No LinkedIn scraping beyond storing the profile URL as-is.
- Do not let this displace cited-insights delivery work; this is a bounded
  side batch (~half a day target).

## Open questions for the implementing engineer

- Confirm where speaker social links live (listing page vs per-speaker/talk
  detail pages) and whether a structured data payload exists; choose the
  cheapest reliable fetch path and record it in the raw manifest.
- Confirm the current canonical write path for admissions in `src/fli/registry.py`
  (CLI vs direct function) and reuse it; do not invent a parallel path.
- If more than ~10% of speakers are unresolvable or ambiguous, stop and report
  before admitting — that signals a parsing or matching defect, not a data
  truth.
