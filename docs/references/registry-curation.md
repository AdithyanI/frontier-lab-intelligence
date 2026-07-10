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
identity," not "approved for tracking." The canonical structural kinds are
`person`, `organization`, and `unsure`; `unknown` remains only the provisional
lifecycle state for a newly observed, unclassified entity. Labs are not a
fourth kind. The existing curated `labs` table remains internal seed/source
provenance and is not exposed as an exhaustive Registry category. Later
organization-channel merging remains separate.

## Channel-To-Entity Lifecycle

```text
channel import
  -> normalize channel key
  -> link to a known entity when identity is certain
  -> otherwise create one provisional entity with kind=unknown
  -> later resolver links an existing actor, creates person/organization,
     or abstains
  -> deterministic eligibility gates may reject before model inference
  -> later relevance curation may propose track/reject
  -> human corrections override automated proposals durably
```

Current invariants:

- Every channel belongs to exactly one entity after `fli channels sync`.
- Synchronization is idempotent for active public sources.
- Database kinds are `person`, `organization`, `unsure`, and provisional
  `unknown`; there are currently zero unknown entities.
- A seeded lab may claim a channel from a one-channel provisional unknown.
- A resolved entity's channel cannot be silently reassigned.
- Missing identity evidence stays missing; classifier abstention is `unsure`.
- A Registry rejection is stored separately from structural kind with a reason,
  source, evidence URL, and timestamp.

## Current Implemented Universe

After removing the rejected graph evidence while retaining the already
filtered and classified nodes, the active corpus contains:

| Kind | Entities |
| --- | ---: |
| person | 2,736 |
| organization | 184 (including 10 seeded labs) |
| unsure (active) | 1 |
| rejected | 3 |
| unknown | 0 |
| **total** | **2,924** |

Those clusters own all 2,956 channels. The difference is the 32 additional
official website, GitHub, arXiv, and blog channels already linked to labs.
The active graph has zero edges. Digg's 1,000-account ranking is an offline
comparison artifact and is not active Registry provenance. A node's accepted
follower-floor and structural-kind decisions survive removal of its discovery
edge.

Every account has a neutral `registry_bootstrap.retained_candidate` fact with
value `post_1000_follower_floor_and_kind_classification`. Accounts actually
seen through the old Digg source also have one non-scoring
`digg_bootstrap.candidate_origin` fact: `ranked`, `graph_node`, or
`ranked_and_graph_node`. These facts explain why a node exists; they must never
be interpreted as a rank or trusted-follow edge.

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

Classification provenance deliberately remains separate from `entities.kind`:
`entity_kind_classification_runs` owns prompt/model/token/cost metadata,
`entity_kind_classifications` owns the two-field decision joined to its input
hash and entity ID, and `entity_kind_classification_errors` owns structured
retry/terminal failures. `fli entity-kinds promote` atomically projects the
accepted model/effort/prompt results into canonical kinds only when all current
unknown inputs have matching results. The Registry joins the stored reason for
auditability. The internal `labs` seed is not surfaced as a public kind or
filter; no generic role field or role framework was introduced.

Classifier requests are tagged in LiteLLM by app, pipeline, job, scope,
prompt version, and run ID. Store the proxy-reported response cost separately
from the dated local rate snapshot, and use the persisted LiteLLM spend log as
the operational source of truth for tokens, exact spend, and tag attribution.

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

The 2026-07-10 full Luna-medium prompt-v2 pass completed with exact coverage of
the 2,956 initial unknown entities: 2,639 person (89.28%), 172 organization
(5.82%), and 145 unsure (4.91%), with zero terminal errors. Stored result usage
is 719,059 input plus 123,374 output tokens. The inference cost, including the
calibration/verification results reused by the full universe and net restart
overhead, is approximately `$1.459852`. Those results are now projected, giving
2,639 people, 182 organizations after including the 10 seeded labs, 145 unsure,
and zero unknown. Classification remains separate from merging and relevance.

## Registry Rejection And Later Relevance Curation

An explicit protected/private provider flag is now a deterministic eligibility
gate: the account is rejected before any LLM call because its public output
cannot be collected. The entity and its structural kind remain intact for
auditability. `entity_registry_rejections` stores the reason code, human-readable
reason, provider source, evidence URL, and decision time. The Registry presents
these rows in a separate Rejected view; they are excluded from active
person/organization/unsure counts.

Tracking is a separate decision and may use richer attention and relevance
evidence. Store automated decisions with rationale, model/policy version,
timestamp, and token cost. Human corrections are durable overrides and must
survive recomputation.

The leading next-step design is graph-first rather than an LLM-only judgment
from profile biographies. Pull the **following lists of a bounded trusted
watchlist**: whom a frontier researcher or lab chooses to follow is generally
cleaner attention evidence than the large, spam-prone follower audience of a
popular account. Keep graph sources with different semantics separate until a
validation set justifies combining them. PageRank should produce an attention
signal, not the final track/reject label.

All structural kinds remain eligible for this ranking, including `unsure`.
Weak identity evidence must not prevent a potentially important account from
surfacing; identity enrichment and tracking relevance remain separate.

## Canonical X-Account Classification Lifecycle

The canonical entrypoint is `fli entity-kinds onboard --handle @name`. It
fetches the TwitterAPI.io profile, enforces the 1,000-follower floor, persists
eligible profile evidence, and rejects protected accounts before inference.
Public accounts use one shared `ENTITY_KIND_INSTRUCTIONS` developer prompt.
The first Responses call supplies the profile. Only when that result is
`unsure`, the runner fetches up to 20 recent authored posts, excluding replies
and retweets, and continues with `previous_response_id`. Quote posts contribute
only the account's top-level commentary.

If the post turn remains `unsure`, one final Responses call requires hosted
`web_search`, with medium search context and at most four tool calls. It must
match the exact handle to the represented actor and prioritize first-party
identity evidence. The final turn still returns only `classification` and
`reason`; search/open/find actions plus complete consulted and cited sources
are persisted separately in `entity_kind_web_enrichments`. More tweets are not
the fallback because a second abstention usually indicates missing external
identity linkage rather than insufficient account voice.

The accepted runner now persists each final decision and promotes its canonical
kind with per-entity commits. It stores the final Response ID, evidence hash,
aggregate token usage, proxy-reported cost, and reason in the existing
classification tables. Before the profile turn it fetches the provider profile;
an explicit protected flag records a Registry rejection instead and performs
zero model calls. Responses use Azure's normal 30-day storage to support
chaining and are not explicitly deleted.

Hosted Azure web search was separately proven through LiteLLM before being
adopted as this final escalation. Deterministic authored posts remain the first
enrichment source; hosted search runs only after both cheaper identity stages
abstain. The first live canonical run promoted `@jack` from `unsure` to
`person`: the profile and 20-post turns abstained, while four bounded search
actions consulted 43 URLs and resolved the exact account. The Registry reason
is normalized to plain text; complete source URLs remain in the web-evidence
row rather than leaking into the model-output field.
