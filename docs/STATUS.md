# System Status

Last verified: 2026-07-15

This is the conceptual handoff for Frontier Lab Intelligence. Read it before
planning across projects or changing the system direction. It explains what
the product is, what is already real, what remains unproven, and which durable
document answers each deeper question.

This file is not the execution tracker and not a chronological log. The active
project tracker owns detailed work state; the build log owns history.

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
  -> later cited extraction from stored X + canonical artifacts
  -> eventual separate Investment + AI Engineering views
```

The stored-X and canonical-artifact evidence paths are implemented. The earlier
multi-stage Audience Insights v2 implementation remains in code and has been
archived, while all generated outputs were explicitly discarded on 2026-07-15.
The successor now starts directly from ranked Feed evidence: one versioned
GPT-5.4-mini/high call makes independent AI Engineering and Investment relevance
judgments over a complete attributed evidence packet. The former model-based
keep/drop gate, its generated databases, and its live API/UI/CLI surfaces were
removed on 2026-07-15. The Feed derives `kept` only when either audience is
relevant; it is not a third judgment. Insight
writing, publication auditing, reconciliation, briefing, and export remain
deferred until this narrower routing boundary is qualitatively proven.

## Where the System Stands

| Layer | Status | What is established |
| --- | --- | --- |
| Registry | Implemented, inspectable, and manually extensible | One entity can own multiple channels; structural kind and Registry admission are separate; rejected records remain reversible and reason-bearing. The Registry UI/API can now intake one X profile through the combined evidence screen or a reason-bearing direct admission, with exact-handle idempotency and durable attempt/model telemetry. The current checkpoint contains 2,630 auditable identities: 2,431 active people, 160 active channel-backed organizations, and 39 reason-bearing rejections. The lean World's Fair 2026/2024 cohort contributes 423 people; unresolved company labels stay person facts rather than fake organizations. Conference inclusion is provenance, not rank or vote weight, and inactivity alone is not a rejection gate because dormant experts can still contribute useful outgoing-follow evidence. |
| Trusted-following graph | Evaluated candidate generator | The current immutable incremental snapshot contains 2,832,858 outgoing-follow edges from 2,558 complete source accounts resolving to 2,521 voting entities. Entity-union overlap is the accepted inspectable support feature across 2,524 active X-addressable Registry targets, including 38 zero-support targets; personalized PageRank remains a diagnostic, not truth. |
| X evidence store | Implemented source boundary | Raw provider evidence is preserved locally and normalized into replayable posts and relations. X is the only implemented discovery source today. |
| Exact event projection | Implemented and regression-tested | Provider-declared quote, retweet, and reply relations form stable envelopes with cutoff-correct daily snapshots and deduplicated weekly views. The current nine-day run contains 20,159 posts and 5,202 exact events. |
| Feed + daily score | Implemented audit surface | The Feed is date-filterable, shows one stable daily score rank across Audit/search filters, and explains its transparent tracked-amplification, author-support, and public-engagement inputs on demand. Registry changes affect derived views without rewriting raw evidence. |
| Canonical artifact library | Bounded implementation + operator index | Outbound primary-resource links are conservatively canonicalized, source-linked, fetched once, snapshotted, and replayable. The catalog contains 1,566 canonical artifacts and a read-only inspection page; the bounded cohort now has 22 clean-text snapshots (19 native plus three Jina Reader recoveries). |
| Feed audience routing | Implemented; nine-day top-10 audit active | The direct Evidence runtime returns independent AI Engineering and Investment booleans plus evidence-grounded reasons, preserves the attributed primary/artifact/reaction hierarchy, and stores exact input/model/cost provenance. GPT-5.4 mini at high reasoning completed 90/90 top-ranked envelopes across July 5–13: 44 `both`, six Engineering-only, eight Investment-only, and 32 `neither`. The single stable prompt key produced 88 cache-hit requests and 152,576 cached tokens from 305,600 input tokens; 89 response-cost headers total $0.462966 and one is missing. Exact snapshot matches appear in Feed as `ENG`/`INV` marks with the two reasons in one disclosure. One derived Status control exposes Relevant, Not relevant, and Not evaluated without inventing a third judgment. Adi's qualitative review remains. |
| Audience insight engine | Historical implementation preserved; not active | The previous split-audience extraction, review, editor, citation, and audit implementation remains in code and its learnings remain archived. Generated run data was deleted; no Insight result is live. |
| Independent audit + recall | Implemented, fail-closed | An adjacent Luna-high publication audit rechecks every selection and a bounded reject sample without seeing rank or prior judgments. Exact false-negative adjudications and immutable finalization sidecars are hash-bound. The 73-packet/146-evaluation rank-blind recall cohort triggered bounded AI widening on exact days rather than a global rank-window expansion. |
| Production publication boundary | Code preserved; no production data | The reconciliation and audit implementation remains available as prior work, but there are no source runs, adjacent audits, or canonical publication pair after the explicit data reset. It is not part of the live product until the simpler extraction contract proves useful. |
| Insights UI | One Feed-ranked path; intentionally empty | Investment and AI Engineering URL state, Feed provenance, citations, date navigation, and empty/error handling remain implemented. The premature Feed-ranked/Reviewed selector was removed. The surface stays empty until a new agreed schema and prompt produce inspected results. |
| Submission package | Not complete | The rubric-mapped write-up, limitations, prompt/evaluation evidence, and final delivery review remain. Nothing has been submitted externally. |

Counts above are dated checkpoint evidence, not live contracts. Query the
current databases or APIs before using them as present-tense product claims.

## The Most Important Unproven Claim

The repository has proved that one simple prompt/schema, versioned run store,
and exact-match Feed projection can route a varied 90-record cohort. It has not
yet proved that the audience threshold is editorially correct: 32 top-ranked
envelopes route to neither audience and 14 route to exactly one, but Adi has not
audited a representative slice of those reasons. Previous multi-stage Insight
results remain historical learning, not the active contract. The next step is
that qualitative audit—not Insight prose or a full-catalog expansion.

## Submission Finish Line

The active Evidence Audience Routing tracker owns the execution detail. At
system level, the remaining proof is:

1. Audit representative `both`, single-audience, and `neither` outputs from the
   July 5–13 top-10 cohort with Adi in Feed.
2. Correct any packet, prompt, or threshold ambiguity revealed by that audit.
3. Use the 32 observed `neither` cases and 14 single-audience cases to calibrate
   the threshold; add lower-ranked hard negatives only if the audit exposes a
   real coverage gap.
4. Freeze the routing contract before any full-catalog expansion.
5. Open a separate Insight-generation project only after routing is accepted.

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
Its first exact-envelope review and nine-day top-10 routing run are complete and
inspectable in Feed. Adi's qualitative audit is next. Insight generation,
full-catalog expansion, and delivery remain deliberately deferred.

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
| What happened chronologically, including spend and tools? | [`references/build-log.md`](references/build-log.md) |
| How should an external reviewer inspect the repository? | [`references/reviewer-guide.md`](references/reviewer-guide.md) |

If this brief conflicts with the active tracker, the tracker wins for execution
state. If either conflicts with implemented behavior, stop, record the mismatch
in the tracker, and reconcile the documentation before building on it.

## Cold-Agent Handoff

A new architect or implementation agent should:

1. Read this file and the case prompt.
2. Read the active tracker's Goal, Decisions, Current Batch, blockers, and Done
   When.
3. Read only the architecture section and project resources relevant to the
   current batch.
4. Inspect code and data at the named boundary before proposing a new
   abstraction.
5. Update the tracker while executing; update this brief only when the
   conceptual system status or critical path changes.

Update this file when an active project changes, a major layer moves between
planned/proven, the critical unproven claim changes, or a foundational status
claim becomes false. Do not append progress notes here.
