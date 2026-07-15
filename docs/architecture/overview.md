# Architecture Overview

Living map of Frontier Lab Intelligence. Update this file when the system
shape changes: new pipeline stage, schema boundary, source class, or module.

Current system: the Registry, immutable trusted-following snapshot, X evidence
store, exact event projection, rank-first Feed view, keep/drop triage, and
canonical artifact library are implemented and inspectable. Audience Insights
v2 now runs two independent audience contracts over one immutable evidence and
application-owned citation core, with rank-blind item review, ID-only daily
editing, separate publication audit, immutable disqualification sidecars, and
an explicit production reconciliation boundary. The active boundary is
freezing the last chronological runs and materializing the canonical
two-audience/nine-day manifest/report pair required by the production read
model; external delivery is deferred. See
[`docs/STATUS.md`](../STATUS.md) for the conceptual handoff and current
checkpoint counts; this document explains implementation shape rather than
project status.

The Registry retains the relevance-reviewed universe. Rejected is a
reason-bearing curation state, not a structural kind. The `labs` table remains
internal source/seed provenance because its rows are not an exhaustive lab
classification; it is not exposed as a Registry kind, badge, count, or filter.
Reviewed organization consolidation and coverage are manifest-driven,
preflighted, transactional, idempotent, and audit-recorded.

The retired Digg edge plane survives only as offline historical evidence. The
live ranking evidence comes from a frozen Registry-cohort outgoing-follow
snapshot; entity overlap is the accepted inspectable ranking feature and
personalized PageRank remains diagnostic. Raw X provider evidence is immutable,
exact quote/retweet/reply envelopes are cutoff-correct, and current Registry
curation is overlaid at read time. Triage and canonical artifact storage are
derived, replayable stages. Extraction consumes accepted first-party X
evidence directly and may join canonical artifact text as optional
strengthening; it never mutates upstream evidence. Rare primary-source
recovery is explicit rather than synthetic: `artifact_event_supplement` binds
one human-reviewed official document to one exact frozen kept event and its
triage hashes, while the ordinary artifact candidate ledger remains derived
only from observed source links.
Exact human name/kind corrections are separately versioned in
`data/registry/entity-overrides.json` and recorded in
`entity_override_audit`; they never rewrite model-classification provenance.

Product relevance is a separate gate after structural kind. The reusable
`registry-relevance-v1` prompt and strict schema run one entity per
Terra-high Responses request with required hosted web search; follower count is
not an input. Results and consulted sources remain review artifacts with no
canonical write path. Approved removals are versioned in
`data/registry/relevance-removals.csv` and
applied only through `fli registry apply-relevance-removals`. The command
preflights the complete manifest, protects seeded labs, merge canonicals,
rejections, multi-channel identities, and graph participants, then removes each
approved one-account identity in one transaction. It supports dry-run and
idempotent replay; it does not turn model output directly into deletion.

The candidate-admission boundary is implemented in
`fli.registry_evaluation`. Its v3 contract receives a public X profile, up to
20 recent authored posts, and—when the source bio is missing—a separately
grounded identity context. It returns two independent
dimensions: `kind` (`person | organization | unsure`) and
`registry_decision` (`keep | remove | review`), each with its own reason.
Application code may later map `keep` to active state and `remove` to a
reason-bearing rejection; the model recommendation itself is not stored state.
Hosted `web_search` is
available with automatic tool choice and may search the open web when the local
evidence is insufficient; a response with no search is valid. The model output
does not mutate canonical state. Search actions and sources remain operational
metadata outside the four-field decision schema.

Manual candidate intake is the application-owned mutation path over that
boundary. `POST /api/registry/intake` and the inline Registry control accept an
X profile in `screen` or `direct` mode. `screen` materializes current profile
evidence, applies the follower/protected-account gates, runs the combined v3
evaluator over up to 20 authored posts, and maps `keep` to active state while
mapping `remove | review` to a reason-bearing rejection. `direct` bypasses the
relevance and follower decisions but still fetches the source, runs the
canonical structural-kind lifecycle, requires a human reason, and preserves
the protected-account collection gate. Existing active handles return before
provider or model client construction. Every accepted, rejected, existing, or
failed attempt is recorded in `entity_registry_intake_audit`, including model
telemetry when a call occurs. The demo does not add feature-specific
authentication; the write route will inherit the planned whole-site access
boundary.

`fli.identity_contexts` supplies the missing-bio stage. It runs required hosted
web research against the exact X identity, stores current role, organization,
durable contributions, relevance summary, consulted sources, usage, and cost
in the resumable run database, and never rewrites the source profile bio. The
final evaluator may still use optional web search. This separates observed
profile data from research-derived context while preventing a blank bio or a
20-post sample from being treated as the person's complete career.

The combined evaluator keeps one versioned 1,024+ token instruction prefix
ahead of per-entity evidence and uses the same stable 64-shard
`prompt_cache_key` convention as the relevance audit. It records both
`cached_tokens` and GPT-5.6 `cache_write_tokens`. The full GPT-5.4-mini run
observed 13.60M cached tokens across 19.88M input tokens (68.38%), while a
same-evidence Luna-high comparison again observed zero cache reads. Cache
behavior is therefore model/deployment-specific and always measured rather
than assumed. That comparison predates Azure's 2026-07-13 Responses cache fix.
The current shared adapter explicitly requests 24-hour retention for GPT-5.6
on the Azure-backed LiteLLM route; a fresh 64-envelope Luna-medium triage run
observed 103,936 cached tokens across 168,022 input tokens. Historical run
telemetry remains unchanged.

Every bulk run has its own ignored, resumable SQLite artifact under
`data/derived/registry-evaluation/`. It freezes the cohort, prompt/schema
hashes, exact evidence bundle, response ID, output, usage, proxy cost, web
actions, sources, and any derived identity context. A filtered comparison run
can reuse selected completed results' exact evidence without another
X-provider request; comparisons never overwrite their source run. Applying a
decision remains a separate curation step: the final 2026-07-12 cleanup used
the intersection of a v3 `remove` recommendation and bottom-decile trusted
follow support, then wrote a reversible, reason-bearing Registry rejection.

`fli.llm_responses` is the shared provider-normalization boundary for these
Responses calls. It extracts only final message text, tolerates nullable blocks
from translated responses, owns stable prompt-cache sharding and LiteLLM cost
header parsing, supplies the Azure-compatible GPT-5.6 cache-retention adapter,
and normalizes hosted-search actions and cited URLs. Luna is the default
efficient model for the structured triage, extraction, and Registry boundaries;
triage and extraction use medium reasoning, while grounded identity and
Registry evaluation use high. The durable routing and evaluation evidence live
in `docs/references/model-routing.md`.
Claude-native web search uses `tool_choice=auto` so the model can finish after
searching; the audit still rejects any response with no observed search action.

Recent X content is local-first and queryable rather than a transient API
bundle. `data/raw/x/x-content.db` preserves exact successful TwitterAPI.io JSON
responses, normalizes the latest known value of every observed post into
`x_post`, and appends every distinct provider observation to the immutable
`x_post_observation` ledger. The first normalized value was backfilled as an
observation before later refreshes could update `x_post`. Ordered
`post_bundle` membership still reconstructs an exact 20-post model input, while
date-complete Feed rebuilds select immutable observations rather than mutable
latest rows.
`fli.db` remains the compact tracked identity/channel Registry; the larger,
changing X-content database stays ignored and can later move to object storage
or Parquet without changing bundle identity.

The product-facing Feed is a separate, rebuildable read model over that raw
evidence. `fli.signal_feed` materializes complete UTC calendar days under the
`signal-feed-v8` contract into `data/derived/signal-feed/feed.db`. Starting from
the selected top-level observations, it recursively follows every embedded
quote/retweet payload it can render, preserves the exact immutable `raw_json`
and hash of every direct or embedded post in the Feed snapshot, and records the
full relation closure. Every post and relation also records when, and through
which direct wrapper, it first became observable. A later rich wrapper can add
new immutable history without leaking its embedded content or edges into an
earlier daily cutoff. Provider-declared target IDs with no captured payload
remain opaque `feed_anchor` rows instead of being discarded; multiple wrappers
can therefore meet at a shared missing target without inventing text or an
author. Pure retweet wrappers collapse into their referenced target; quote
posts remain authored evidence and also point at the quoted target. A run pins
the UTC range, selection contract, and ordered fingerprint of every selected
observation. Re-running unchanged evidence reuses the same content-addressed
run ID.

`fli.web.feed` deliberately joins the current Registry at read time rather than
copying curation state into the derived database. Rejected authors disappear
from the next response, and rejected amplifiers stop contributing, while the
raw and historical normalized evidence remains unchanged. Each canonical
Registry entity votes at most once and cannot amplify its own post. The
provisional daily score, implemented by the versioned `attention-v1.1`
contract, is an inspectable ordering aid—not an insight, importance, or quality
judgment. It combines day-relative percentiles for tracked amplification (55%),
author network support (25%), and public engagement (20%). Tracked amplification
is breadth: every distinct active canonical entity contributes
one flat vote, independent of its network-support position. The originator's own
entity-overlap support is the separate 25% component; public interactions are
log-scaled. This avoids multiplying amplifier prominence into the same signal
while keeping every input visible for later evaluation. The same API also exposes
chronological and public-engagement orderings. The Feed presents only the
stable daily score rank across all evidence for the selected day (`#1`, `#2`,
...). Audit filters and search only hide rows; they never restart the ranking.
A click reveals the underlying daily score, raw inputs, within-day percentiles,
weights, and limitations. Grouped evidence carries the exact member post and
components that produced its peak daily score so the disclosure never explains
the wrong root post.

`fli.signal_events` is a separate content-addressed projection over one frozen
Feed run. The `signal-events-v3` / `exact-structural-v5-provider-edges` contract
joins only provider-declared quote/retweet targets and reply parents. A shared
conversation ID is not itself a grouping edge. Renderable posts and opaque
provider anchors participate in
the same structural component, so wrappers around an uncaptured original still
form one envelope. Canonical event IDs derive from a provider-qualified terminal
post or opaque provider target—not the selected presentation root—so
they remain stable across rebuilds of the same structural evidence. The Event
store persists the multi-post components, members, links, anchors, and per-day
membership. `signal_publication` is the single explicit pointer to the validated
Event run and matching Feed run; readers never infer "live" from whichever run
was created most recently.

`fli.web.events` turns that published structure into cutoff-correct daily
projections. A selected day includes only evidence both published and first
disclosed through that UTC cutoff; its visible links obey the same boundary.
A continuing event keeps its stable identity and cumulative prior
context, while `day_member_count`, `prior_context_count`, `is_new_on_day`, and
`previous_activity_day` distinguish that day's delta from history. The date
strip reports envelope counts produced by this projection, not raw evidence-post
counts. Registry curation remains dynamic: rejected renderable posts are
removed, the surviving graph is re-componentized, rejected wrappers cannot
bridge otherwise separate components, and opaque provider anchors continue to
connect legitimate survivors. Unconsumed posts remain one-member envelopes.

The weekly projection rolls the same daily revisions through a seven-day
window. When a later exact relationship merges components that were separate
earlier in the week, it supersedes every overlapping earlier state by
provider-qualified visible membership. This retains one cumulative envelope,
its active-day list, and peak daily score/engagement without double-counting
the same post or retaining a superseded event revision.

The React `/evidence/feed` surface is one evidence browser rather than separate post,
group, or lane modes. It offers complete-day navigation, search, the three
transparent sort orders, score inputs, raw engagement, and direct X
provenance. Each envelope renders the root once, then exact replies in
parent-first order, unique quote commentary, and a compact retweeter trace.
Captured parents always precede their descendants and sibling branches are
chronological. A reply whose exact parent is absent stays as a visibly
unparented branch rather than being attached by conversation or timing
inference. LLM relevance, semantic grouping, summaries, and cited insights
remain later stages after this deterministic layer is audited.

`fli.insight_triage` is the first implemented cited-insight boundary after the
deterministic Feed. It receives a frozen top-ranked envelope but deliberately
does not receive its daily score, engagement, followers, Registry rank, or
amplifier prominence. One `gpt-5.4-mini`/medium Responses call through LiteLLM
returns only the envelope-level `keep | drop` decision and one concise reason.
The stable 1,024+ token instructions precede the variable envelope. Bulk runs
use deterministic cache-key shards with at most one in-flight request per key,
parallelize across keys, and persist completed responses through one SQLite
writer so interrupted work resumes without repeating successful calls.
Provider-supplied article/card title, preview, and
URL already stored in raw X JSON are joined before triage so link-only primary
artifacts are not mistaken for empty posts; no artifact body is fetched or
interpreted at this stage. `fli.insight_triage_runs` freezes the cohort,
prompt/schema hashes, exact input, response, usage, cache reads, LiteLLM tags,
proxy cost, and explicit failures in a resumable derived SQLite run. Kept
envelopes continue whole to cited extraction and may join resolved artifact
text when available. Category/event type is deliberately absent from both the
routing gate and the first extraction contract until a proven consumer needs
it.

The Feed exposes these completed decisions as an audit projection, not as a
replacement ranking. `fli.web.triage` selects the newest fully completed run
for the requested UTC day. A decision is displayed only when both its stable
`event_id` and `snapshot_content_sha256` match the currently projected
envelope; a decision for an older or differently connected snapshot cannot
leak onto new evidence. Completed work is reusable only when the event ID,
snapshot hash, and exact rendered-input hash all match, so repaired grouping
reuses unchanged envelopes without reusing stale judgments.
Daily score, recency, and engagement still sort the same evidence independently;
`keep`, `drop`, and `not evaluated` are separate filters with counts computed
before pagination. The projection reads the run's existing
`(decision, current_rank, event_id)` and `(status, current_rank, event_id)`
indexes and never mutates the triage or Feed stores.

`fli.artifacts`, `fli.artifact_urls`, and `fli.evidence_lineage` implement a
parallel deterministic enrichment boundary for corrected kept envelopes. They
admit outbound URLs only from the root X post or replies by the same stable X
account in the same conversation. Other authors' replies, quotes, retweets, and
nested links remain visible reactions but cannot create artifact associations
or enter Insight evidence. Conversation identity spans locally missing
intermediate replies without relaxing the author boundary. Eligible URLs are
bound to the post that actually contains them and indexed without fetching the
whole corpus.
Ordinary
X status/profile/media URLs remain source evidence; X long-form Articles are
the explicit artifact exception. Conservative `artifact-url-v1`
canonicalization removes only known tracking noise, retains every observed and
expanded form as an alias, and never merges different URLs solely by content
hash. Stable source-kind/provider/external-ID/snapshot observations preserve
provenance independently of mutable event projections.

`fli.artifact_fetch` freezes a bounded, stratified top-ranked cohort and
fetches it through a one-worker public-network safety boundary. Manual
redirects, DNS checks, robots, size/time limits, append-only attempts, explicit
retryable/terminal errors, and content-addressed raw/text snapshots make the
stage resumable and replayable. HTML uses Trafilatura, PDFs use pypdf, and
client-rendered error shells remain failures rather than false clean text. The
replaceable `jina-reader-v1` fallback handles only ordinary public HTML pages
that failed the native boundary; its separate fetch policy and raw JSON
snapshot preserve provider provenance, while X, LinkedIn, YouTube, hosted
forms, robots-denied pages, authentication, and paywalls remain deferred. The
2026-07-15 primary-author rebuild indexes 1,334 canonical artifacts and 1,432
source observations from 1,897 decisions, with zero foreign-author or
wrong-conversation lineage violations across the stored Feed. It retains 32
still-eligible successful snapshots, including 22 X Articles. Broad crawling,
RSS/GitHub adapters and cited-insight generation remain deferred. The web
layer now exposes the live catalog through read-only `/api/artifacts/dates`
and `/api/artifacts` projections plus a minimal `/evidence/artifacts` index. The shared
Feed-style navigator selects the UTC publication day of the X observation
(never mutable retrieval time); within a day, one row per canonical artifact
inherits the best originating Feed rank, with source time shown separately and
retrieval state inside expandable provenance rather than in the collapsed index
row. Expanded provenance deep-links through the stored source event ID to the
exact Feed envelope; the Feed remains the evidence workspace and owns the
onward source link. This is a frozen ordering input carried from Feed, not a new artifact
score. The same artifact
may appear on multiple days when the network independently links it again. This
is an operator inspection surface, not a second Feed or an insight product.

`fli.cited_insight_runs` now freezes the first five accepted envelopes into a
separate resumable extraction run. `insight-v1.1` gives the model the complete
accepted first-party X envelope plus any available artifact text, but asks it
to return only one claim, three compact analytical fields, and one verbatim
supporting quote. The application—not the model—binds that quote to the frozen
X post or artifact identity and URL. A result whose quote is not an exact
substring is retained as a failed calibration row and never reaches the
read-only `/api/insights` projection. The first proof published four verified
insights from five candidates; its one rejected citation, usage, prompt-cache
reads, proxy cost, and raw output remain auditable in the run database.

Audience Insights v2 replaces the compromise audience framing with two
independent products over the same frozen evidence and application-owned
citation binder. `fli.audience_insight_runs` gives Investment and AI
Engineering separate extraction prompts, schemas, run databases, cache
namespaces, pre-editor item filters, daily editors, and day-set gates. The
editor can select only runner-owned IDs that passed every item-review
dimension; it cannot rewrite a claim or citation. Feed rank chooses a bounded
candidate cohort but is absent from extraction, review, and editorial inputs.

`fli.audience_insight_publication_audit` is a second, isolated calibration
boundary so the pre-editor filter is not reused as proof of its own quality. A
separate SQLite audit freezes every published selection and a deterministic
small sample of the highest-Feed-ranked filter rejects. Its Luna-high prompt,
strict schema, cache namespace, request tags, attempts, and telemetry are
independent. The auditor sees sanitized evidence and item content under an
opaque ID, never rank, selection state, prior judgments/rationale, or editor
metadata. It reports zero-tolerance citation/attribution failures, the 80%
selected usefulness/actionability/specificity threshold, and false-negative
reject counts. Duplicate and padding judgments remain exclusively in the
separate day-set gate.

A source run and its audit are never rewritten. An adjacent immutable
publication-finalization sidecar may only make the release boundary stricter:
it either removes exact audit-failed selected IDs, or records an exact senior
editorial disqualification after the independent audit has passed. The latter
binds a review ID, reviewer, enumerated reason, and rationale to exact active
candidate IDs. Neither mode can promote a reject, substitute content, or
reorder survivors. Every read revalidates the source selection and audit
bindings; canonical reconciliation additionally binds the sidecar bytes. A
senior editorial veto changes the released projection but retains that
mechanically valid item in duplicate-suppression history, so later editors do
not rediscover the same weak framing and already-frozen downstream runs do not
need to be rewritten. An audit disqualification remains absent from both the
released projection and later history.

New chronological runs receive that history through explicit command inputs,
not a “newest directory” guess. Repeated `--prior-run-db` values must name one
internally passed run per earlier day, in strictly increasing order, for the
same audience. Before any model client is created, the runner validates the
entire audience/day/order chain, then revalidates each source's exact adjacent
`publication-audit-v1/audit.db` and optional immutable finalization. The
resolved mode, exact sources, projection modes, item count, and history hash are
returned in command JSON. `--history-mode auto` remains an explicit
non-production escape hatch; `--history-mode none` is reserved for an explicit
history origin. Omitting both a mode and exact prior databases is an error.

`fli.audience_insight_production_reconciliation` then provides the production
closeout boundary. Its strict explicit manifest
names every required audience/day, exact source database, adjacent audit,
expected base selection count, optional finalization, and—when available—the
exact X Article artifact cohort. The Article origin union is also explicit:
ordinary items must derive from the declared production-run event IDs, while
the two lower-rank census Articles are admitted only through exact sample IDs
in the frozen recall database. That recall origin binds the complete
`recall_run` / `recall_sample` / `recall_replacement` ledger hash, revalidates
the sample protocol, selection hash, packet identity, accepted artifact-event
edge, and source artifact database, and rejects overlap with run-derived
events. It is therefore not a general artifact superset escape hatch. The
reconciler discovers no runs by recency or directory scan, opens all SQLite
inputs read-only, fails closed on missing or duplicate cells,
immutable-contract drift, unresolved false negatives, incomplete stage state,
unknown proxy cost, or nonterminal bound Articles, and emits deterministic
per-run and aggregate count, token, cache, cost, audit-hash, and
finalization-hash evidence. A numeric provider-reported zero cost remains
valid; NULL remains unknown and requires a superseding run. An Article cohort
not explicitly bound is reported as unbound rather than silently inferred.

Production publication is deliberately stricter than local fixture discovery.
`fli.web.insights` accepts only the adjacent
`production-reconciliation-v2/manifest.json` and `report.json` pair. On every
read it evaluates the manifest again, requires the stored report to equal the
fresh canonical report byte-for-byte, then revalidates each exact run/audit/
finalization projection before returning a date or item. A missing pair,
partial replacement, contract or telemetry drift, source/audit hash change,
unbound false negative, path escape, or X Article snapshot drift produces an
unavailable product rather than a best-effort fallback. An explicit `run_root`
is reserved for isolated fixture/test discovery and is not a production
compatibility path.

The Insights product also exposes an explicit pre-editor comparison view. Its
`/api/insights/extracted*` read model opens the existing per-run `insights.db`
files read-only, chooses the most complete production extraction for each
audience/day, and returns only citation-bound `candidate_item` insights ordered
by their original Feed rank. This view stops before item review, daily editing,
publication audit, and reconciliation; the UI labels it “Feed-ranked” and keeps
the fail-closed canonical publication projection as the separate “Reviewed
brief” view. No extraction data is copied or regenerated for this comparison.

The web layer treats these SQLite stores as versioned read models. Feed/Event
and Ranking responses are cached in-process against main-database plus WAL
version tokens, so a Registry change or rebuilt derived run invalidates the
affected cache. Exact-envelope assembly is cached once per complete Feed day;
search, sort, pagination, and triage filters are then applied over that shared
projection instead of rebuilding its SQLite joins. The SPA deduplicates and
prefetches complete Feed days and
lazy-mounts closed evidence trees. Registry list reads stay uncached in the
browser because their indexed queries are already fast and curation freshness
matters more than another cache.

## Stack

One Python codebase, isolated SQLite stores, one React SPA served by the API.

| Layer | Choice | Why |
| --- | --- | --- |
| Language/package | Python 3.13, `src/fli/` | Most rubric weight is data, LLM, scoring, and ingestion work. |
| Database | SQLite | A compact tracked Registry plus isolated raw and derived stores keep identity, immutable evidence, and rebuildable read models inspectable. |
| Web UI | React + Vite + TS SPA over a FastAPI JSON API; sigma.js for graph viz | Decided 2026-07-08: the UI doubles as our data-inspection surface (graph + candidate review), which server-rendered Jinja2 handles poorly. Same stack as Adi's other apps. Identity: `DESIGN.md` cobalt/brass, not adi-design. |
| Pipeline | CLI subcommands | Each stage should be independently runnable, testable, and demoable. |
| Scheduling | Simple cron/loop later | Scheduled ingestion does not need queue infrastructure yet. |

Rejected for now: Next.js/SSR frameworks (a static Vite SPA on a JSON API is
enough), Streamlit/Gradio toy-dashboard shape, and Dobby/personal-memory
architecture inside this product repo. Jinja2 server-rendered pages were the
original choice and are being retired in favor of the SPA.

## System pipeline

```mermaid
flowchart LR
    subgraph sources [Sources]
        XLISTS[X list memberships]
        XFOLLOW[Registry following snapshot<br/>2.83M immutable edges]
        XPOSTS[Stored X posts<br/>raw responses + normalized bundles]
        BLOGS[Lab blogs / RSS]
        ARXIV[arXiv]
        GH[GitHub releases]
    end

    REG[(Registry<br/>labs + people)]
    ING[Ingestion<br/>pull · dedup · cluster]
    EXT[Extraction<br/>LLM → structured insights]
    SCO[Scoring<br/>dimensions + validation]
    DEL[Delivery<br/>digests · alerts]
    UI[Web UI<br/>FastAPI + React SPA]
    OBS[(Immutable X observations<br/>provider payload history)]
    FEED[Feed v8<br/>posts · disclosure-dated relation closure · opaque anchors]
    EVENTS[Events v3<br/>stable exact envelopes · cutoff projections]
    PUB[Published read model<br/>explicit validated run pointer]
    READ[Registry-aware projections<br/>daily delta · weekly dedupe · triage]
    ART[(Artifact catalog<br/>canonical URLs · aliases · source provenance)]
    FETCH[Bounded artifact fetch<br/>raw body · title · clean text]

    XLISTS --> REG
    XFOLLOW --> REG
    XPOSTS --> OBS --> FEED --> EVENTS --> PUB --> READ
    READ -->|accepted envelopes + first-party X| EXT
    READ -->|outbound links| ART --> FETCH
    FETCH -.->|optional primary evidence| EXT
    REG -->|current active/rejected state| READ
    REG -->|who to watch| ING
    BLOGS & ARXIV & GH --> ING
    ING --> ART
    EXT --> SCO
    SCO --> DEL
    REG -.-> UI
    READ -.-> UI
    SCO -.-> UI
    DEL -.-> UI
    ING -.->|discovered names| REG
```

Target stages:

1. **Registry:** labs, people, identities, affiliations, provenance.
2. **Ingestion:** public source pulls, dedup, clustering, freshness.
3. **Extraction:** structured/cited insights from accepted X evidence,
   optionally strengthened by fetched artifacts.
4. **Scoring:** visible dimensions plus validation, not an arbitrary weighted sum.
5. **Delivery:** persona digests, alerts, reviewable UI, PDF/export later.

## Signal Funnel

```mermaid
flowchart TD
    S0[Source scoping<br/>curated source list]
    S1[Exact grouping<br/>replies · quotes · retweets]
    S2[Daily-score ordering<br/>transparent candidate generation]
    S3[Keep / drop triage<br/>sole relevance + substance gate]
    S4[Cited extraction<br/>X evidence + optional artifacts]
    S5[Persona framing<br/>investment vs AI team]
    OUT1[Alert tier]
    OUT2[1-page digest]
    OUT3[Full appendix]
    NONE[Nothing significant today]

    S0 --> S1 --> S2 --> S3 --> S4 --> S5
    S5 --> OUT1 & OUT2 & OUT3
    S4 --> NONE
```

Judgment is meant to live in two visible places: source selection and scoring
rubrics. Everything else should be mechanical and testable.

Design principles borrowed from prior art:

- Curated source lists and denominator disclosure from smol.ai/AI News.
- "Nothing significant today" as a trust-preserving output.
- Machine proposes, human disposes from Techmeme-style workflows.
- Reason-for-inclusion labels instead of one opaque score.
- Time decay and noise dampeners for freshness.
- Dated affiliations because people moves are themselves a signal.

## Current Data

Implemented raw table:

```text
raw_items(id, source, lab, external_id, fetched_at, payload)
```

Current file artifacts:

```text
data/fli.db                         # raw evidence SQLite corpus
data/digg/rankings.csv              # offline Digg comparison baseline only
data/following/cohorts/*.json       # frozen broad collection membership
data/raw/following/*/snapshot.db    # ignored local raw pages + fresh edges
data/raw/x/x-content.db             # ignored raw X responses + normalized posts/bundles
data/derived/following/*/analysis.db # ignored recomputable rankings + identity map
data/derived/signal-feed/feed.db     # ignored signal-feed-v8 snapshots + discovery-cutoff relation closure
data/derived/signal-events/events.db # ignored signal-events-v3 projection + live pointer
data/derived/x-daily-collection.db   # ignored frozen-cohort collection manifests
docs/references/digg-ranking-baseline.md
```

Current source-import commands:

```text
fli sources import-x-list --list-id <x-list-id> --source <source_key>
fli sources import-x-following --username <x-handle> --source <source_key>
fli following-snapshot freeze-cohort --cohort-id <id> --output <path>
fli following-snapshot init --snapshot-id <id> --cohort <path>
fli following-snapshot status|validate --snapshot-db <path>
fli following-snapshot finalize --snapshot-db <path>
fli following-snapshot collect --snapshot-db <path> --handle <x-handle>
fli following-snapshot collect --snapshot-db <path> --all --profiles-only
fli following-snapshot collect --snapshot-db <path> --all --workers 20
fli following-ranking overlap --snapshot-db <path> --registry-db data/fli.db
fli x-daily-collection plan --start-day YYYY-MM-DD --end-day YYYY-MM-DD --no-input --json
fli x-daily-collection execute --start-day YYYY-MM-DD --end-day YYYY-MM-DD --no-input --json
fli x-daily-collection status --run-id <id> --no-input --json
fli signal-feed refresh --days 7 [--through YYYY-MM-DD]
fli signal-events refresh --publish
```

The first provider implementation is TwitterAPI.io. It reads its API key from
`~/.secrets/twitterapi-io/api-key`, mirrors X accounts into channels, emits one
JSON object, and pages until the provider says there is no next page. List
imports write membership facts. Following imports atomically replace one
complete snapshot with `followed_by` facts plus directed `follows` edges. Neither
command classifies imported accounts or approves them for tracking.

The broad PageRank collection no longer uses that legacy whole-import path.
`fli.following_snapshots` freezes the active Registry cohort into tracked JSON
and initializes one isolated, ignored `following-snapshot-v1` SQLite database.
Its page cache is keyed by snapshot, stable source X ID, and request cursor;
each transaction stores canonical raw provider JSON before normalized accounts
and directed source→target edges. Source state distinguishes pending,
in-progress, complete, protected, missing, unavailable, and failed. Identical
page retries are no-ops, conflicting retries fail closed, and completed
snapshots are immutable. `status`, `validate`, and `finalize` are JSON-first,
non-interactive inspection/lifecycle commands. Initialization itself makes no
external request. Ranking will require an explicit snapshot database rather
than reading `data/fli.db` edges.

A new cohort may initialize as an incremental child of a finalized snapshot.
Parent reuse intersects only on stable source X ID and copies terminal source
state, raw profiles/pages, normalized accounts, and edges into the child's own
database. New cohort sources remain pending. `snapshot_lineage` records the
parent path/checksum and exact copy counts, while inherited evidence preserves
its original observation time. The child therefore has one explicit frozen
membership denominator but can contain honestly disclosed mixed observation
dates. Verified conference profile responses can be seeded from their raw
cache before collection so a graph refresh does not pay for or overwrite the
same provider evidence twice.

Bounded collection is now implemented. Every paid run requires an explicit
handle, source limit, or `--all`. Source profiles are cached before following
pages, so profile and cursor evidence both survive interruption. Profile-only
scans and full collection may use parallel source workers behind one
request-start QPS limiter; exactly one worker owns each source, so its pages
remain sequential and cursor-safe. The first live calibration paused
`@karpathy` after one 200-edge page, resumed without repeating that profile or
page, and completed at 1,108 edges across six pages. The all-source profile
scan cached 2,228 current follower/following counts, marked nine protected and
three missing sources, and completed 12 zero-following sources without a paid
following request. The authorized full run completed all 2,206 remaining
accessible sources at 20 workers / 9 QPS with zero crawl failures. The immutable
snapshot contains 13,409 raw pages, 463,180 distinct target accounts, and
2,456,305 directed edges; its best-available provider-cost estimate is
`$27.81218`. The tracked manifest binds those facts to the local 2.0 GB database
checksum.

The 2026-07-14 incremental child freezes 2,564 stable-ID Registry sources,
reuses 2,212 sources from that parent, and collects only the 352-source delta.
It contains 15,470 raw pages, 557,363 target accounts, and 2,832,858 directed
edges. Of 2,564 frozen accounts, 2,558 are complete, three missing, and three
protected. Evidence retains its original July 11 or July 14 observation time;
the child is not presented as a same-day crawl. Marginal profile/following work
is estimated at `$4.37070`, while the `$32.06420` cumulative evidence estimate
includes inherited rows.

The first derived rankings are now live. `fli.following_rankings` materializes a
snapshot- and Registry-checksummed active/rejected/unknown X-ID map in an
ignored `analysis.db`, then ranks every discovered account by the number of
distinct complete active Registry entities that follow it; multiple X channels
owned by one organization contribute at most one vote. The command can read
only the frozen snapshot edge table and an authorizer-limited set of Registry
identity tables; it cannot read legacy `data/fli.db.graph_edges`. The current
run reconciles 2,558 complete active source accounts, 2,521 voting entities,
2,832,858 raw eligible edges, 2,831,995 deduplicated entity-target votes,
557,363 ranked accounts, and 2,524 active X-addressable Registry targets,
including 38 zero-support targets. It also materializes entity-union support;
multiple target channels are unioned and self-support is excluded. Raw
followers are display evidence, not an overlap input. Equal support counts
share one dense score rank and use a separate deterministic account display
position only in the global discovery view.

The materialization is rebuilt once after a Registry curation batch so ranks
and denominators stay internally consistent. It is intentionally not recomputed
inside an interactive page request. Automatic background refresh is deferred
unless curation becomes frequent enough to justify the added machinery.

An experimental 30-source personalized PageRank also runs over the same edge
boundary and stores its direct comparison in the derived database. It
converged correctly, but only 37.9% of its top 100 overlaps the simple baseline;
the reviewed seeds and their immediate neighbors dominate because most target
nodes have no collected outgoing edges. PageRank therefore remains diagnostic,
while entity-overlap advances to human top-k evaluation as the default ranking.

Known data facts:

- `fli fetch` landed 1,599 raw items from lab blogs/sitemap, arXiv, and
  GitHub releases.
- The active graph has zero edges. The 360,667 Digg edges, derived PageRank,
  graph-only candidates, raw edge artifacts, and exploratory personal
  following snapshot were removed on 2026-07-10.
- The Registry retains 2,630 classified entities: 2,431 active people, 160
  active organizations, zero active unsure, and 39 reason-bearing rejections.
  The 2,718 channels include official X, website, GitHub, and blog channels
  consolidated into stable real-world organizations. The approved relevance
  manifest contains 689 exact one-X removals. The final organization pass
  applies Adi's temporary 10,000-follower floor; lower-reach organizations may
  be rediscovered later through trusted-follow PageRank evidence.
- Official AI Engineer World's Fair 2026 and 2024 snapshots contribute 423
  unique X-addressable people. Canonical storage keeps one newest role, bio,
  and listed-company label per person; an organization/affiliation is created
  only when it resolves to an existing channel-backed entity or an official
  conference website. The final boundary has 96 resolved conference
  organizations and 186 affiliations; 195 channel-less labels were pruned as
  Registry clutter. Repeated conference history and non-X enrichment remain
  raw-only. Provider reconciliation and the frozen-following audit leave 407
  active identities, 13 explicit missing/suspended rejections, and three
  protected-account rejections. Conference presence affects neither rank nor
  vote weight. Posting inactivity is not a rejection gate: a dormant but
  observable expert can still contribute useful outgoing-follow evidence.
- Every account carries a neutral `registry_bootstrap.retained_candidate`
  marker. The 1,853 accounts actually observed through Digg also carry one
  `digg_bootstrap.candidate_origin` value (`ranked`, `graph_node`, or both).
  These are provenance only—not graph edges or ranking inputs.
- `data/digg/rankings.csv` retains the frozen 1,000-account Digg ranking only
  for later comparison. It is not imported into the active database.
- `fli sources import-x-list --list-id 1585430245762441216 --source
  ai_high_signal` imported 609 AI High Signal X-list members via
  TwitterAPI.io; 230 were already in the Digg bootstrap and 379 were new
  versus Digg.
- smol.ai AINews `prefPeople` imported 31 unique X handles from its pinned
  public GitHub source. Twenty-three already existed and eight new accounts
  were added; 21 overlap AI High Signal, 17 overlap Digg, and 17 occur in all
  three sources.

### Current Schema (as built, not the target sketch)

This is what actually exists in `data/fli.db` today. The `accounts`,
`account_source_facts`, and empty `graph_edges` tables back X source imports;
the product model is `entities`, `channels`, `entity_channels`, and
`channel_observations`.
The classifier adds separate run, classification, and error tables. Registry
rejections remain separate from structural kind in
`entity_registry_rejections`; applied identity merges are recorded in
`entity_merge_audit`, and reviewed name/kind corrections in
`entity_override_audit`.
`raw_items` is an unconnected bootstrap table. Row counts as of this writing
are in parentheses.

The Registry read model exposes nullable `followers_count` as the sum of the
latest stored X-account follower counts owned by each entity, plus a stable
`reach_rank` across all active Registry entities. All, People, and Organizations
show this as **X reach**: the ordinal is primary and the compact combined total
remains secondary scale evidence (`#24 · 3.3M`). The default API order is
`sort=reach&direction=asc`; reversing it shows the deepest observed ranks first.
Search, kind filters, and pagination do not redefine the comparison universe.
Missing observations remain null and sort last. This is a public-reach proxy,
not graph evidence or a canonical importance score.

The Network workspace presents Ranking and Registry as related but distinct
subviews. Registry may also sort on entity-level Network support materialized
with the latest immutable entity-overlap run. The target is one real-world
Registry entity: distinct complete active Registry entities following any X
account mapped to that target count once, and self-support is excluded. The UI
leads with `support_count / eligible_source_entity_count`, then shows a dense
tie-aware ordinal among active X-addressable Registry entities. Snapshot date
and denominator stay visible. Ranking alone retains the deterministic global
account position for candidate discovery. This does not mutate Registry
identity, combine public reach into support, or create an importance score;
active identities with a stable X channel receive an explicit support row,
including zero support. Identities without a stable X mapping remain null and
sort last.

```mermaid
erDiagram
    RAW_ITEMS {
        int id PK
        string source "blog | arxiv | github"
        string lab
        string external_id
        string fetched_at
        string payload "JSON"
    }
    ACCOUNTS {
        int id PK
        string platform "x"
        string handle
        string display_name
        string x_id
        int followers_count
    }
    ACCOUNT_SOURCE_FACTS {
        int id PK
        int account_id FK
        string source "ai_high_signal | smol_ai"
        string fact "list_member"
        string value
    }
    GRAPH_EDGES {
        int id PK
        int from_account_id FK
        int to_account_id FK
        string relationship "follows"
        string source
    }
    LABS {
        int id PK
        string slug
        string name
        string status "frontier | emerging"
        int x_account_id FK "legacy link"
    }
    ENTITIES {
        int id PK
        string kind "person | organization | unsure | unknown (provisional)"
        string slug
        string name
    }
    CHANNELS {
        int id PK
        string kind "x | github | blog | website"
        string key
        string url
    }
    ENTITY_CHANNELS {
        int entity_id FK
        int channel_id FK
        string relationship "official | identity | candidate"
        float confidence
    }
    CHANNEL_OBSERVATIONS {
        int id PK
        int channel_id FK
        string source "ai_high_signal | smol_ai | x_profile"
        string metric "list_member | followers_count"
        string value
        string observed_at
    }
    ENTITY_KIND_CLASSIFICATION_RUNS {
        int id PK
        string model
        string reasoning_effort
        string prompt_version
        string status
        int input_tokens
        int output_tokens
        float estimated_cost_usd
        float reported_cost_usd
        string request_tags "JSON array"
    }
    ENTITY_KIND_CLASSIFICATIONS {
        int entity_id FK
        string input_sha256
        string classification "person | organization | unsure"
        string reason
        string prompt_version
        string reasoning_effort
        float reported_cost_usd
        int run_id FK
    }
    ENTITY_KIND_CLASSIFICATION_ERRORS {
        int id PK
        int run_id FK
        int entity_id FK
        string error_type
        int terminal
    }
    ENTITY_REGISTRY_REJECTIONS {
        int entity_id PK,FK
        string reason_code
        string reason
        string source
        string evidence_url
        string rejected_at
    }
    ENTITY_KIND_WEB_ENRICHMENTS {
        int entity_id FK
        string input_sha256
        string classification "person | organization | unsure"
        string reason
        string prompt_version "entity-kind-web-v1"
        string actions_json
        string sources_json
        float reported_cost_usd
        int run_id FK
    }
    ENTITY_SOURCE_FACTS {
        int entity_id FK
        string source
        string fact
        string value
        string observed_at
        string evidence_url
    }
    ENTITY_AFFILIATIONS {
        int person_entity_id FK
        int organization_entity_id FK
        string relationship
        string role_title
        string source
        string observed_at
        string evidence_url
    }

    ACCOUNTS ||--o{ ACCOUNT_SOURCE_FACTS : "has (5,419)"
    ACCOUNTS ||--o{ GRAPH_EDGES : "from_account_id"
    ACCOUNTS ||--o{ GRAPH_EDGES : "to_account_id (0 current)"
    LABS }o--|| ACCOUNTS : "x_account_id (legacy, optional)"
    LABS ||--|| ENTITIES : "internal seed provenance by slug"
    ENTITIES ||--o{ ENTITY_CHANNELS : "has (2,718)"
    CHANNELS ||--|| ENTITY_CHANNELS : resolves_to
    CHANNELS ||--o{ CHANNEL_OBSERVATIONS : "observed_as (11,599)"
    ENTITIES ||--o{ ENTITY_SOURCE_FACTS : "evidenced facts (1,763)"
    ENTITIES ||--o{ ENTITY_AFFILIATIONS : "person role (186)"
    ENTITIES ||--o{ ENTITY_AFFILIATIONS : "organization affiliation (186)"
    ENTITY_KIND_CLASSIFICATION_RUNS ||--o{ ENTITY_KIND_CLASSIFICATIONS : "produced (2,300)"
    ENTITY_KIND_CLASSIFICATION_RUNS ||--o{ ENTITY_KIND_CLASSIFICATION_ERRORS : "records (0)"
    ENTITY_KIND_CLASSIFICATION_RUNS ||--o{ ENTITY_KIND_WEB_ENRICHMENTS : "stages (1)"
    ENTITIES ||--o{ ENTITY_KIND_CLASSIFICATIONS : "classified independently"
    ENTITIES ||--o{ ENTITY_KIND_WEB_ENRICHMENTS : "enriched independently"
    ENTITIES ||--o| ENTITY_REGISTRY_REJECTIONS : "may be rejected with reason"
    ENTITIES ||--o{ ENTITY_MERGE_AUDIT : "canonical identity records merges"
    ENTITIES ||--o{ ENTITY_OVERRIDE_AUDIT : "records reviewed corrections"
```

Table row counts: `raw_items` 1,599, `accounts` 2,600,
`account_source_facts` 5,419, `graph_edges` 0, `labs` 10,
`entities` 2,630, `channels` 2,718, `entity_channels` 2,718,
`channel_observations` 11,599, `entity_source_facts` 1,763,
`entity_affiliations` 186, `entity_kind_classification_runs` 10,
`entity_kind_classifications` 2,300, `entity_kind_web_enrichments` 1,
`entity_kind_classification_errors` 0, `entity_registry_rejections` 36, and
`entity_merge_audit` 29, and `entity_override_audit` 1.

Note `raw_items` has no foreign keys into the rest of the schema yet — it is
the as-fetched evidence corpus, not joined to entities/channels until
ingestion/extraction lands. The `accounts` / `account_source_facts` /
`graph_edges` trio is the legacy bootstrap X import layer described above; it
still backs the graph viz but is being superseded by `entities` / `channels`
/ `entity_channels` / `channel_observations` as the product's canonical model.

## Entity / Channel Model

The case prompt asks for labs and individuals as first-class entities. The
identity model resolves them across X, GitHub, websites, and official feeds;
arXiv papers remain source documents for later extraction, not owned identity
channels. The model is therefore:

```text
entities              # who: OpenAI, Anthropic, Andrej Karpathy
channels              # where: @openai, OpenAI blog, github.com/openai
entity_channels       # evidence/confidence that a channel belongs to an entity
channel_observations  # measured/source-specific facts about a channel over time
entity_source_facts   # source-bound role, bio, and admission provenance
entity_affiliations   # dated person-to-organization claims with role + source
```

Entity is identity, not endorsement. A channel that cannot yet be resolved
creates a provisional `unknown` entity. The canonical structural vocabulary is
`person`, `organization`, and `unsure`; `unknown` is only the pre-classification
lifecycle state. The 10 seeded rows in `labs` remain internal source provenance
and do not create a public subtype. Source-specific role and bio claims live in
`entity_source_facts`; dated person-to-organization claims live in
`entity_affiliations`. Neither changes entity kind, voting weight, or rank.
Conference imports consolidate those claims to the newest available non-empty
fact and one affiliation per person; the immutable raw snapshots retain the
complete event history without turning repeat appearances into product data.
Rejection remains a separate curation state. An explicit protected-account flag is the first
implemented rejection gate; broader relevance curation remains later.

An entity may own multiple channels of the same kind. SpaceX owns the
independent X channels `@spacex` and `@SpaceXAI`; the reviewed batches add
21 product/developer/subgroup accounts to eleven canonical organizations. Each X account
keeps its own backing account row, profile observations, and source facts; only
the redundant organization entity is removed. A manifest reason and evidence
URL are retained in `entity_merge_audit`. Complete preflight plus one
`BEGIN IMMEDIATE` transaction make late validation failures and dry runs
all-or-nothing. The one-owner index on `entity_channels.channel_id` still
prevents any channel from belonging to two entities.

```mermaid
flowchart TD
    C[Channel arrives]
    R{Known identity?}
    E[Link existing entity]
    U[Create unknown entity]
    P{Public account?}
    X[Rejected<br/>reason retained]
    K[Kind classifier<br/>person · organization · unsure]
    D[Broader relevance curation later]

    C --> R
    R -->|yes| E --> P
    R -->|no or uncertain| U --> P
    P -->|protected| X
    P -->|public| K
    K --> D
```

Exact rules and the accepted classifier contract live in
`docs/references/registry-curation.md`.

Rule of thumb:

```text
Entity = who
Channel = where we observe them
Entity channel = proof that this where belongs to that who
Observation = what we saw there at a time
```

Current implemented tables:

```text
entities(id, kind, slug, name, notes, created_at, updated_at)
channels(id, kind, key, label, url, first_seen_at, last_seen_at)
entity_channels(entity_id, channel_id, relationship, confidence, evidence_url, notes)
channel_observations(channel_id, source, metric, value, observed_at, evidence_url)
```

The `accounts`, `account_source_facts`, and `graph_edges` tables are source
import backing, not the product model. X accounts are mirrored into
`channels(kind='x')`. Neutral Digg/bootstrap origin markers remain, but no
Digg rank, score, edge, or PageRank observations remain.

### Active Classifier Boundary

The first LLM pass operates on each current unknown X-backed cluster
independently. Deterministic code supplies handle, display name, bio, and
profile URL. Structured model output contains exactly:

```json
{
  "classification": "person | organization | unsure",
  "reason": "Short identity-based explanation"
}
```

The model does not return identifiers, probability, model name, prompt version,
timestamp, or cost. The runner owns that metadata, resumability, concurrency,
and database association. It calls OpenAI models through the shared LiteLLM
proxy using `LLM_API_ENDPOINT` and `LLM_API_KEY`; the app does not use direct
Azure OpenAI credentials. Attention observations such as follower count,
PageRank, Digg rank, and list membership are excluded from this structural
classification.

Every request carries stable LiteLLM tags for app, pipeline, job, scope,
prompt, and run. The runner stores its official-rate estimate separately from
LiteLLM's reported response cost. The post-upgrade LiteLLM 1.91.1 verification
reconciled both values with the persisted spend log, including the tagged token
counts; proxy spend logs are the operational source of truth for billed usage.
The full Luna-medium prompt-v2 result set covers all 2,956 initial unknown
entities: 2,639 person, 172 organization, and 145 unsure. The atomic promotion
step validates the current input hash and accepted model/effort/prompt contract
before updating canonical kinds. The Registry exposes the stored reason in the
detail view. Seeded lab provenance remains internal and is not displayed.

`fli entity-kinds onboard --handle @name` is the canonical single-account
entrypoint. It fetches the provider profile, applies the 1,000-follower floor,
persists eligible profile evidence, and rejects protected accounts before any
model call. Public accounts enter one sequential Responses chain: profile;
then up to 20 authored posts after abstention; then one required hosted-web
turn, capped at four tool calls, after a second abstention. Every turn keeps the
same strict `classification` + `reason` schema and continues through
`previous_response_id`.

The runner commits the final decision and promotion immediately. Hosted-web
actions and deduplicated consulted/cited sources are stored separately in
`entity_kind_web_enrichments`; they do not expand the model-output schema.
Exact prompt/model results resume without another paid call. The batch
`fli entity-kinds enrich --limit N` path reuses the same staged lifecycle for
current abstentions.

Identity resolution may attach several X channels to one organization. A
person is expected to have one primary X account in most cases, but the data
model permits multiple channels for both people and organizations. The first
consolidation keeps SpaceX as the canonical entity, renames the stable former
`@xai` account to its current `@SpaceXAI` handle, and attaches it beside
`@spacex`; no historical-handle record is exposed.

## X Graph Source Direction

The product database's graph remains intentionally empty. The completed fresh
graph source is the outgoing-follow snapshot from the frozen,
relevance-screened Registry cohort,
where each source account is accessible—not followers of popular accounts and
not the offline Digg comparison ranking. Collection membership is not itself a
claim that every account deserves equal trust.

```text
frozen Registry X cohort
  -> GET following for each accessible X user
  -> snapshot.edge(source_x_id, target_x_id)
  -> trusted-follow overlap baseline
  -> personalized PageRank from a smaller reviewed trust subset
  -> people candidates for curation
```

Why this direction:

- Followers of a large account are mostly audience and spam.
- Following lists from frontier researchers/labs are a higher-signal attention
  graph.
- Costs stay bounded because the source cohort is frozen and each edge has a
  source snapshot/evidence URL.
- Third-party X data APIs can be evaluated later, but the official API shape is
  the cleanest story for a case-study product.

Do not import the Digg comparison ranking or combine it with the new graph.
Compare outputs only after the fresh graph has been evaluated independently.
The 2,231-account active collection cohort, the smaller personalization subset, and
the ranked candidate output must remain separate inspectable artifacts.
Large raw pages and normalized edges live in an ignored per-snapshot SQLite
file rather than the Git-tracked product database. Git retains a small manifest
with cohort, completeness, cost, checksum, and result paths. See
`docs/references/following-snapshot-storage.md`.

Examples:

```text
Entity: OpenAI
Channels: @openai, openai.com/news/rss.xml, github.com/openai

Entity: Andrej Karpathy (future curation pass)
Channels: @karpathy, github.com/karpathy
```

## Target Data Model Sketch

This is a hypothesis to test against real candidate evidence, not a locked
schema.

```mermaid
erDiagram
    ENTITY {
        string id PK
        string kind "person | organization | unknown (target)"
        string slug
        string name
    }
    CHANNEL {
        string id PK
        string kind "x | github | blog | website"
        string key
        string url
    }
    ENTITY_CHANNEL {
        string entity_id FK
        string channel_id FK
        string relationship "official | identity | candidate"
        float confidence
        string evidence_url
    }
    CHANNEL_OBSERVATION {
        string channel_id FK
        string source
        string metric
        string value
        datetime observed_at
    }
    AFFILIATION {
        string person_id FK
        string lab_id FK
        date start_date
        date end_date "null = current"
        string provenance
    }
    DOCUMENT {
        string id PK
        string source_url
        string cluster_id
        datetime published_at
    }
    INSIGHT {
        string id PK
        string document_id FK
        string attributed_to FK
        string claim
        string evidence_quote
    }
    SCORE {
        string insight_id FK
        string dimension
        int value
        string rationale
    }

    ENTITY ||--o{ ENTITY_CHANNEL : has
    CHANNEL ||--o{ ENTITY_CHANNEL : resolves_to
    CHANNEL ||--o{ CHANNEL_OBSERVATION : observed_as
    ENTITY ||--o{ AFFILIATION : "person side"
    ENTITY ||--o{ INSIGHT : "attributed to"
    DOCUMENT ||--o{ INSIGHT : yields
    INSIGHT ||--o{ SCORE : scored
```

Scoring dimensions under consideration: novelty, materiality, credibility,
actionability per persona, corroboration, and freshness. The combination into
a ranking should be checked against human/hindsight labels before becoming a
final score.

## Module Status

| Module | Status |
| --- | --- |
| `fli.cli` | `--version`, `web`, `fetch`, `labs`, `channels`, `registry`, `sources`, `entity-kinds`, `relevance-audit` |
| `fli.store` | raw `raw_items` SQLite layer |
| `fli.graph` | minimal account/source-fact/edge backing schema; no active importer or ranker; active edge count is zero |
| `fli.channels` | canonical entity/channel model; `fli channels sync\|summary` |
| `fli.labs` | internal curated source seed (10 historical rows); seeds official channels but does not define a public Registry kind/subtype |
| `fli.fetch` | raw fetch spike for blogs/sitemap, arXiv, GitHub releases |
| `fli.sources` | machine-readable TwitterAPI.io profile, timeline, X-list, and single-source outgoing-follow adapter; provenance only, no classification |
| `fli.conference_sources` | manifest-driven official conference snapshots, exact-X identity reconciliation, lean current role/bio/affiliation import, resumable raw profile hydration, unavailable-account rejection, and following-snapshot profile seeding |
| `fli.x_content` | immutable raw provider responses and `x_post_observation` history, plus mutable latest-post convenience rows and exact post bundles |
| `fli.x_daily_collection` | frozen-cohort, date-complete, cache-aware and resumable Registry X timeline collection with JSON-first plan/execute/status commands |
| `fli.signal_feed` | content-addressed `signal-feed-v8` snapshots with recursive embedded relation closure, first-disclosure provenance, opaque provider anchors, and immutable per-post raw JSON |
| `fli.signal_events` | `signal-events-v3` exact structural components with provider-qualified identity, disclosure-dated links, and an explicit `signal_publication` pointer |
| `fli.web.events` | Registry-aware cutoff-correct daily/delta and deduplicated weekly envelope projections; date counts are envelope counts cached as one structural-version summary and warmed when the always-on web process starts |
| `fli.insight_triage_runs` | resumable snapshot/input-hash-bound envelope triage with exact reuse and cached-token/cost telemetry |
| `fli.artifacts` | shared canonical artifact identity, aliases, provenance, disclosures, immutable fetch attempts, and content-addressed clean text |
| `fli.cited_insights` / `fli.cited_insight_runs` | historical minimal `insight-v1.1` proof: frozen five-record run, resumability, usage/cost telemetry, and application-owned exact citation binding |
| `fli.audience_insights` / `fli.audience_insight_runs` | independent Investment and AI Engineering extraction/schema/cache contracts, exact citation binding, resumable attempt ledgers, all-five-pass item filtering, ID-only daily editing, day-set review, and audited-history inputs |
| `fli.audience_insight_publication_audit` | isolated rank-blind selected/reject audit, hash-bound false-negative adjudication, and immutable publication-disqualification sidecars |
| `fli.audience_insight_recall` | frozen 73-packet lower-rank/X-Article/drop census with audience-specific extraction/review and exact final-set comparison fields |
| `fli.audience_insight_production_reconciliation` | strict explicit 18-cell manifest evaluator binding contracts, source runs, adjacent audits, finalizations, chronological history, complete telemetry, and the exact X Article cohort into one deterministic report |
| `fli.following_snapshots` | immutable, resumable raw-page/account/edge storage for one frozen outgoing-follow cohort, with checksum-bound parent reuse for unchanged stable-ID sources |
| `fli.following_rankings` | deterministic account discovery ordering plus entity-union Network support (source and target both one entity/one vote, self excluded), with experimental personalized PageRank retained for comparison |
| `fli.web` | JSON API + built SPA host; Network keeps Registry entity support and Ranking discovery distinct, Feed/Event readers share the newest completed analysis selection, and Insights publishes only runs proven by the fresh canonical reconciliation pair; source in `frontend/` |
| `fli.registry` | channel ownership invariant, provisional unknown materialization, and canonical Registry read model |
| `fli.relevance` | read-only, web-grounded Registry relevance audit using the versioned `registry-relevance-v1` prompt; emits cited review artifacts and cannot mutate canonical data |
| `fli.llm_responses` | shared normalization of OpenAI-compatible Responses text, hosted-search actions, and cited sources across native and translated providers |
| Audience insight extraction | split audience contracts calibrated and production runs materialized chronologically; failed/superseded attempts remain immutable provenance |
| Insight evaluation | independent item/day review, adjacent publication audit, exact false-negative adjudication, bounded recall widening, and deterministic production reconciliation implemented |
| Insights UI | one Feed-ranked audience surface remains implemented; generated Insight data was explicitly reset pending a simpler schema and prompt |
| Local alert outbox | required package proof; no external sending without approval |

## Current Build Order

1. Finish the corrected chronological production suffix without allowing an
   unaudited day into later editorial history.
2. Bind the exact 18 audience/day source runs, adjacent audits, finalizations,
   and 22 X Article snapshots into the final manifest; write its canonical
   deterministic report only after fresh evaluation passes.
3. Build the SPA and prove Investment and AI Engineering date/item/empty states,
   exact citations, navigation, accessibility, and console cleanliness against
   the live reconciled read model.
4. Reconcile exact counts, token/cache/cost telemetry, quality results, and
   limitations; pass repo checks and archive Audience Insights v2.
5. Resume briefing, alert/outbox, reviewer landing, final report, and package
   smoke work as a successor submission project before 2026-07-20.
