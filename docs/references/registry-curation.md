# Registry Curation Contract

Exact contract for turning observed channels into entities and later teaching
an agent to classify and curate them. The architecture overview shows the
system shape; this reference records the implementation rules.

## Three Separate Questions

1. **Identity resolution:** which channels belong to the same real-world
   identity?
2. **Kind classification:** is the identity a `lab`, `person`, or `unknown`?
3. **Curation:** should Frontier Lab Intelligence `track` or `reject` it?

Do not collapse these into one status or model call. An entity means "observed
identity," not "approved for tracking."

## Channel-To-Entity Lifecycle

```text
channel import
  -> normalize channel key
  -> link to a known entity when identity is certain
  -> otherwise create one provisional entity with kind=unknown
  -> later kind classifier proposes lab/person/unknown
  -> later curation policy proposes track/reject
  -> human corrections override automated proposals durably
```

Current invariants:

- Every channel belongs to exactly one entity after `fli channels sync`.
- Synchronization is idempotent: a no-op rerun keeps the same database hash.
- Allowed canonical kinds are only `lab`, `person`, and `unknown`.
- A seeded lab may claim a channel from a one-channel provisional unknown.
- A resolved entity's channel cannot be silently reassigned.
- Missing identity evidence stays missing; uncertainty stays `unknown`.

## Current Universe

The frozen 2026-07-09 corpus contains:

| Kind | Entities |
| --- | ---: |
| lab | 10 |
| person | 0 |
| unknown | 2,598 |
| **total** | **2,608** |

Those entities own all 2,640 channels. The difference is the 32 additional
official website, GitHub, arXiv, and blog channels already linked to labs.

## Kind Classifier: Future Input Contract

The first classifier should see only identity-bearing fields:

```json
{
  "entity_id": 123,
  "name": "Example Name",
  "bio": "Observed profile biography or null",
  "channels": [
    {"kind": "x", "key": "example", "url": "https://x.com/example"}
  ]
}
```

It should return:

```json
{
  "kind": "lab | person | unknown",
  "confidence": 0.0,
  "rationale": "Short evidence-based explanation",
  "policy_version": "registry-kind-v1"
}
```

Digg rank, PageRank, follower count, list membership, and Digg role are
excluded. They describe attention or source provenance, not identity kind.

## Evaluation Before Full Classification

Start with a small stratified calibration set spanning multi-source accounts,
single-source accounts, graph-only endpoints, missing bios, obvious people,
obvious organizations, and ambiguous handles. Refine the policy on that set,
then evaluate on a separate untouched set.

Report per-kind precision/recall, a confusion matrix, and the unknown rate.
Overall accuracy alone is misleading because people will likely dominate.

## Later Track/Reject Curation

Tracking is a separate decision and may use richer attention and relevance
evidence. Store automated decisions with rationale, model/policy version,
timestamp, and token cost. Human corrections are durable overrides and must
survive recomputation.
