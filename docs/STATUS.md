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
  -> artifact-anchored Developments on one canonical day
  -> transparent daily Development ranking
  -> independent AI Engineering + Investment routing
  -> independent Investment and AI Engineering agents
  -> atomic audience-specific daily cohorts
  -> web brief, plus Investment PDF and explicit Slack or email delivery
```

The stored-X and canonical-artifact evidence paths are implemented. Current
analysis starts from ranked Developments projected from exact Event evidence
and accepted canonical artifacts. Exact Events remain immutable. Same-day
original posts merge only when they point to the same release-specific
artifact, and that artifact-based Development belongs to its earliest accepted
Event day rather than reappearing when another author links it later.

On 29 July the three stacked legacy Investment paths were consolidated into
one company-aware agent. Superseded editorial and candidate-decision modules,
stores, prompts, API fallbacks, and UI renderers were deleted rather than kept
dormant. AI Engineering then gained its own single-call, surface-linked agent
that judges each Development against seven assumed Aion surfaces. It shares
the Investment publication discipline and evidence packet but has its own
prompt, store, read projection, and renderer, with no PDF or delivery path.

The current published proof covers 24 days from July 5–28 for both audiences.
Each lane selects up to ten positively routed Developments per day; days with
fewer eligible candidates remain smaller rather than admitting irrelevant
work. The current readers expose 186 Investment Developments (64 surfaced)
and 212 Engineering Developments (27 surfaced). The result is
intentionally conservative: launches, pilots, provider
benchmarks, and early demand signals can fire a standing bet or touch an
engineering surface without claiming that a thesis-level threshold cleared or
that an implementation decision is already proven.

## Where the System Stands

| Layer | Status | What is established |
| --- | --- | --- |
| Registry | Implemented, inspectable, and manually extensible | One entity can own multiple channels; structural kind and Registry admission are separate; rejected records remain reversible and reason-bearing. The Registry UI/API can now intake one X profile through the combined evidence screen or a reason-bearing direct admission, with exact-handle idempotency and durable attempt/model telemetry. The current checkpoint contains 2,630 auditable identities: 2,431 active people, 160 active channel-backed organizations, and 39 reason-bearing rejections. The lean World's Fair 2026/2024 cohort contributes 423 people; unresolved company labels stay person facts rather than fake organizations. Conference inclusion is provenance, not rank or vote weight, and inactivity alone is not a rejection gate because dormant experts can still contribute useful outgoing-follow evidence. |
| Trusted-following graph | Evaluated candidate generator | The current immutable incremental snapshot contains 2,832,858 outgoing-follow edges from 2,558 complete source accounts resolving to 2,521 voting entities. Entity-union overlap is the accepted inspectable support feature across 2,524 active X-addressable Registry targets, including 38 zero-support targets; personalized PageRank remains a diagnostic, not truth. |
| X evidence store | Implemented source boundary | Raw provider evidence is preserved locally and normalized into replayable posts and relations. X is the only implemented discovery source today. |
| Exact event projection | Implemented and regression-tested | Provider-declared evidence is stored as root-owned structural forests, not unrestricted connected components: quote/retweet reactions attach to one source, only the source author's replies extend its thread, and every member has at most one structural parent. Third-party replies remain in the ledger but cannot import their own branch or bridge independent roots. The product publishes each Event exactly once on its earliest canonical source day; later activity appends to that Event without creating another dated candidate. The current reviewer window is one frozen July 5–28 publication: Feed `ecd737fede29…` and Event `615269522f9d…`. |
| Development projection + daily rank | Implemented grouping-only audit surface | `/api/developments` and `/evidence/feed` derive Developments from exact Events plus accepted canonical artifacts. Independently authored original posts merge only when they share the same release-specific artifact; generic host roots are rejected as anchors. An artifact-based Development is published only on the artifact's earliest accepted Event day, and both audience stores reject reuse of one Development ID across days. Exact Event IDs, posts, activity, and artifact lineage remain inspectable underneath. `daily-development-rank-v1` orders each day by distinct Registry participants across every source Event, mean participant network position, maximum public interactions on one source post, then stable Development ID. Original authors, quote authors, and reposters each count once. There is no organization bonus, scalar score, or weighted blend, and the projection needs no separate database yet. |
| Canonical artifact library | Complete supported pass + operator index | Outbound primary-resource links are conservatively canonicalized, source-linked, fetched once, snapshotted, and replayable. The current Event-native import contains 6,298 accepted source observations, 6,304 disclosures, and 5,378 canonical artifacts with zero import failures. One shared extraction validator rejects placeholder-dominated bodies and deterministic bot, consent, authentication, client-rendering, and error shells before they become packet evidence; immutable raw responses remain preserved. |
| Feed audience routing | v15 July 5–28 production coverage complete | One frozen Evidence publication feeds 24 top-100 daily runs containing 2,339 completed Developments with zero unresolved failures: 167 both, 92 Engineering-only, 46 Investment-only, and 2,034 neither. The deterministic gate completed 1,717 packets without a model call: 1,472 contained unsupported native media, 153 were short unsupported text, and 92 had only unavailable linked evidence. The remaining 622 Luna/medium calls cost $3.044634. |
| Audience Insight generation | Investment agent v15 published for July 5–28 | The Sol/xhigh projection selects up to the ten highest daily ranks with a positive Investment route—not the union-positive Feed—then screens all 37 companies and retrieves only plausible complete memos. The 24 complete publications contain 186 Developments: 64 surfaced and 122 suppressed. Direction comes from the cited memo-owned bet; the daily agent decides the causal connection and whether its exact materiality threshold cleared. The current publications consumed 4,809,068 input tokens, including 1,218,283 cached tokens, and cost $27.521637. Selection skips a Development already owned by another published day; a day remains below ten when no additional eligible candidate exists. Complete multi-day cohorts publish in one atomic transaction and only the current prompt version can satisfy or render a publication. Qualitative calibration across marginal company connections remains the main unproven boundary. |
| AI Engineering Insight generation | Engineering agent v2 published for July 5–28 | One Sol/high call per Development judges up to the ten highest Engineering-routed daily candidates against the seven assumed Aion surfaces in `docs/references/aion-surfaces.json`. The 24 complete publications contain 212 generated candidates: 27 surfaced and 185 suppressed. They consumed 663,081 input tokens and cost $5.995455. Each surfaced result names at most two concrete surfaces and explains what engineering decision the evidence could change; suppressed results preserve a reason. The lane has its own exact traces, strict validation, atomic publication, read projection, and backend regression tests. It intentionally has no company memo loop, materiality gate, PDF, or delivery path. |
| Prompt-cache operations | Implemented and live-verified | Cacheable jobs keep stable 1,024+ token prefixes first, use deterministic keys, serialize within a key, and record Responses `cached_tokens`. Registry jobs now use eight cache lanes instead of 64; audience routing is single-key/cache-first by default; Insight refresh runs one lane per audience prompt. The 27 July different-input canary observed 3/4 Luna and 4/4 Terra warm hits through the shared Azure-backed LiteLLM route. `fli prompt-cache-canary --no-input` makes the check repeatable; misses remain a measured best-effort provider condition rather than proof that a model lacks caching. The authoritative contract, current proof, incident history, and troubleshooting checklist live in [`prompt-caching.md`](references/prompt-caching.md). |
| Investment company context | Complete 37-company research set with 176 binary standing bets | BIT Lens and the Investment read path consume one `company-memos-v3` corpus. Its 176 pre-registered bets have 127 upside and 49 downside directions, zero `mixed` labels, exact thresholds, watchpoints, and source lineage. Direction is owned by the memo and resolved from `ticker + bet_id`; the daily model cannot restate or contradict it. A reproducible Sol/xhigh ledger preserves every reclassification and the source hash used to rebuild the corpus. |
| Insight path consolidation | Complete; one path in code and data | Each audience has exactly one generator and no fallback tier. `fli.insights` contains `investment_agent`, `investment_agent_runs`, `engineering_agent`, `engineering_agent_runs`, `company_context`, `pdf_report`, and `cli`; roughly 9,000 lines of superseded editorial, daily-runner, Codex App Server, consolidation, and candidate-decision code were deleted with their tests, prompts, and stores. `/api/insights` dispatches on audience to one of two stores, the SPA renders one component per `content_kind`, and an audience without a current run returns an explicit reason instead of older content. |
| Insights UI and delivery | Two audience readers; Investment-only PDF and delivery | Each surfaced Investment Development leads with its agent-written headline and collapsed causal mechanisms. Opening a mechanism shows every retained company, the memo-owned green upside or red downside direction, exact bet link, model-written impact, and either `Review thesis` when the threshold cleared or `Early signal` when it did not. The AI Engineering reader shows the shared Feed rank and evidence, then links each concrete landing into the BIT Lens Aion map. A compact `Brief \| Suppressed` switch lets either audience audit rejected Developments and the agent's stored reason without mixing them into the brief. Evidence, memo, bet, and surface URLs remain application-owned and deterministic. The A4 PDF workbook and confirmed Slack/email delivery consume only the current Investment publication; those actions remain disabled for Engineering. |
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

The current work boundary is qualitative calibration of two audience-specific
judgments over one deterministic Development projection. Exact Events remain
the provenance unit; release-specific artifacts merge original posts on one
canonical day, and `daily-development-rank-v1` supplies the shared order.
Investment v15 and AI Engineering v2 are both published for July 5–28. The
next step is to audit marginal company connections, surface
landings, and suppressions rather than add another generation path. The binary
memo direction, exact Investment threshold, and seven-surface Engineering map
should remain fixed during that calibration.

Completed reasoning is preserved in the sharded build log and the surviving
trackers under [`docs/projects/archive/`](projects/archive/). Removed project
paths are not active contracts. Use `scripts/build-log.py search` when a
historical decision is not represented by a surviving tracker. The
attention-ranking redesign remains the historical Event-rank lineage; current
Investment work uses the company-aware path and does not restore the deleted
editorial system.

Interview work has decomposed a ranked Development into two defensible
audience paths. Investment screens a compact 37-company index, opens only
plausible complete memos, and returns bet-linked causal connections.
Engineering compares the same Development packet with seven explicit Aion
surfaces and returns only decision-changing landings. Both are now proven
across multiple complete daily cohorts; the next boundary is qualitative
false-positive and miss analysis, not more architecture.

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
