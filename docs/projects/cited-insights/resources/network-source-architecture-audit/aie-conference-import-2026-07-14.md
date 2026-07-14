# AI Engineer conference Registry import — 2026-07-14

## Decision

Directly admit every X-addressable speaker in the official AI Engineer World's
Fair 2026 and 2024 directories. Conference curation is an admission source,
not a vote, a ranking boost, or proof that the cohort is optimal.

The product Registry is intentionally lean. It retains one identity, one
verified X channel, the best available conference-supplied role and bio, and
one listed organization relationship per person. When the same person appears
in both requested events, the 2026 claim replaces the 2024 claim. Event
history, talks, LinkedIn, personal sites, and ambiguous organization X links
remain only in the immutable raw source snapshots.

## Official evidence

| Source | Records | X-addressable | SHA-256 |
|---|---:|---:|---|
| AI Engineer World's Fair 2026 | 552 | 315 | `d05c46958f2a6cfa199dbc75e05f204e2b154fc8efe1c95279f8caccbafb4d32` |
| AI Engineer World's Fair 2024 | 173 | 134 | `04722928a72ad601ad296c046bf67049cddb79d7f7dff427c60615e3537be02d` |
| AI Engineer Europe 2026 | 162 | 103 | `949fc1b2c827f65e4f7b0140fef9f5db6333610f7c0f6394fa2ab2f3a1df922c` |
| AI Engineer Summit 2023 | 58 | 34 | `cffd5e2426d3f44b7b5738e476dc8ec896eb981f2ab01bd0b5357cd8149178bb` |

Only the two World's Fair sources were admitted. Europe 2026 and Summit 2023
remain available as raw, checksum-bound evidence for a future explicit
decision. Raw responses and the resumable X-profile cache live under ignored
`data/raw/conference-sources/`; the tracked
`data/registry/conference-sources.json` manifest binds the supported URLs,
formats, observation dates, and hashes.

## Admission result

The two requested directories contain 725 speaker records and 423 unique
X-addressable people; 26 appear in both years. The pre-write audit found 96
already active identities, 327 new identities, and no rejected-handle
collisions.

The idempotent write produced the following current Registry boundary:

- 423 conference-sourced people, represented once each.
- 327 new people and 253 new organization identities beyond the prior
  Registry checkpoint.
- 423 admission/source claims, 422 roles, 403 bios, 419 listed-company claims,
  and 419 person-to-organization affiliations.
- No `company_x_candidate`, talk, LinkedIn, personal-site, or repeated
  historical conference facts.

Organizations are useful resolution targets for affiliations, but conference
inclusion gives neither people nor organizations special rank or voting
weight.

## X reconciliation

The old immutable following snapshot already covered 80 of the 423 conference
people. The remaining 343 conference handles needed stable provider identity
evidence:

- 330 public accounts were resolved and hydrated with stable X IDs and
  follower counts.
- 12 handles were confirmed missing and one was confirmed suspended.
- Those 13 unavailable identities were moved to reason-bearing Registry
  rejections; they are preserved for audit but excluded from active monitoring
  and the next voting cohort.
- 410 conference people therefore remain active and X-addressable; 330 are new
  to the previous outgoing-follow snapshot.

The two provider passes made 356 profile requests: 343 initial attempts plus a
13-handle retry while terminal failure caching was added. At 18 provider
credits per profile, the best available cost estimate is 6,408 credits, or
`$0.06408`. Successful raw profile responses and terminal failures are cached,
so normal reruns make zero provider requests.

Across the whole active Registry, 2,564 X sources currently have stable IDs.
Of these, 2,212 overlap the prior snapshot and 352 are new to it. The 22
non-conference additions are retained because the new immutable cohort must
describe the full current Registry boundary rather than a conference-only
subset.

## Next immutable network run

The next snapshot will:

1. Freeze the active 2,564-source Registry against a committed database hash.
2. Copy unchanged terminal evidence for the 2,212 stable-ID sources shared
   with `registry-following-2026-07-11-v1`.
3. Seed the 330 newly fetched conference profile responses from the raw cache,
   avoiding duplicate paid profile calls.
4. Collect outgoing-follow pages only for the 352 genuinely new active
   sources, then finalize and validate the child snapshot.
5. Build a new derived analysis with the new cohort and voting-entity
   denominator disclosed explicitly.

This is an incremental mixed-observation snapshot, not a claim that every edge
was observed on one day. Inherited sources retain their 2026-07-11 evidence
timestamps; new sources retain their actual 2026-07-14 timestamps. Snapshot
lineage records the parent checksum and exact copied row counts.

## Reproduce

```bash
PYTHONPATH=src .venv/bin/python -m fli.cli conference-sources audit \
  --source aie-worldsfair-2026 --source aie-worldsfair-2024
PYTHONPATH=src .venv/bin/python -m fli.cli conference-sources import \
  --source aie-worldsfair-2026 --source aie-worldsfair-2024
PYTHONPATH=src .venv/bin/python -m fli.cli conference-sources hydrate-profiles \
  --source aie-worldsfair-2026 --source aie-worldsfair-2024
PYTHONPATH=src .venv/bin/python -m fli.cli conference-sources reject-unavailable \
  --source aie-worldsfair-2026 --source aie-worldsfair-2024
```

The import and cache-replay paths are deterministic and idempotent. A new
provider call still requires the configured TwitterAPI.io secret; raw-source
parsing and Registry reconciliation do not.
