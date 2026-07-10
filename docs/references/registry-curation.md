# Registry Curation Contract

Exact contract for turning observed channels into entities and later teaching
an agent to classify and curate them. The architecture overview shows the
system shape; this reference records the implementation rules.

## Separate Questions

1. **Identity resolution:** which channels belong to the same real-world
   identity?
2. **Structural kind:** is the resolved actor a person or organization, or must
   the system abstain?
3. **Role:** is an organization a frontier model lab, evaluator, investor, or
   something else the product needs to distinguish?
4. **Curation:** should Frontier Lab Intelligence `track` or `reject` it?

Do not collapse these into one opaque decision. One orchestrated agent may run
the steps, but it must emit each decision separately. An entity means "observed
identity," not "approved for tracking." The current database still implements
`lab` / `person` / `unknown`; the person/organization/unresolved contract below
is the proposed replacement and must be frozen before migration.

## Channel-To-Entity Lifecycle

```text
channel import
  -> normalize channel key
  -> link to a known entity when identity is certain
  -> otherwise create one provisional entity with kind=unknown
  -> later resolver links an existing actor, creates person/organization,
     or abstains
  -> later role policy may designate an organization as a frontier model lab
  -> later curation policy proposes track/reject
  -> human corrections override automated proposals durably
```

Current invariants:

- Every channel belongs to exactly one entity after `fli channels sync`.
- Synchronization is idempotent: a no-op rerun keeps the same database hash.
- Currently allowed database kinds are only `lab`, `person`, and `unknown`.
- A seeded lab may claim a channel from a one-channel provisional unknown.
- A resolved entity's channel cannot be silently reassigned.
- Missing identity evidence stays missing; uncertainty stays `unknown`.

## Current Implemented Universe

After the 2026-07-10 Adi-following snapshot, the corpus contains:

| Kind | Entities |
| --- | ---: |
| lab | 10 |
| person | 0 |
| unknown | 2,956 |
| **total** | **2,966** |

Those provisional clusters own all 2,998 channels. The difference is the 32 additional
official website, GitHub, arXiv, and blog channels already linked to labs.
The legacy graph has one additional non-Registry account: `@adithyan_ai`, kept
only as the source node for its 638 retained outgoing-follow edges.

## Resolution Agent: Proposed Input Contract

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

It should return one structured action:

```json
{
  "action": "link_existing_entity | create_person | create_organization | leave_unresolved",
  "existing_entity_id": null,
  "confidence": 0.0,
  "rationale": "Short evidence-based explanation",
  "evidence_urls": [],
  "policy_version": "registry-resolution-v1"
}
```

Digg rank, PageRank, follower count, list membership, and Digg role are
excluded from structural kind judgment. They describe attention or source
provenance, not whether an actor is a person or organization. Profile URLs,
linked sites, and a small recent-post sample may be fetched as identity evidence
when name/bio/channel fields are insufficient.

## Evaluation Before Full Classification

Start with a small stratified calibration set spanning multi-source accounts,
single-source accounts, graph-only endpoints, missing bios, obvious people,
obvious organizations, and ambiguous handles. Refine the policy on that set,
then evaluate on a separate untouched set.

Report person/organization precision and recall, abstention coverage, a
confusion matrix, and identity-link precision. False merges are more damaging
than temporarily leaving two clusters unresolved. Overall accuracy alone is
misleading because people will likely dominate.

## Later Track/Reject Curation

Tracking is a separate decision and may use richer attention and relevance
evidence. Store automated decisions with rationale, model/policy version,
timestamp, and token cost. Human corrections are durable overrides and must
survive recomputation.
