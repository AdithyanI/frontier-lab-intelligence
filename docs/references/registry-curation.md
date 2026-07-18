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
provenance and is not exposed as an exhaustive Registry category. Explicit
organization-channel consolidation remains separate from kind classification.

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

After the relevance and organization-identity cleanup, the corpus contains:

| Kind | Entities |
| --- | ---: |
| person (active) | 2,431 |
| organization | 160 |
| unsure (active) | 0 |
| rejected | 39 |
| unknown | 0 |
| **total** | **2,630** |

These are the 2026-07-18 dated checkpoint totals; query `/api/registry` for the
live read contract. Multiple official X, website, GitHub,
and blog channels may resolve to one stable real-world organization. The
eight affiliation-search arXiv
queries were removed from the identity channel model; all 137 fetched arXiv
documents remain in `raw_items` for later extraction work.
The current immutable following snapshot and accepted entity-support view are
documented in `docs/STATUS.md`. A node's accepted
follower-floor and structural-kind decisions survive removal of its discovery
edge.

The following profile scan identified nine additional people whose only
observed channel is protected X. Adi placed them in the existing Rejected view
under `protected_x_no_public_channel`: Albert Webson, Alane Suhr, David
Warde-Farley, Gwern, Heng Ji, Maike Osborne, Neal Khosla, Noah A. Smith, and S.
Osindero. They are excluded from active Registry counts, source collection,
ranking inputs, and candidate output. `clear_rejection` is the explicit path to
restore one later if a usable public channel appears.

The final 2026-07-12 person cleanup added 10 reversible
`off_mandate_low_trust_support` rejections. Each required both a v3 `remove`
decision and bottom-decile support in the accepted entity-overlap snapshot;
the entities and their evidence remain stored. Exact results and retained
counterexamples are recorded in
`docs/projects/archive/trusted-following-ranking/resources/registry-evaluation-v3-final-cleanup.md`.

Relevance cleanup is an explicit, human-approved boundary rather than a
direct model action. Its 689 rows live in
`data/registry/relevance-removals.csv`; the transactional Registry command
preflights identity, channel ownership, lab status, merge status, rejection
state, and graph participation before deleting an entity, its sole X channel,
and its backing account. The accepted set contains 614 people and 75
organizations. Eighteen organization rows override an earlier model keep:
one dormant source and 17 organizations below Adi's temporary 10,000-follower
floor. The original audit evidence and restoration notes remain in the active
trusted-following project.

Every account has a neutral `registry_bootstrap.retained_candidate` fact with
value `post_1000_follower_floor_and_kind_classification`. Accounts actually
seen through the old Digg source also have one non-scoring
`digg_bootstrap.candidate_origin` fact: `ranked`, `graph_node`, or
`ranked_and_graph_node`. These facts explain why a node exists; they must never
be interpreted as a rank or trusted-follow edge.

## Reviewed Organization Consolidation

False merges are more damaging than temporary duplicates. Organization
consolidation therefore uses the reviewed
`data/registry/organization-groups.json` manifest, never fuzzy matching or an
LLM decision. `fli registry apply-organization-groups --dry-run` resolves and
validates the entire manifest before mutation, uses one transaction, and may be
rerun idempotently. Every applied decision records the removed entity, reason,
source, evidence URL, and timestamp in `entity_merge_audit`; accounts,
channels, observations, and source facts remain intact.

The reviewed batches consolidated 21 redundant entities into eleven
high-confidence organizations, in addition to the earlier SpaceX proof:

| Canonical organization | Additional X channels |
| --- | --- |
| Anthropic | `@claudeai`, `@claudedevs` |
| OpenAI | `@openaidevs` |
| Mistral AI | `@mistraldevs` |
| Anysphere | `@cursor_ai` |
| Vercel | `@nextjs`, `@v0`, `@aisdk` |
| Hugging Face | `@gradio`, `@diffuserslib` |
| fal | `@editwithfal` |
| Thinking Machines Lab | `@tinkerapi` |
| Google | `@googleai`, `@geminiapp`, `@googlelabs`, `@googleaistudio`, `@googleresearch`, `@julesagent`, `@stitchbygoogle` |
| Stanford AI Lab | `@stanfordnlp` |
| Reka | `@moonvalley` |

Google DeepMind remains first-class because the assignment evaluates frontier
labs, not only legal parents. Manus remains separate from Meta because the
acquisition was ordered unwound. Stable Diffusion remains separate from
Stability AI because current product affiliation is certain but account-level
corporate control was not strong enough for this precision-first wave. Ought
and Elicit remain separate because Elicit became an independent public-benefit
corporation. Independent communities such as `@claude_code` are not absorbed
into the corresponding vendor.

Major-company coverage is a separate, explicit correction layer. The reviewed
`data/registry/organization-coverage.json` manifest pins one immutable
following snapshot by id and checksum, declares stable parent organizations,
and lists exact identity/product/research channels with first-party evidence.
`fli registry apply-organization-coverage --snapshot <snapshot.db> --dry-run`
preflights the entire batch before a transaction imports only reviewed cached
profiles, attaches channels, and performs named merges. It never imports raw
following pages or graph edges. The first applied batch created or normalized
Microsoft, Amazon, Apple, Ai2, ByteDance, Tencent, Meta, Alibaba, Baidu,
Databricks, Moonshot AI, Kuaishou, NVIDIA, AMD, and Intel. Google remains the
stable parent for Google product channels; Google DeepMind remains a deliberate
first-class lab exception. NVIDIA owns the reviewed `@nvidia`, `@nvidiaai`, and
`@nvidiaaiinfra` X channels; the latter's verified profile resolves to NVIDIA's
first-party data-center site.

Exact human corrections that do not merge or delete an identity live in
`data/registry/entity-overrides.json` and apply through
`fli registry apply-entity-overrides`. Complete preflight checks the expected
name and kind before one transaction updates the entity; old/new values,
reason, source, evidence URL, and timestamp are stored in
`entity_override_audit`. The active override manifest corrects
`@shahules786` to the person Shahul ES. NVIDIA and Meta now use the stronger
parent/channel coverage contract rather than one-off renames. Temporary Task
Master and Argmax display-name corrections were omitted from replay because
both entities are removed by the later 10,000-follower boundary.

A bounded TwitterAPI.io activity audit recorded the latest timeline date for
127 organization X channels and 2,122 person X channels using a 2024-07-11
cutoff. Inactivity is channel evidence, not an automatic person deletion:
Papers with Code was removed because both its X channel and underlying service
are dormant, while inactive but important researchers remain available and
should simply not be treated as current post sources. The organization audit
also found that low reach is not the same as low relevance; Adi nevertheless
approved removing the 17 remaining sub-10,000 organizations as a temporary
first-PageRank boundary, with restoration through later graph evidence.

The Registry's All, People, and Organizations views use one transparent,
stable public-reach ordering: sum the latest stored follower counts across
every X channel owned by the entity, then assign its ordinal once across all
active Registry entities. The table labels this **X reach** and renders the
ordinal first with compact magnitude beside it (`#24 · 3.3M`). Search, kind
filters, and pagination never restart the rank. This is a reach proxy, not
PageRank, a structural-kind input, or the final trusted-seed decision. Handles
remain searchable and available in the detail card but are hidden from these
ranked tables to keep rows calm. Missing follower observations display as an em
dash and sort last. Rejected retains its review-oriented reason column.

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

## Manual X Profile Intake

The Network workspace exposes Add Profile as its third explicit subview. Its
API is `POST /api/registry/intake` with an X profile plus one
of two explicit modes:

- `screen` fetches and stores the profile, rejects protected or sub-1,000
  accounts mechanically, otherwise fetches up to 20 authored posts and runs
  `registry-evaluation-v3`. `keep` becomes active; `remove` and `review` remain
  reversible, reason-bearing rejections.
- `direct` requires an operator reason and bypasses the follower/relevance
  decision. It still runs the canonical kind lifecycle and never admits a
  protected profile whose public evidence cannot be collected.

Exact-handle lookup happens before client construction. An already-active
profile therefore returns its existing entity with zero provider and model
calls, preventing duplicates and spend. `entity_registry_intake_audit` records
the requested mode, human reason, outcome, evaluator reasons, model contract,
usage, reported cost, failure, and timestamps. The current case-study demo has
no feature-level password; the route is intended to sit behind the same
whole-site access boundary as the rest of the product when that is enabled.
