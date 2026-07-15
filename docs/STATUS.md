# System Status

Last verified: 2026-07-15

This is the conceptual handoff for Frontier Lab Intelligence. Read it before
planning across projects or changing the system direction. It explains what
the product is, what is already real, what remains unproven, and which durable
document answers each deeper question.

This file is not the execution tracker and not a chronological log. The active
project tracker owns detailed work state; the build log owns historical
submission evidence. Query that history with `scripts/build-log.py recent` or
`search` only when needed; do not load the complete artifact during handoff.

## North Star

Earn the next BIT Capital interview with one coherent, defensible, working
case study: turn public frontier-lab evidence into 3–5 excellent, checkable,
decision-useful insights for an investment team and an AI engineering team.

The product thesis is:

> A curated network can identify important frontier-AI activity early; exact
> evidence grouping, transparent routing, and primary-source citations can
> turn that activity into intelligence a human can trust.

The submission deadline is 2026-07-20. Until then, a narrow evaluated path
from evidence to cited delivery is more valuable than broader crawling, a
larger graph, or additional UI polish.

## Product Story

```text
Registry
  -> trusted X collection cohort
  -> exact quote / retweet / reply envelopes over time
  -> transparent daily-score ordering
  -> independent AI Engineering + Investment routing
  -> audience-specific surface-or-suppress Insight pass
  -> separate Investment + AI Engineering views
```

The stored-X and canonical-artifact evidence paths are implemented. The earlier
multi-stage Audience Insights v2 implementation and generated outputs were
explicitly discarded on 2026-07-15; its learnings remain archived in docs.
The successor now starts directly from ranked Feed evidence: one versioned
GPT-5.4-mini/high call makes independent AI Engineering and Investment relevance
judgments over a complete attributed evidence packet. The former model-based
keep/drop gate, its generated databases, and its live API/UI/CLI surfaces were
removed on 2026-07-15. The Feed derives `kept` only when either audience is
relevant; it is not a third judgment. A successor Insight foundation defines
two audience prompts and one small surface-or-suppress schema. Its first frozen
envelope comparison produced four valid suppressions across mini and Terra;
there is still no run database or live Insight publication.

## Where the System Stands

| Layer | Status | What is established |
| --- | --- | --- |
| Registry | Implemented, inspectable, and manually extensible | One entity can own multiple channels; structural kind and Registry admission are separate; rejected records remain reversible and reason-bearing. The Registry UI/API can now intake one X profile through the combined evidence screen or a reason-bearing direct admission, with exact-handle idempotency and durable attempt/model telemetry. The current checkpoint contains 2,630 auditable identities: 2,431 active people, 160 active channel-backed organizations, and 39 reason-bearing rejections. The lean World's Fair 2026/2024 cohort contributes 423 people; unresolved company labels stay person facts rather than fake organizations. Conference inclusion is provenance, not rank or vote weight, and inactivity alone is not a rejection gate because dormant experts can still contribute useful outgoing-follow evidence. |
| Trusted-following graph | Evaluated candidate generator | The current immutable incremental snapshot contains 2,832,858 outgoing-follow edges from 2,558 complete source accounts resolving to 2,521 voting entities. Entity-union overlap is the accepted inspectable support feature across 2,524 active X-addressable Registry targets, including 38 zero-support targets; personalized PageRank remains a diagnostic, not truth. |
| X evidence store | Implemented source boundary | Raw provider evidence is preserved locally and normalized into replayable posts and relations. X is the only implemented discovery source today. |
| Exact event projection | Implemented and regression-tested | Provider-declared evidence is projected as root-owned structural forests, not unrestricted connected components: quote/retweet reactions attach to one source, only the source author's replies extend its thread, and every member has at most one structural parent. Third-party replies remain in the Feed ledger but cannot render, import their own branch, or bridge independent roots. Daily snapshots are cutoff-correct and weekly views retain the richest stable-root revision. The current July 5–13 Feed contains 39,491 normalized posts; its published Event run contains 7,515 grouped envelopes, 28,625 members, and 21,368 links. |
| Feed + daily score | Implemented audit surface | Daily collection includes authored replies; the ledger preserves replies whose conversation root is captured, while the product projection admits only first-party continuations and treats trusted quotes/retweets as reactions. The Feed is date-filterable, shows one stable daily score rank across Audit/search filters, and explains its transparent tracked-amplification, author-support, and public-engagement inputs on demand. Registry changes affect derived views without rewriting raw evidence. |
| Canonical artifact library | Complete supported pass + operator index | Outbound primary-resource links are conservatively canonicalized, source-linked, fetched once, snapshotted, and replayable. The reply-inclusive catalog converges to 2,735 artifacts with zero lineage violations; 2,507 have usable text, including all 221 arXiv metadata/abstract records and all 167 cached X Articles. Videos remain deferred and 65 non-video pages are unavailable or retryable. One shared extraction validator rejects placeholder-dominated bodies before they become successful snapshots. |
| Feed audience routing | Current nine-day top-100 audit complete | The direct Evidence runtime returns independent AI Engineering and Investment booleans plus evidence-grounded reasons, preserves the attributed primary/artifact/reaction hierarchy, and stores exact packet/input/model/cost provenance. The complete packet remains immutable; only the model-facing view is capped at 20,000 tokens with an explicit truncation marker. The corrected July 5–13 run completed all 900 envelopes against the root-owned Event publication: 344 both, 112 Engineering-only, 141 Investment-only, and 303 neither. Thirty-eight repeated exact inputs have zero label conflicts. The publication-bound refresh freezes packets sequentially, then runs only pending model requests in bounded parallelism and prunes obsolete runs only after complete success. |
| Audience Insight generation | First one-envelope comparison complete | Separate Investment and AI Engineering prompts reuse the exact attributed routing packet and share one strict decision/reason/summary/implication/next-step schema. The application owns event ID, date, Feed rank, and candidate ID. Mini and Terra both suppressed the first dual-relevant mission-statement envelope for both audiences, proving relevance does not force publication. There is no runner, store, or live Insight yet. |
| Insights UI | One Feed-ranked path; intentionally empty | Investment and AI Engineering URL state, date navigation, Feed links, and empty/error handling remain implemented. Its API now returns the honest successor empty state and never reads old Insight databases. Item rendering will be adapted after the first envelope output is approved. |
| Submission package | Not complete | The rubric-mapped write-up, limitations, prompt/evaluation evidence, and final delivery review remain. Nothing has been submitted externally. |

Counts above are dated checkpoint evidence, not live contracts. Query the
current databases or APIs before using them as present-tense product claims.

## The Most Important Unproven Claim

The repository has proved that one prompt/schema, versioned run store, and
exact-match Feed projection can route a varied 90-record cohort, and the five
disputed/borderline packets now behave coherently under the approved v7
boundary. The next unproven claim is that positive audience routes can be
converted into a small set of excellent, source-bound Insights without
reviving the premature multi-stage stack or weakening attribution. Previous
multi-stage Insight results remain historical learning, not the active
contract.

## Submission Finish Line

The routing boundary is frozen. The active Evidence Audience Routing tracker
owns final closeout and archive. At system level, the remaining proof is:

1. Evaluate one user-selected positive envelope with each applicable successor
   prompt and inspect both the surfaced content and any suppression reason.
2. Add the smallest run store only after that output contract is accepted, then
   produce and inspect 3–5 excellent Insights in Feed-rank order.
3. Assemble the rubric-mapped submission package and limitations.
4. Perform the final delivery review before requesting explicit approval for
   any external submission.

External submission or alert delivery remains blocked without Adi's explicit
current-session approval.

## What Is Deliberately Deferred

- Broad RSS, blog, GitHub, arXiv, or second-source ingestion.
- Semantic/topic event clustering beyond exact provider relations.
- A learned ranking model or renewed daily-score weight tuning.
- Large discovered-account admission or recursive graph crawling.
- Mobile/responsive polish.
- Real external alerts, publishing, uploading, or submission without Adi's
  explicit current-session approval.

These are valid future extensions, not prerequisites for proving the current
case-study thesis.

## Current Direction

The active tracker is
[`docs/projects/evidence-audience-routing/tasks.md`](projects/evidence-audience-routing/tasks.md).
The repaired-Event nine-day top-100 routing refresh and its bounded contextual
review are complete. The first successor Insight comparison is also complete
and correctly suppressed a weak dual-relevant candidate across both audiences
and models. The active tracker now owns routing closeout and selection of a
stronger surfaceable Insight candidate. Full-catalog generation and delivery
remain deliberately deferred.

Completed phases and their reasoning are preserved under
[`docs/projects/archive/`](projects/archive/). They should be consulted when a
new decision touches a frozen boundary, not read front-to-back during ordinary
handoff.

## Which Document to Read

| Question | Source of truth |
| --- | --- |
| What is the external assignment? | [`references/case-prompt.md`](references/case-prompt.md) |
| What are we optimizing for and what context matters? | [`references/context.md`](references/context.md) |
| What should be done next, exactly? | [`projects/evidence-audience-routing/tasks.md`](projects/evidence-audience-routing/tasks.md) |
| How is the system implemented? | [`architecture/overview.md`](architecture/overview.md) |
| What product and UI principles are frozen? | [`../PRODUCT.md`](../PRODUCT.md) and [`../DESIGN.md`](../DESIGN.md) |
| Why was a past decision made? | Active/archived project decisions and resources |
| What happened chronologically, including spend and tools? | `scripts/build-log.py recent` / `search`; complete reviewer artifact at [`references/build-log.md`](references/build-log.md) |
| How should an external reviewer inspect the repository? | [`references/reviewer-guide.md`](references/reviewer-guide.md) |

If this brief conflicts with an active tracker, the tracker wins for execution
state. If either conflicts with implemented behavior, stop, record the mismatch
in the tracker, and reconcile the documentation before building on it.

## Cold-Agent Handoff

A new architect or implementation agent should:

1. Read this file and the case prompt.
2. If an active tracker exists, read its Goal, Decisions, Current Batch,
   blockers, and Done When; otherwise use Current Direction above.
3. Read only the architecture section and project resources relevant to the
   current batch.
4. Inspect code and data at the named boundary before proposing a new
   abstraction.
5. Update the tracker while executing; update this brief only when the
   conceptual system status or critical path changes.

Update this file when an active project changes, a major layer moves between
planned/proven, the critical unproven claim changes, or a foundational status
claim becomes false. Do not append progress notes here.
