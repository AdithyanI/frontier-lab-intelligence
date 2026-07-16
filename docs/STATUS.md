# System Status

Last verified: 2026-07-16

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
judgments over a first-party-authored evidence packet. The former model-based
keep/drop gate, its generated databases, and its live API/UI/CLI surfaces were
removed on 2026-07-15. The Feed derives `kept` only when either audience is
relevant; it is not a third judgment. A successor Insight foundation defines
two audience prompts and one small surface-or-suppress schema. Historical Terra
calibrations remain documented, but their generated rows were deleted because
they used superseded source and output contracts. The production path freezes
first-party-only requests into one resumable SQLite store. Investment v9 and
AI Engineering v6 are calibrated on the original bounded review set plus a
balanced 50-decision expansion. The remaining catalog is paused because the
expansion exposed cross-Event semantic duplicates that prompt tuning cannot
resolve.

## Where the System Stands

| Layer | Status | What is established |
| --- | --- | --- |
| Registry | Implemented, inspectable, and manually extensible | One entity can own multiple channels; structural kind and Registry admission are separate; rejected records remain reversible and reason-bearing. The Registry UI/API can now intake one X profile through the combined evidence screen or a reason-bearing direct admission, with exact-handle idempotency and durable attempt/model telemetry. The current checkpoint contains 2,630 auditable identities: 2,431 active people, 160 active channel-backed organizations, and 39 reason-bearing rejections. The lean World's Fair 2026/2024 cohort contributes 423 people; unresolved company labels stay person facts rather than fake organizations. Conference inclusion is provenance, not rank or vote weight, and inactivity alone is not a rejection gate because dormant experts can still contribute useful outgoing-follow evidence. |
| Trusted-following graph | Evaluated candidate generator | The current immutable incremental snapshot contains 2,832,858 outgoing-follow edges from 2,558 complete source accounts resolving to 2,521 voting entities. Entity-union overlap is the accepted inspectable support feature across 2,524 active X-addressable Registry targets, including 38 zero-support targets; personalized PageRank remains a diagnostic, not truth. |
| X evidence store | Implemented source boundary | Raw provider evidence is preserved locally and normalized into replayable posts and relations. X is the only implemented discovery source today. |
| Exact event projection | Implemented and regression-tested | Provider-declared evidence is stored as root-owned structural forests, not unrestricted connected components: quote/retweet reactions attach to one source, only the source author's replies extend its thread, and every member has at most one structural parent. Third-party replies remain in the ledger but cannot import their own branch or bridge independent roots. The product publishes each Event exactly once on its earliest canonical source day; later activity appends to that Event without creating another dated candidate. The clean July 5–15 Feed contains 51,323 normalized posts; its one-run Event store contains 9,646 grouped envelopes, 37,227 members, and 27,913 links. |
| Feed + daily score | Implemented audit surface | Daily collection includes authored replies and tracked reactions. The Feed is date-filterable, shows one frozen canonical-day rank across Audit/search filters, and explains its transparent tracked-amplification, author-support, and public-engagement inputs on demand. Later reactions remain available in one flat activity disclosure but do not republish or rerank the source Event. Registry changes affect derived views without rewriting raw evidence. |
| Canonical artifact library | Complete supported pass + operator index | Outbound primary-resource links are conservatively canonicalized, source-linked, fetched once, snapshotted, and replayable. The reply-inclusive catalog converges to 2,735 artifacts with zero lineage violations; 2,507 have usable text, including all 221 arXiv metadata/abstract records and all 167 cached X Articles. Videos remain deferred and 65 non-video pages are unavailable or retryable. One shared extraction validator rejects placeholder-dominated bodies before they become successful snapshots. |
| Feed audience routing | Current v9 top-100 coverage through July 15 | The direct Evidence runtime returns independent AI Engineering and Investment booleans plus evidence-grounded reasons. Its semantic packet contains the root, same-author replies/thread/quote commentary, and accepted first-party artifacts; independently authored reactions and pure reposts remain outside model input. The July 14–15 extension completed 200/200 envelopes with zero failures: 61 both, 21 Engineering-only, 32 Investment-only, and 86 neither. All 200 requests were cache-eligible, 168 reported cache reads (301,056 cached tokens), and proxy-reported cost was $1.052918. The earlier July 5–13 runs remain stored without another model call; routes are exposed only where their frozen envelope hash still matches the rebuilt publication. |
| Audience Insight generation | Implementation complete; 75-decision persona audit ready for selection | Investment v9 and AI Engineering v6 share one strict decision/title/reason/summary/implication/next-step schema but address distinct readers: a technically fluent bottom-up public-tech investor and a senior product-minded production AI engineer. Investment next steps require a thesis, exposure, value-chain consequence, or investment-relevant observable rather than an Engineering experiment. Engineering next steps apply transferable source patterns to a representative team workflow instead of assigning audience-remote reproduction work. Model input uses the same first-party semantic boundary as routing. `fli insights` freezes exact requests before execution, rejects non-current source or prompt contracts, resumes completed audiences without another call, and records result/cache/cost telemetry. The prompt-qualified store contains 75 decisions: 43 surfaced, 32 suppressed, 89,600 cached input tokens, and $1.305057 proxy-reported cost. The latest balanced 50-decision expansion surfaced 30 and suppressed 20, but those 30 contain about seven obvious cross-Event duplicate notes; the next boundary is consolidation/final selection, not looser prompts or immediate catalog scale. |
| Insights UI | Ready for the v9/v6 audit and final selection | The Investment and AI Engineering views share the Feed-style date rail, inherit the frozen canonical Feed rank, and expose `Kept`, `Suppressed`, and `All` status views. `/api/insights/dates` and `/api/insights` are the only live endpoints. Publication requires the exact current audience prompt/hash/schema and a completed current v9 routing item; no old row is re-anchored, relabeled, or read through a compatibility route. The current checkpoint exposes 43 kept and 32 suppressed decisions across all nine evaluated days. Repeated runs of one Event/audience are deduplicated, but semantically overlapping independent Events remain visible for audit until the consolidation boundary is chosen. |
| Submission package | Not complete | The rubric-mapped write-up, limitations, prompt/evaluation evidence, and final delivery review remain. Nothing has been submitted externally. |

Counts above are dated checkpoint evidence, not live contracts. Query the
current databases or APIs before using them as present-tense product claims.

## The Most Important Unproven Claim

The repository has proved that one prompt/schema, versioned run store, and
canonical Feed projection can route a complete nine-day top-100 cohort under a
first-party-only semantic boundary. Two bounded Terra calibrations and one
balanced 50-decision expansion have proved that the current audience gates can
retain actionable early signals while rejecting weak packets. The next
unproven claim is editorial rather than model-local: whether semantically
overlapping independent Events should be consolidated before the final reader
view, and which 3–5 unique developments form the strongest submission proof.
The latest 30 surfaced decisions represent roughly 23 unique developments, so
immediate catalog scale would amplify a known duplication problem rather than
add stronger evidence. Previous multi-stage Insight results remain historical
learning, not the active contract.

## Submission Finish Line

The routing boundary is frozen. The active Evidence Audience Routing tracker
owns final closeout and archive. At system level, the remaining proof is:

1. Consolidate or manually select across the obvious cross-Event duplicate
   clusters without weakening the per-Event audience prompts.
2. Rank the unique Investment/Engineering developments for usefulness,
   specificity, evidence quality, and audience fit, then select the strongest
   3–5 for the submission proof.
3. Assemble the rubric-mapped submission package and limitations.
4. Perform the final delivery review before requesting explicit approval for
   any external submission.

External submission or alert delivery remains blocked without Adi's explicit
current-session approval.

## What Is Deliberately Deferred

- Broad RSS, blog, GitHub, arXiv, or second-source ingestion.
- Semantic/topic event clustering beyond exact provider relations.
- A learned ranking model or renewed daily-score weight tuning. A verified
  redesign concept and deferred tracker exist at
  [`projects/attention-score-v2/`](projects/attention-score-v2/); it must not
  activate before submission delivery.
- Large discovered-account admission or recursive graph crawling.
- Mobile/responsive polish.
- Real external alerts, publishing, uploading, or submission without Adi's
  explicit current-session approval.

These are valid future extensions, not prerequisites for proving the current
case-study thesis.

## Current Direction

The active tracker is
[`docs/projects/evidence-audience-routing/tasks.md`](projects/evidence-audience-routing/tasks.md).
The canonical Event rebuild and v9 nine-day top-100 routing replacement are
complete. The old v8 routing directories, superseded Insight prompt rows,
duplicate Insight API routes, and Event re-anchoring helper are gone. The
current Investment v9 / Engineering v6 store contains the 75-decision audit;
the active tracker owns cross-Event consolidation, final 3–5 selection, and
closeout.

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
