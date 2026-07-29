# System Status

Last verified: 2026-07-29

This is the conceptual handoff for Frontier Lab Intelligence. Read it before
planning across projects or changing the system direction. It explains what
the product is, what is already real, what remains unproven, and which durable
document answers each deeper question.

This file is not an execution tracker and not a chronological log. Routine work
does not require a project tracker. When Adi explicitly invokes `$project`, that
tracker owns detailed work state; the build log owns historical submission
evidence. Query that history with `scripts/build-log.py recent` or `search` only
when needed; do not load the complete artifact during handoff.

## North Star

Earn the next BIT Capital interview with one coherent, defensible, working
case study: turn public frontier-lab evidence into 3–5 excellent, checkable,
decision-useful insights for an investment team and an AI engineering team.

The product thesis is:

> A curated network can identify important frontier-AI activity early; exact
> evidence grouping, transparent routing, and primary-source citations can
> turn that activity into intelligence a human can trust.

The case study was submitted on 20 July 2026. The follow-up interview and case
discussion with BIT's AI team is on Thursday, 30 July 2026. The immediate
endpoint is being able to explain and defend the working system, its design
choices, trade-offs, limits, costs, agent-assisted build process, and what
should be built next.

Before the follow-up, prioritize interview evidence and explanation:
stress-test the scoring and signal-to-noise choices, make token/API costs easy
to retrieve, rehearse how the system was built, and verify that the surfaced
brief is genuinely useful to a BIT analyst. Do not broaden the platform or
change production behavior merely to make the system look more complete.

## Product Story

```text
Registry
  -> trusted X collection cohort
  -> exact quote / retweet / reply Events over time
  -> same-artifact, same-day Developments
  -> transparent daily Development ranking
  -> independent AI Engineering + Investment routing
  -> company-aware Investment screening and memo retrieval
  -> atomic published Investment cohort
  -> web brief, PDF, and explicit Slack or email delivery
```

The stored-X and canonical-artifact evidence paths are implemented. Current
analysis starts from ranked Developments projected from exact Event evidence
and accepted canonical artifacts. Exact Events remain immutable; same-day
original posts merge only when they point to the same release-specific
artifact.

On 29 July the three stacked Insight lanes were consolidated to one. The
company-aware Investment agent is now the only path that generates, stores,
renders, exports, or delivers an Insight. Superseded editorial and
candidate-decision modules, stores, prompts, API fallbacks, and UI renderers
were deleted rather than kept dormant. AI Engineering has no current generator
and returns an explicit unavailable reason.

The July 19–21 published top-ten cohorts prove screening across all 37 compact
company cards, selective memo retrieval, surface/suppress judgment, and
after-memo rejection. Those visible cohorts still use v8/v9. The active
contract is v11; two v11 proof rows exist, but no complete v11 day has been
published. The immediate refresh boundary is therefore a dry-run followed by
one complete v11 replay of the three top-ten cohorts.

## Where the System Stands

| Layer | Status | What is established |
| --- | --- | --- |
| Registry | Implemented, inspectable, and manually extensible | One entity can own multiple channels; structural kind and Registry admission are separate; rejected records remain reversible and reason-bearing. The Registry UI/API can now intake one X profile through the combined evidence screen or a reason-bearing direct admission, with exact-handle idempotency and durable attempt/model telemetry. The current checkpoint contains 2,630 auditable identities: 2,431 active people, 160 active channel-backed organizations, and 39 reason-bearing rejections. The lean World's Fair 2026/2024 cohort contributes 423 people; unresolved company labels stay person facts rather than fake organizations. Conference inclusion is provenance, not rank or vote weight, and inactivity alone is not a rejection gate because dormant experts can still contribute useful outgoing-follow evidence. |
| Trusted-following graph | Evaluated candidate generator | The current immutable incremental snapshot contains 2,832,858 outgoing-follow edges from 2,558 complete source accounts resolving to 2,521 voting entities. Entity-union overlap is the accepted inspectable support feature across 2,524 active X-addressable Registry targets, including 38 zero-support targets; personalized PageRank remains a diagnostic, not truth. |
| X evidence store | Implemented source boundary | Raw provider evidence is preserved locally and normalized into replayable posts and relations. X is the only implemented discovery source today. |
| Exact event projection | Implemented and regression-tested | Provider-declared evidence is stored as root-owned structural forests, not unrestricted connected components: quote/retweet reactions attach to one source, only the source author's replies extend its thread, and every member has at most one structural parent. Third-party replies remain in the ledger but cannot import their own branch or bridge independent roots. The product publishes each Event exactly once on its earliest canonical source day; later activity appends to that Event without creating another dated candidate. The current July 5–21 Feed contains 81,390 normalized posts; its published Event store contains 14,947 grouped components, 58,430 members, and 43,999 links. The Registry-aware read projection yields 19,657 complete daily Events. |
| Development projection + daily rank | Implemented grouping-only audit surface | `/api/developments` and `/evidence/feed` derive same-day Developments from exact Events plus accepted canonical artifacts. Independently authored original posts merge only when they share the same release-specific artifact; generic host roots are rejected as anchors. Exact Event IDs, posts, activity, and artifact lineage remain inspectable underneath. `daily-development-rank-v1` orders each day by distinct Registry participants across every source Event, mean participant network position, maximum public interactions on one source post, then stable Development ID. Original authors, quote authors, and reposters each count once. There is no organization bonus, scalar score, or weighted blend, and the projection needs no separate database yet. |
| Canonical artifact library | Complete supported pass + operator index | Outbound primary-resource links are conservatively canonicalized, source-linked, fetched once, snapshotted, and replayable. The current Event-native import contains 6,298 accepted source observations, 6,304 disclosures, and 5,378 canonical artifacts with zero import failures. One shared extraction validator rejects placeholder-dominated bodies and deterministic bot, consent, authentication, client-rendering, and error shells before they become packet evidence; immutable raw responses remain preserved. |
| Feed audience routing | v15 July 5–21 production replay complete | The current v15 top-100 pass completed 1,647 Developments with zero failures: 618 both, 200 Engineering-only, 88 Investment-only, and 741 neither. Its deterministic evidence gate completed 325 packets without an LLM call—122 short unsupported text posts and 203 posts whose linked or media evidence was unavailable—while preserving an explicit reason for both audiences. Luna/medium evaluated the remaining 1,322 packets. The run reported 759,808 cached input tokens, 424 cache-hit requests, and $7.762206 total cost. Five transient failures on July 20–21 succeeded on the exact resumable retry. The immutable v14 pass remains available as historical comparison. |
| Audience Insight generation | Company-aware Investment top-ten proof for July 19–21; v11 refresh pending | The Sol/xhigh projection selects the ten highest daily ranks with a positive Investment route—not the union-positive Feed—then screens all 37 companies. Across 30 published v8/v9 Developments it surfaces 19, suppresses 11, retains 52 company assessments, and records five after-memo rejections. July 19 surfaces 4/10, July 20 9/10, and July 21 6/10. Those cohorts reused 472,576 cached input tokens from 1,386,679 total and reported $7.740683. The active v11 contract has two unpublished proof rows; preview and then replay the complete three-day cohort before presenting v11 as live. The production loop owns bounded transient retries and exact traces. Complete daily cohorts publish atomically, so a failed or partial run cannot leak older or out-of-lane rows into the UI. AI Engineering successor work and broader Investment calibration remain unproven. |
| Prompt-cache operations | Implemented and live-verified | Cacheable jobs keep stable 1,024+ token prefixes first, use deterministic keys, serialize within a key, and record Responses `cached_tokens`. Registry jobs now use eight cache lanes instead of 64; audience routing is single-key/cache-first by default; Insight refresh runs one lane per audience prompt. The 27 July different-input canary observed 3/4 Luna and 4/4 Terra warm hits through the shared Azure-backed LiteLLM route. `fli prompt-cache-canary --no-input` makes the check repeatable; misses remain a measured best-effort provider condition rather than proof that a model lacks caching. The authoritative contract, current proof, incident history, and troubleshooting checklist live in [`prompt-caching.md`](references/prompt-caching.md). |
| Investment company context | Complete 37-company research set plus three-day top-ten mapping proof | BIT Lens and the Investment read path expose a source-bearing memo for every company in the canonical candidate universe. Each packet separates company prior context from Event evidence and includes business economics, operating drivers, testable frontier-AI transmission paths, thesis tests, uncertainties, and an exact dated source ledger. The two-stage agent now proves structured Event-to-company judgment across the July 19–21 top ten, including reason-bearing suppression and after-memo rejection; the next boundary is replay across the routed cohort, not company cold start. |
| Insight path consolidation | Complete; one path in code and data | The company-aware Investment agent is the only Insight generator. `fli.insights` now contains only `investment_agent`, `investment_agent_runs`, `company_context`, `pdf_report`, and `cli`; roughly 9,000 lines of superseded editorial, daily-runner, Codex App Server, consolidation, and candidate-decision code were deleted with their tests, prompts, and stores. `/api/insights` has no fallback tier, the SPA has no second renderer, and an audience without a current run returns an explicit reason instead of older content. |
| Insights UI and delivery | One reader, PDF, and delivery projection over the published cohort | Each surfaced Development leads with its agent-written investment headline rather than unreliable webpage metadata. Company rows are collapsed by default; opening one shows the mechanism, each affected company with its direction, affected business driver, size basis, and per-company impact, plus one unproven claim and one next check. Evidence links are application-owned and deterministic: one opens the exact Feed Development and one opens the exact company memo. Model text does not own those URLs. The A4 PDF workbook and confirmed Slack/email delivery render the same published cohort. AI Engineering has no current-lineage run and says so explicitly. |
| Submission package | Submitted 20 July 2026; live reviewer path remains available | The submitted email leads with the public product and video, links the written How it works report, provides five exact showcase Insights, links the public repository, and attaches one sample PDF. A clean checkout restores a checksummed read-only snapshot with one command. |

Counts above are dated checkpoint evidence, not live contracts. Query the
current databases or APIs before using them as present-tense product claims.

## The Most Important Unproven Claim

The repository proves the end-to-end product and the final five submission
Insights are locked. The remaining product claim is whether the current
company-aware Investment path consistently turns routed Developments into a
small set of useful analyst read-throughs without inventing a company
connection. The remaining interview claim is whether that boundary, its cost,
and its limitations can be explained without reconstructing the full build
history.

## Post-submission State

The case study was submitted on 20 July 2026. The submitted proof and
reproduction snapshot remain frozen. The active priorities are:

1. Keep the submitted links and public product stable.
2. Audit the current company-aware Investment output without changing upstream
   evidence or the locked submission proof.
3. Preserve one coherent explanation of the showcase Insights, measured costs,
   limitations, and next steps.
4. Prepare concise interview defenses for source scope, ranking validation,
   top-100 recall, model choice, and the human-triggered delivery boundary.

Any additional external message or alert delivery remains blocked without
Adi's explicit current-session approval.

## What Is Deliberately Deferred

- Broad RSS, blog, GitHub, arXiv, or second-source ingestion.
- Semantic/topic clustering beyond exact provider relations and exact
  same-artifact Development grouping.
- A learned ranking model. Production uses the transparent, deterministic
  `daily-development-rank-v1` ordering; learning weights or optimizing it
  against downstream labels remains deferred.
- Large discovered-account admission or recursive graph crawling.
- Mobile/responsive polish.
- Scheduled/unattended alerts or additional submission messages. Any new
  external send still requires Adi's explicit current-session approval.

These are valid future extensions, not prerequisites for proving the current
case-study thesis.

## Current Direction

The current work boundary is audience-specific Insight judgment over the
deterministic Development projection. Exact Events remain the provenance unit;
shared release-specific artifacts merge same-day original posts for inspection
and `daily-development-rank-v1` provides the common order. The v15 Development
routing proof is complete for the July 5–21 top-100 cohort, and Investment
v8/v9 is published for the ten highest positive Investment routes on July
19–21. The next step is to preview and publish the same three-day cohort under
the active v11 contract, then audit its false positives, suppressions, and
cross-Development duplication. AI Engineering may later be built on the same
path; it must not be restored from deleted editorial code.

Completed reasoning is preserved in the sharded build log and the surviving
trackers under [`docs/projects/archive/`](projects/archive/). Removed project
paths are not active contracts. Use `scripts/build-log.py search` when a
historical decision is not represented by a surviving tracker. The
attention-ranking redesign remains the historical Event-rank lineage; current
Investment work uses the company-aware path and does not restore the deleted
editorial system.

Interview work has now decomposed the final Investment step from a ranked
Development to a defensible public-company transmission path. The compact
37-company index is the screening input, and all 37 complete research packets
are available for retrieval. One July 21 proof screens the complete index,
opens only three plausible memos, validates the final minimal schema, and
projects the result into Insights. The next boundary is testing the same
contract across more routed Developments and tuning false positives and misses.

The public product at
[`frontier-lab-intelligence.adithyan.io`](https://frontier-lab-intelligence.adithyan.io/)
is the primary reviewer experience. Cloudflare Tunnel routes the hostname to
this repository's always-on service at `127.0.0.1:8797`. The reproduction layer
is also complete: `./demo.command` restores an immutable 357 MB snapshot into a
clean checkout, verifies its SHA-256, and serves the frozen data read-only. The
exact local contract is recorded in
[`references/demo-release.md`](references/demo-release.md).

Completed phases and their reasoning are preserved under
[`docs/projects/archive/`](projects/archive/). They should be consulted when a
new decision touches a frozen boundary, not read front-to-back during ordinary
handoff.

## Which Document to Read

| Question | Source of truth |
| --- | --- |
| What is the external assignment? | [`references/case-prompt.md`](references/case-prompt.md) |
| Which Insights demonstrate the case-study proof? | The published product and [`references/reviewer-guide.md`](references/reviewer-guide.md) |
| What should be done next, exactly? | Keep the submitted reviewer path available and prepare the interview defenses listed in Post-submission State; start a new tracker only if Adi explicitly invokes `$project`. |
| Which code/store/command/test owns a stage? | [`architecture/code-map.md`](architecture/code-map.md) |
| How is the system implemented? | [`architecture/overview.md`](architecture/overview.md) |
| What product and UI principles are frozen? | [`../PRODUCT.md`](../PRODUCT.md) and [`../DESIGN.md`](../DESIGN.md) |
| Why was a past decision made? | Active/archived project decisions and resources |
| What happened chronologically, including spend and tools? | `scripts/build-log.py recent` / `search`; complete reviewer artifact at [`references/build-log.md`](references/build-log.md) |
| What does each refresh stage cost? | [`references/tokenomics.md`](references/tokenomics.md) |
| How should an external reviewer inspect the repository? | [`references/reviewer-guide.md`](references/reviewer-guide.md) |

If this brief conflicts with an explicitly invoked active tracker, the tracker
wins for execution state. If either conflicts with implemented behavior, stop
and reconcile the relevant durable documentation before building on it.

## Cold-Agent Handoff

A new architect or implementation agent should:

1. Read this file and the case prompt.
2. If Adi explicitly invoked `$project`, read its Goal, Decisions, Current
   Batch, blockers, and Done When; otherwise use Current Direction above.
3. Read only the architecture and reference docs relevant to the current work.
4. Inspect code and data at the named boundary before proposing a new
   abstraction.
5. Update an explicitly invoked tracker while executing; otherwise work
   directly. Update this brief only when conceptual status or the critical path
   changes.

Update this file when an active project changes, a major layer moves between
planned/proven, the critical unproven claim changes, or a foundational status
claim becomes false. Do not append progress notes here.
