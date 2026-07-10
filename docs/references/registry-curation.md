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
  -> later curation policy proposes track/reject
  -> human corrections override automated proposals durably
```

Current invariants:

- Every channel belongs to exactly one entity after `fli channels sync`.
- Synchronization was idempotent before the one-time Adi-following cleanup. The
  cleanup is intentionally not reusable importer policy, so rerunning that
  import or a later channel sync can rematerialize removed source rows.
- Database kinds are `person`, `organization`, `unsure`, and provisional
  `unknown`; there are currently zero unknown entities.
- A seeded lab may claim a channel from a one-channel provisional unknown.
- A resolved entity's channel cannot be silently reassigned.
- Missing identity evidence stays missing; classifier abstention is `unsure`.

## Current Implemented Universe

After the 2026-07-10 Adi-following snapshot, the corpus contains:

| Kind | Entities |
| --- | ---: |
| person | 2,607 |
| organization | 180 (including 10 seeded labs) |
| unsure | 137 |
| unknown | 0 |
| **total** | **2,924** |

Those clusters own all 2,956 channels. The difference is the 32 additional
official website, GitHub, arXiv, and blog channels already linked to labs.
The legacy graph has one additional non-Registry account: `@adithyan_ai`, kept
only as the source node for its 638 retained outgoing-follow edges.

On 2026-07-10, Adi explicitly removed the stray `@philschmid` candidate and
all entities whose verified X follower count was below 1,000. The six initially
missing smol.ai profiles were then checked through TwitterAPI.io: three valid
above-floor accounts remain, `@akhaliq` and `@lucidrains` were removed at 40
and 395 followers, and stale `@danhendrycks` was resolved to the existing
canonical `@hendrycks` entity. All 137 remaining unsure entities have a stored
follower count of at least 1,000. This was a one-time destructive corpus
cleanup, not a reusable relevance model or a change to structural-kind
semantics.

`@adithyan_ai` remains an internal graph-source account for 638 retained edges,
but has no Registry channel or entity. Channel sync mirrors only accounts with
source facts, so this graph-only account cannot rematerialize as `unknown`.

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

## Later Track/Reject Curation

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

## Azure Web-Search Enrichment Compatibility

Microsoft's current Azure OpenAI Responses documentation supports hosted
agentic `web_search` for GPT-4 and later. The shared LiteLLM Luna route points
to the Azure OpenAI v1/preview endpoint and advertises web search, tool choice,
function calling, and response schemas. A tagged 2026-07-10 smoke through
LiteLLM proved the exact combined contract: Luna-medium performed two searches
and one page open, returned 12 source URLs, and completed the strict
`classification` + `reason` schema for `@jack`. The request used 8,693 input
and 279 output tokens and LiteLLM reported `$0.010367`.

This proves transport/tool compatibility, not evidence quality. The smoke
found the correct person but consulted several weak secondary domains. The
production enrichment policy should prefer stored recent tweets and official
or first-party identity sources, use domain controls where useful, and reserve
open-web search for cases that remain unresolved. Azure's hosted search uses
Grounding with Bing, incurs separate tool costs, and sends search data outside
the Azure compliance and geo boundary under Microsoft's documented terms.

The bounded runner is implemented as `fli entity-kinds enrich --limit N`.
It reads only entities whose canonical kind is currently `unsure`, requires at
least one observable hosted search action, returns the same strict
`classification` + `reason` output, and stages the result in
`entity_kind_web_enrichments`. `actions_json` records search/open/find actions;
`sources_json` deduplicates consulted URLs and merges citation titles/state.
Run/model/prompt/input hashes, tokens, errors, LiteLLM tags, local estimates,
and proxy-reported cost use the existing classifier provenance machinery.
Every completed entity commits immediately and exact matching results skip on
resume. The runner never updates `entities.kind`; no batch execution or
promotion policy has been accepted yet.
