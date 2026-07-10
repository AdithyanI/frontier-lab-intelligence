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

Do not collapse these into one opaque decision. An entity means "observed
identity," not "approved for tracking." The current database still implements
`lab` / `person` / `unknown`; Adi accepted `person` / `organization` / `unsure`
for the first independent kind-classification pass on 2026-07-10. The database
migration and later organization-channel merging remain separate work.

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
- Synchronization was idempotent before the one-time Adi-following cleanup. The
  cleanup is intentionally not reusable importer policy, so rerunning that
  import or a later channel sync can rematerialize removed source rows.
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

## First Kind Classifier: Accepted Contract

The first pass classifies every current unknown X-backed cluster independently.
It does not merge channels, infer affiliation, or decide relevance. The runner
already owns the database/entity identifier and should send only
identity-bearing profile fields:

```json
{
  "handle": "example",
  "display_name": "Example Name",
  "bio": "Observed profile biography or null",
  "profile_url": "https://x.com/example"
}
```

The Structured Outputs response must contain exactly two fields:

```json
{
  "classification": "person",
  "reason": "The account name and biography describe an individual researcher."
}
```

Allowed classifications are exactly:

- `person`: one individual human.
- `organization`: a company, lab, nonprofit, team, product, publication,
  community, or project rather than one individual.
- `unsure`: evidence is missing, contradictory, or too weak.

No probability or confidence score is wanted. The model must not repeat the
handle, entity ID, model name, prompt version, timestamp, or cost. Deterministic
runner code joins the response to the input entity and stores operational
metadata outside the model response.

Digg rank, PageRank, follower count, list membership, and Digg role are
excluded from structural kind judgment. They describe attention or source
provenance, not whether an actor is a person or organization. Profile URLs,
linked sites, and a small recent-post sample may later enrich only `unsure`
cases. The first pass uses existing profile fields.

Use OpenAI Structured Outputs through the shared LiteLLM proxy. Runtime reads
`LLM_API_ENDPOINT` and `LLM_API_KEY` from the existing machine-secret setup;
this repo does not consume direct Azure OpenAI credentials.

## Evaluation Before Full Classification

Start with a small varied calibration set spanning multi-source accounts,
single-source accounts, graph-only endpoints, missing bios, obvious people,
obvious organizations, brands, and ambiguous handles. Refine the policy on
that bounded set before running all 2,956 initial unknown entities.

Report result counts, invalid-output/retry counts, abstention coverage, token
use, cost, and qualitative errors. A later merge evaluator must optimize for
identity-link precision because false merges are more damaging than temporarily
leaving two clusters separate. Overall classification accuracy alone is
misleading because people will likely dominate.

## Later Track/Reject Curation

Tracking is a separate decision and may use richer attention and relevance
evidence. Store automated decisions with rationale, model/policy version,
timestamp, and token cost. Human corrections are durable overrides and must
survive recomputation.
