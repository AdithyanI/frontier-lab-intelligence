# System Status

Last verified: 2026-07-21

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

The case study was submitted on 2026-07-20. The current endpoint is earning the
next interview through a stable reviewer path and a defensible discussion of
the system's decisions, limits, and next steps. New platform breadth remains
lower value than keeping the submitted proof coherent and available.

## Product Story

```text
Registry
  -> trusted X collection cohort
  -> exact quote / retweet / reply Events over time
  -> transparent daily-score ordering
  -> independent AI Engineering + Investment routing
  -> optional per-Event working annotations
  -> daily agent research, consolidation, and ranked cited Insights
  -> separate Investment + AI Engineering views
  -> explicit Slack or email Daily Brief delivery
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
first-party-only requests into one resumable SQLite store. Investment v10 and
AI Engineering v7 now use per-audience watchpoint/experiment schemas and stored
post dates. The July 5–15 current-contract cohort is fully evaluated. The
per-Event layer remains an auditable annotation source. A repo-local daily
intelligence agent now owns consolidation and final selection across the
complete routed-positive cohort behind a strict validated write boundary.

## Where the System Stands

| Layer | Status | What is established |
| --- | --- | --- |
| Registry | Implemented, inspectable, and manually extensible | One entity can own multiple channels; structural kind and Registry admission are separate; rejected records remain reversible and reason-bearing. The Registry UI/API can now intake one X profile through the combined evidence screen or a reason-bearing direct admission, with exact-handle idempotency and durable attempt/model telemetry. The current checkpoint contains 2,630 auditable identities: 2,431 active people, 160 active channel-backed organizations, and 39 reason-bearing rejections. The lean World's Fair 2026/2024 cohort contributes 423 people; unresolved company labels stay person facts rather than fake organizations. Conference inclusion is provenance, not rank or vote weight, and inactivity alone is not a rejection gate because dormant experts can still contribute useful outgoing-follow evidence. |
| Trusted-following graph | Evaluated candidate generator | The current immutable incremental snapshot contains 2,832,858 outgoing-follow edges from 2,558 complete source accounts resolving to 2,521 voting entities. Entity-union overlap is the accepted inspectable support feature across 2,524 active X-addressable Registry targets, including 38 zero-support targets; personalized PageRank remains a diagnostic, not truth. |
| X evidence store | Implemented source boundary | Raw provider evidence is preserved locally and normalized into replayable posts and relations. X is the only implemented discovery source today. |
| Exact event projection | Implemented and regression-tested | Provider-declared evidence is stored as root-owned structural forests, not unrestricted connected components: quote/retweet reactions attach to one source, only the source author's replies extend its thread, and every member has at most one structural parent. Third-party replies remain in the ledger but cannot import their own branch or bridge independent roots. The product publishes each Event exactly once on its earliest canonical source day; later activity appends to that Event without creating another dated candidate. The clean July 5–15 Feed contains 51,323 normalized posts; its one-run Event store contains 9,646 grouped Events, 37,227 members, and 27,913 links. |
| Feed + daily score | Implemented audit surface | Daily collection includes authored replies and tracked reactions. The Feed is date-filterable, shows one frozen canonical-day rank across Status/search filters, and explains its transparent tracked-amplification, author-support, and public-engagement inputs on demand. Later reactions remain available in one flat activity disclosure but do not republish or rerank the source Event. Registry changes affect derived views without rewriting raw evidence. |
| Canonical artifact library | Complete supported pass + operator index | Outbound primary-resource links are conservatively canonicalized, source-linked, fetched once, snapshotted, and replayable. The active Event-native import contains 5,032 decisions, 4,627 accepted source observations, and 3,999 canonical artifacts with zero lineage violations. The catalog has usable text for 3,453 artifacts; 252 are catalogued but unfetched, 25 are retryable, and 269 are unavailable. One shared extraction validator rejects placeholder-dominated bodies and deterministic bot, consent, authentication, client-rendering, and error shells before they become packet evidence; immutable raw responses remain preserved. |
| Feed audience routing | Current v9 packet policy plus exact cross-publication reuse | The direct Evidence runtime returns independent AI Engineering and Investment booleans plus evidence-grounded reasons. New freezes admit only first-party X sources from the evaluation day through seven days earlier: a current same-author continuation may replace an older root, while an old-only Event is excluded. Independently authored reactions and pure reposts remain outside model input. Multi-day refresh freezes one global publication before parallel day execution and creates immutable current-lineage targets. It reuses a compatible predecessor judgment only for the exact same Event, evidence SHA, and rendered input SHA; changed or newly ranked Events alone require model work, and reuse provenance remains stored per row. |
| Audience Insight generation | Complete v10/v7 evaluation of every routed-positive audience | Investment v10 and AI Engineering v7 address distinct readers through one shared decision core and per-audience action schemas: `Summary` → `Why it matters` → one trigger-shaped Investment `Watchpoint` or one bounded Engineering `Experiment`. Insight-only rendering adds the evaluation day and stored post dates without changing routing hashes, and suppresses resurfaced historical material that has no current development. `fli insights` freezes exact requests before execution, rejects non-current source or prompt contracts, resumes completed audiences without another call, and records result/cache/cost telemetry. The current production batch contains 947 unique Event/audience decisions: 404 surfaced and 543 suppressed. It reported 847 cache-hit requests, 1,755,904 cached tokens, and $15.512238 proxy-reported cost. The stale 2022 ChatGPT candidate is now suppressed with its date; all 189 surfaced Investment notes use trigger→assumption watchpoints, and no surfaced rationale contains editorial gate-talk. Cross-Event semantic duplicates remain an explicit downstream editorial boundary. |
| Daily editorial agent | Strict workspace v3 plus safe post-freeze date fan-out | `$fli-daily-intelligence` freezes the routed-positive day, applies the seven-day first-party X window, projects authoritative X publication dates, and exposes exact artifact disclosure lineage without automatically filtering artifacts. Workspace v3 with `semantic_snapshot_sha256` is the only executable authoring contract; historical packets are not upgraded or resumed. `fli daily-intelligence run-day` checkpoints exact Evidence, routing, workspace, Codex-task, and editorial-run identities for one date. Historical parallel work instead publishes Evidence once, routes the full range against that publication, and then fans out independent immutable workspaces and Codex tasks; several full `run-day` Evidence publishers do not compete. Retries treat a durable import as terminal before touching App Server and validate frozen task settings before any live resume. Artifact citations still require verified excerpts; embeddings remain optional retrieval only. |
| Insights UI and delivery | Canonical daily reader, cached PDF workbook, manual Slack/email delivery, plus candidate audit | For an imported day, `Kept` reads the newest complete daily editorial run. Investment presents the conclusion-led title, facts, one causal interpretation, company read-through, confirmation/challenge signals, and separate original-Feed and artifact/context sources without exposing intermediate reasoning scaffolding. Engineering retains its bounded experiment detail. The selected complete audience/day downloads from the top-right as a deterministic A4 workbook. Beside it, a muted `Send brief` action requires an explicit confirmation: Slack presents every cited Insight with its complete interpretation and links to the complete brief and PDF; email receives up to five ranked Insights with the cached PDF attached. Provider credentials remain server-side, and the same-origin app confirms sends without a separate access-key field. The PDF's reader-first opening combines the title, audience/date, and clickable ranked Insight titles without run hashes or pipeline counts; every title jumps directly to analysis without the web-only rank-rationale disclosure, then continues to its linked full source ledger, and every later page returns to the brief index. Original-Feed titles in the PDF open the exact internal Feed Event, which retains the onward original-post link; artifact/context titles still open their cited sources directly. Serif display headings and blue slash markers give the workbook a restrained visual relationship to the case brief without copying BIT branding. `/api/insights/report.pdf` renders only the canonical read projection into an atomic content-addressed cache with ETag revalidation. `Suppressed` / `All` and days without an imported run retain the per-Event candidate audit. `/api/insights` exposes a discriminated read contract and the date rail overlays final imported counts. All fifteen July 5–19 days have canonical imported runs. |
| Submission package | Submitted 20 July 2026; live reviewer path remains available | The submitted email leads with the public product and video, links the written How it works report, provides five exact showcase Insights, links the public repository, and attaches one sample PDF. A clean checkout restores a checksummed read-only snapshot with one command. |

Counts above are dated checkpoint evidence, not live contracts. Query the
current databases or APIs before using them as present-tense product claims.

## The Most Important Unproven Claim

The repository proves the end-to-end product and the final five submission
Insights are locked. The remaining claim is communicative: whether an external
reviewer can understand the product, reproduce the evidence-backed demo, and
see the rubric coverage without reconstructing the development history.

## Post-submission State

The case study was submitted on 20 July 2026. The intelligence and
reproduction boundaries remain frozen. The active priorities are:

1. Keep the submitted links and public product stable.
2. Preserve one coherent explanation of the five showcase Insights, measured
   costs, limitations, and next steps.
3. Prepare concise interview defenses for source scope, ranking validation,
   top-100 recall, model choice, and the human-triggered delivery boundary.

Any additional external message or alert delivery remains blocked without
Adi's explicit current-session approval.

## What Is Deliberately Deferred

- Broad RSS, blog, GitHub, arXiv, or second-source ingestion.
- Semantic/topic event clustering beyond exact provider relations.
- A learned ranking model. Attention Score v2 research is archived as deferred;
  production remains on the existing transparent day-relative formula.
- Large discovered-account admission or recursive graph crawling.
- Mobile/responsive polish.
- Scheduled/unattended alerts or additional submission messages. Any new
  external send still requires Adi's explicit current-session approval.

These are valid future extensions, not prerequisites for proving the current
case-study thesis.

## Current Direction

The bounded artifact-content repair is complete: the shared validator now
quarantines obvious extraction shells, 25 previously accepted false successes
were reclassified, and immutable successor routing runs reused 195 exact
judgments while rerouting only five changed packets. No Insight run was
triggered. Routine follow-up remains tracker-free.

Repository housekeeping is complete and archived
under [`docs/projects/archive/repo-housekeeping/`](projects/archive/repo-housekeeping/):
all runtime domains have direct package ownership, the code/data map is the
cold-start implementation index, local-data lifecycle is explicit, and fast
checks prevent the former flat source layout from returning. Attention Score
v2 remains paused and archived without changing the production score.

The submission-critical daily-intelligence quality project is complete and
archived under
[`docs/projects/archive/daily-intelligence-quality/`](projects/archive/daily-intelligence-quality/).
It shipped deterministic X chronology, artifact disclosure lineage, verified
artifact excerpts, resumable Codex handoff, calibrated company direction,
compact agent inspection, and current imported runs through 19 July. The final
five-Insight proof is locked in its
[`submission selection`](projects/archive/daily-intelligence-quality/resources/submission-proof-selection-2026-07-19.md).
Busy-day tail selection and cross-day novelty remain disclosed limitations,
not blockers to the curated proof. Post-submission work is limited to reviewer
clarity, availability, and interview preparation, not another
intelligence-generation or harness cycle.

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
| Which Insights are the locked submission proof? | [`projects/archive/daily-intelligence-quality/resources/submission-proof-selection-2026-07-19.md`](projects/archive/daily-intelligence-quality/resources/submission-proof-selection-2026-07-19.md) |
| What should be done next, exactly? | Keep the submitted reviewer path available and prepare the interview defenses listed in Post-submission State; start a new tracker only if Adi explicitly invokes `$project`. |
| Which code/store/command/test owns a stage? | [`architecture/code-map.md`](architecture/code-map.md) |
| How is the system implemented? | [`architecture/overview.md`](architecture/overview.md) |
| What product and UI principles are frozen? | [`../PRODUCT.md`](../PRODUCT.md) and [`../DESIGN.md`](../DESIGN.md) |
| Why was a past decision made? | Active/archived project decisions and resources |
| What happened chronologically, including spend and tools? | `scripts/build-log.py recent` / `search`; complete reviewer artifact at [`references/build-log.md`](references/build-log.md) |
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
