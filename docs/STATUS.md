# System Status

Last verified: 2026-07-28

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

The case study was submitted on 2026-07-20. As of 2026-07-26, Adi has three
working days before the Thursday follow-up interview and case discussion with
BIT's AI team. The immediate endpoint is no longer submission: it is being able
to explain and defend the working system, its design choices, trade-offs,
limits, costs, agent-assisted build process, and what should be built next.

During this three-day window, prioritize interview evidence and explanation:
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
  -> optional per-Event working annotations
  -> daily agent research, consolidation, and ranked cited Insights
  -> separate Investment + AI Engineering views
  -> explicit Slack or email Daily Brief delivery
```

The stored-X and canonical-artifact evidence paths are implemented. The earlier
multi-stage Audience Insights v2 implementation and generated outputs were
explicitly discarded on 2026-07-15; its learnings remain archived in docs.
The successor now starts from ranked Developments projected from exact Event
evidence and accepted canonical artifacts. Exact Events remain immutable;
same-day original posts merge only when they point to the same release-specific
artifact. Historical `daily-rank-v2` routing, Insight, editorial, PDF, and
delivery outputs remain preserved as prior proof but are not current
Development-lineage outputs. One July 21 Development now proves the successor
Investment boundary: the agent screens all 37 compact company cards, opens only
three causally plausible company memos, and persists three minimal, auditable
company read-throughs. This is a single-Development proof, not a completed
full-day replay.
The former model-based
keep/drop gate, its generated databases, and its live API/UI/CLI surfaces were
removed on 2026-07-15. The Feed derives `kept` only when either audience is
relevant; it is not a third judgment. A successor Insight foundation defines
two audience prompts and one small surface-or-suppress schema. Historical Terra
calibrations remain documented, but their generated rows were deleted because
they used superseded source and output contracts. The production path freezes
first-party-only requests into one resumable SQLite store. Investment v10 and
AI Engineering v7 now use per-audience watchpoint/experiment schemas and stored
post dates. The July 5–21 `daily-rank-v2` cohort remains fully evaluated as
historical lineage. A repo-local daily intelligence agent owns consolidation
and final selection, but it has deliberately not been replayed against the new
Development projection.

## Where the System Stands

| Layer | Status | What is established |
| --- | --- | --- |
| Registry | Implemented, inspectable, and manually extensible | One entity can own multiple channels; structural kind and Registry admission are separate; rejected records remain reversible and reason-bearing. The Registry UI/API can now intake one X profile through the combined evidence screen or a reason-bearing direct admission, with exact-handle idempotency and durable attempt/model telemetry. The current checkpoint contains 2,630 auditable identities: 2,431 active people, 160 active channel-backed organizations, and 39 reason-bearing rejections. The lean World's Fair 2026/2024 cohort contributes 423 people; unresolved company labels stay person facts rather than fake organizations. Conference inclusion is provenance, not rank or vote weight, and inactivity alone is not a rejection gate because dormant experts can still contribute useful outgoing-follow evidence. |
| Trusted-following graph | Evaluated candidate generator | The current immutable incremental snapshot contains 2,832,858 outgoing-follow edges from 2,558 complete source accounts resolving to 2,521 voting entities. Entity-union overlap is the accepted inspectable support feature across 2,524 active X-addressable Registry targets, including 38 zero-support targets; personalized PageRank remains a diagnostic, not truth. |
| X evidence store | Implemented source boundary | Raw provider evidence is preserved locally and normalized into replayable posts and relations. X is the only implemented discovery source today. |
| Exact event projection | Implemented and regression-tested | Provider-declared evidence is stored as root-owned structural forests, not unrestricted connected components: quote/retweet reactions attach to one source, only the source author's replies extend its thread, and every member has at most one structural parent. Third-party replies remain in the ledger but cannot import their own branch or bridge independent roots. The product publishes each Event exactly once on its earliest canonical source day; later activity appends to that Event without creating another dated candidate. The current July 5–21 Feed contains 81,390 normalized posts; its published Event store contains 14,947 grouped components, 58,430 members, and 43,999 links. The Registry-aware read projection yields 19,657 complete daily Events. |
| Development projection + daily rank | Implemented grouping-only audit surface | `/api/developments` and `/evidence/feed` derive same-day Developments from exact Events plus accepted canonical artifacts. Independently authored original posts merge only when they share the same release-specific artifact; generic host roots are rejected as anchors. Exact Event IDs, posts, activity, and artifact lineage remain inspectable underneath. `daily-development-rank-v1` orders each day by distinct Registry participants across every source Event, mean participant network position, maximum public interactions on one source post, then stable Development ID. Original authors, quote authors, and reposters each count once. There is no organization bonus, scalar score, or weighted blend, and the projection needs no separate database yet. |
| Canonical artifact library | Complete supported pass + operator index | Outbound primary-resource links are conservatively canonicalized, source-linked, fetched once, snapshotted, and replayable. The current Event-native import contains 6,298 accepted source observations, 6,304 disclosures, and 5,378 canonical artifacts with zero import failures. One shared extraction validator rejects placeholder-dominated bodies and deterministic bot, consent, authentication, client-rendering, and error shells before they become packet evidence; immutable raw responses remain preserved. |
| Feed audience routing | Luna/medium Development top-100 validated | The complete historical July 5–21 `daily-rank-v2` Event runs remain auditable. The self-contained `audience-routing-v13` prompt now routes one whole Development packet with all original posts and artifact lineage while leaving pure amplifiers out of semantic evidence. The sequential July 21 top-100 pass completed all 97 routable Developments with zero failures: 55 both, 10 Engineering-only, 11 Investment-only, and 21 neither. Three displayed ranks lacked a current first-party X source from which to freeze a packet. A positive route is a recall-oriented candidate for downstream investigation, not a publishable Insight; only one routed Development has completed the successor Investment analysis so far. |
| Audience Insight generation | One company-aware Investment successor proof | Historical Investment v10 and AI Engineering v7 outputs remain preserved, and current readers reject their superseded Event-rank lineage as successor output. For July 21 Development rank 1, the new Terra/high two-stage agent screened all 37 companies, opened PANW, NTSK, and RBRK memos, and persisted three plain-language assessments under `investment-agent-read-v2`. The second turn reused 17,920 cached input tokens; total reported model cost was $0.1317225. Full-day Investment replay, calibration, and an AI Engineering successor remain unproven. |
| Prompt-cache operations | Implemented and live-verified | Cacheable jobs keep stable 1,024+ token prefixes first, use deterministic keys, serialize within a key, and record Responses `cached_tokens`. Registry jobs now use eight cache lanes instead of 64; audience routing is single-key/cache-first by default; Insight refresh runs one lane per audience prompt. The 27 July different-input canary observed 3/4 Luna and 4/4 Terra warm hits through the shared Azure-backed LiteLLM route. `fli prompt-cache-canary --no-input` makes the check repeatable; misses remain a measured best-effort provider condition rather than proof that a model lacks caching. The authoritative contract, current proof, incident history, and troubleshooting checklist live in [`prompt-caching.md`](references/prompt-caching.md). |
| Investment company context | Complete 37-company research set plus one live mapping proof | BIT Lens and the Investment read path expose a source-bearing memo for every company in the canonical candidate universe. Each packet separates company prior context from Event evidence and includes business economics, operating drivers, testable frontier-AI transmission paths, thesis tests, uncertainties, and an exact dated source ledger. The two-stage agent now proves structured Event-to-company judgment for one July 21 Development; the next boundary is calibration and replay across the routed cohort, not company cold start. |
| Daily editorial agent | Historical 17-day proof preserved; Development replay not started | The complete July 5–21 `daily-orchestration-v3` proof remains bound to historical `daily-rank-v2` lineage. The agent and validation contracts remain implemented, but no Development-lineage daily brief, PDF, or delivery projection has been generated. |
| Insights UI and delivery | Successor Investment inspection plus the historical daily reader | When a company-aware Investment run exists for a day, it takes precedence over the historical editorial projection. Its Development rows are collapsed by default; opening one shows the bottom line, mechanism, affected business driver, main uncertainty, and one next check for each surfaced company. Evidence links are application-owned and deterministic: one opens the exact Feed Development and one opens the exact company memo. Model text does not own those URLs. The older complete daily reader, cached A4 PDF workbook, and confirmed Slack/email delivery remain available for days without a successor run; AI Engineering still uses that historical path. |
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
- Semantic/topic clustering beyond exact provider relations and exact
  same-artifact Development grouping.
- A learned ranking model. Production uses the transparent, deterministic
  `daily-rank-v2` ordering; learning weights or optimizing it against downstream
  labels remains deferred.
- Large discovered-account admission or recursive graph crawling.
- Mobile/responsive polish.
- Scheduled/unattended alerts or additional submission messages. Any new
  external send still requires Adi's explicit current-session approval.

These are valid future extensions, not prerequisites for proving the current
case-study thesis.

## Current Direction

The current work boundary is the deterministic Development projection and
`daily-development-rank-v1`. Exact Events remain the provenance unit; shared
release-specific artifacts merge same-day original posts for inspection and
ranking. The Feed opens on all grouped Developments and exposes every exact
source underneath. It can also assemble and show the exact future routing
input—source posts, substantive current same-author updates, and retrieved artifacts—while
keeping reaction text out and making no model call. Downstream routing, Insight,
editorial, PDF, and delivery replay is intentionally paused until this grouping
is reviewed.

Repository housekeeping is complete and archived
under [`docs/projects/archive/repo-housekeeping/`](projects/archive/repo-housekeeping/):
all runtime domains have direct package ownership, the code/data map is the
cold-start implementation index, local-data lifecycle is explicit, and fast
checks prevent the former flat source layout from returning. The later
attention-ranking redesign remains preserved as the historical Event-rank
lineage; rejected formula experiments remain decision history only.

The submission-critical daily-intelligence quality project is complete and
archived under
[`docs/projects/archive/daily-intelligence-quality/`](projects/archive/daily-intelligence-quality/).
It shipped deterministic X chronology, artifact disclosure lineage, verified
artifact excerpts, resumable Codex handoff, calibrated company direction,
and compact agent inspection. Its original submission checkpoint ran through
19 July; the later ranking migration produced exact-lineage editorial runs
through 21 July. The final five-Insight submission proof remains locked in its
[`submission selection`](projects/archive/daily-intelligence-quality/resources/submission-proof-selection-2026-07-19.md).
Busy-day tail selection and cross-day novelty remain disclosed limitations,
not blockers to the curated proof. Post-submission work is limited to reviewer
clarity, availability, and interview preparation, not another
intelligence-generation or harness cycle.

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
| Which Insights are the locked submission proof? | [`projects/archive/daily-intelligence-quality/resources/submission-proof-selection-2026-07-19.md`](projects/archive/daily-intelligence-quality/resources/submission-proof-selection-2026-07-19.md) |
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
