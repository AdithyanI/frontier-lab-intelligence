# Audience Insights v2 quality evaluation

Status: calibration and recall decisions complete; corrected chronological
production and canonical reconciliation in progress.

This is the immutable evaluation record for the two audience products. It
records failed attempts, frozen contracts, exact audits, and the expansion
decision. It is not a hand-edited insight output.

## Acceptance model

Audience Insights v2 separates five judgments that cover different failure
modes:

1. The application-owned citation binder proves that the supporting quote
   occurs uniquely in frozen evidence and binds its exact source identity,
   offsets, URL, and hash.
2. A rank-blind item reviewer screens every extracted candidate for claim
   fidelity, epistemic discipline, audience usefulness, actionability, and
   specificity. Investment and AI Engineering use different frozen reviewer
   instructions because their false-positive modes differ.
3. An audience-specific daily editor sees only all-five-pass IDs. It may select
   and order IDs but cannot rewrite claims or analysis. It may publish fewer
   than three items rather than pad a weak day.
4. A day-set reviewer checks duplicate stories, relative padding, and whether a
   thin set is honest. One deterministic tail-only reconciliation is allowed;
   iterative pruning and one-item-to-empty reconciliation are forbidden.
5. A separately stored, rank-blind Luna-high publication audit re-evaluates
   every selected item plus up to five high-Feed-rank reviewer rejects. Exact
   selected items require zero citation, attribution, or epistemic failures and
   at least 80% joint usefulness, actionability, and specificity. Apparent
   reject false negatives require hash-bound exact-item adjudication; the
   editor receives no credit for a hypothetical rewrite.

The deterministic combined gate consumes only frozen source DBs, adjacent
publication audits, and bound adjudications. It makes no model call.

## Frozen prompt families

| Boundary | Investment | AI Engineering |
| --- | --- | --- |
| Extraction | `investment-insight-v2.2` | `ai-engineering-insight-v2.2` |
| Daily editor | `investment-daily-editor-v2.1` | `ai-engineering-daily-editor-v2.4` |
| Item review | `audience-insight-item-review-v2.3` | `audience-insight-item-review-v2.4` |
| Day-set review | `audience-insight-day-set-review-v2.4` | same |
| Publication audit | `audience-insight-publication-audit-v1.0` | same |

Investment extraction uses Luna-high because preserved Luna-medium runs did
not follow the public-equity attribution and analysis contract reliably. AI
Engineering extraction uses Luna-medium. Item review, daily editing, day-set
review, and publication audit use Luna-high. Every attempt records model,
reasoning effort, cache namespace, tokens, cache reads/writes, reported cost,
response ID, raw output, and terminal failure state.

## Final calibration window

All superseded runs remain immutable under
`data/derived/audience-insights-v2/<day>/<audience>/`. The final exact runs are
identified by `final-calibration`, `holdout`, or `extension` in their run IDs.

### Investment

| Day | Role | Selected | Adjacent audit | Interpretation |
| --- | --- | ---: | --- | --- |
| Jul 5 | predeclared extension | 0 | pass; 3 rejects | honest thin day |
| Jul 6 | extension holdout | 0 | pass; 5 rejects | honest thin day |
| Jul 9 | calibration | 1 | pass; selected + 5 rejects | one Meta Muse Spark/Box story |
| Jul 11 | calibration | 0 | pass; 5 rejects + bound adjudication | honest thin day |
| Jul 13 | original untouched holdout | 0 | pass; 5 rejects | honest thin day |

The original Jul 13 holdout was preserved as a valid negative result. Before
inspecting more output, Jul 5 and Jul 6 were frozen as one unchanged extension
block, with Jul 6 declared as the extension holdout. No tuning occurred between
those dates.

The only Jul 6 all-five-pass item was a Palantir control/mission thesis. The
editor excluded it because it was standing context rather than a new product,
contract, customer result, financial disclosure, regulatory event, or dated
catalyst. Two independent exact-item reviewers agreed it would not enter.

The Jul 9 Muse Spark/Box item remains valid evidence of the calibration
mechanism, but a later senior-reader product review found that its immutable
analysis promoted a partner testimonial inside Meta's launch post into a
stronger demand/adoption signal than the primary evidence supports. It must not
survive the final production set merely to preserve nonzero yield. The
production closeout is therefore testing a primary-source commercial recovery
and otherwise keeps Investment honestly sparse; calibration history is not
rewritten.

### AI Engineering

| Day | Role | Selected | Adjacent audit | Interpretation |
| --- | --- | ---: | --- | --- |
| Jul 9 | final calibration | 1 | pass; selected + 5 rejects + 2 bound adjudications | GPT-5.6 Sol benchmark |
| Jul 11 | final calibration | 1 | pass; selected + 5 rejects | MuScriptor integration prototype |
| Jul 13 | untouched holdout | 2 | pass; selected + 5 rejects + 1 bound adjudication | RL training setup and initialization experiment |

AI item-review v2.4 was frozen after a preserved Jul 9 failure in which a named
API plus broad capabilities was incorrectly treated as actionable. The final
reviewer requires a concrete task, input/artifact/interface or failure mode, and
an operational success/failure condition.

The Jul 13 apparent false negative about Grok Build repository uploads was
useful and reproducible, but its exact third-party claim was written as
unqualified xAI product fact. Two independent reviewers agreed that source
metadata and a later caveat cannot repair missing claim-level attribution; the
ID-only editor cannot rewrite it.

## Combined gate v1.1

Manifest:
`data/derived/audience-insights-v2/calibration/combined-gate-v1.1/manifest.json`

Deterministic report:
`data/derived/audience-insights-v2/calibration/combined-gate-v1.1/report.json`

Result: pass.

- **AI Engineering — `standard_pass`:** four selected items across three days,
  selections on every day including the untouched holdout, 100% joint external
  quality, uniform contracts, and exact source/audit bindings.
- **Investment — `audited_sparse`:** the unchanged standard yield gate failed;
  the named sparse branch passed with five frozen days, one externally audited
  item, four explicitly honest zero days, a full five-reject zero-item holdout,
  uniform contracts, and no unresolved or would-enter false negative.

`audited_sparse` is not a standard pass or a quality waiver. It cannot pass an
all-zero window, a window under five days, a non-thin zero day, a missing/full
reject holdout audit, contract drift, stale binding, failed selected item, or
unresolved/would-enter reject. The standard thresholds remain three selected
items, two selected days, and at least one holdout selection.

## Investment coverage diagnosis

An independent read-only corpus review examined the exact final Jul
5/6/9/11/13 runs:

- 191 top-50 evidence packets produced 58 cited candidates and only three
  all-five-pass items; two were duplicate facets of the Jul 9 Muse Spark story
  and one was the correctly excluded standing Palantir thesis.
- All 191 roots were X posts. Across their evidence packets, 1,144 blocks were
  X content and only 39 were attached artifacts. There was no dedicated
  IR/filing/earnings/contract evidence lane.
- Common failures were generic Investment implications, dropped third-party
  attribution, unsupported causal premises, and vague watchpoints.
- The frozen rank-blind lower/article/drop sample produced no all-five-pass
  Investment item, so widening beyond top 50 is not supported.

The strongest recoverable underlying story was a Jul 6 secondary summary of a
reported Anthropic 20-year, $19B, roughly 400 MW TeraWulf lease. The exact item
correctly failed because it stated the secondary report as fact. This is the
concrete post-MVP case for resolving linked primary reports and adding a bounded
commercial evidence lane: IR, filings, earnings, regulation, named contracts,
pricing, and adoption metrics. It is not evidence for lowering the publication
bar or admitting thesis commentary into the daily signal set.

## Rank-blind recall audit

Run:
`audience-insights-v2-recall-current-contract-2026-07-15`

Database:
`data/derived/audience-insights-v2/recall/audience-insights-v2-recall-current-contract-2026-07-15/recall.db`

- Frozen sample: 73 evidence packets / 146 audience evaluations.
- Strata: 36 lower-kept ranks 51–100, 10 additional X Articles, and 27 dropped
  candidates across all nine days.
- The current-contract replay completed 144 determinate evaluations and
  retained two deterministic schema-terminal cells as unknown rather than
  negative evidence: AI Engineering Jul 6 rank 69 and Investment Jul 13 rank
  80. Their predeclared containment windows were top 75 and top 100.
- AI Engineering produced two all-five-pass lower-rank items. Exact comparison
  found both `would_enter`: Jul 5 rank 84 entered the validated widened top-100
  day, and Jul 9 rank 100 entered the corrected-history top-100 day. Each
  affected chronological suffix was rebuilt rather than mixing old history
  with a widened day.
- Investment produced one all-five-pass lower-rank item, Jul 6 rank 69. Exact
  adjudication found `would_not_enter`: the partnership announcement was useful
  standing thesis context but did not contain a bounded daily public-equity
  implication or observable disclosure.
- No dropped sample justified publication for either audience. The result does
  not support global top-100 expansion; it supports only the exact bounded cells
  above.

Passing an isolated item rubric does not justify widening. A lower-ranked item
must actually enter or materially diversify its final higher-ranked daily set.
Any accepted widening reruns that day and every later day for the same audience
because audited editorial history changes.

## Production and closeout

Fresh production runs materialize chronologically from Jul 5 through Jul 13.
The next date starts only after the current run has an adjacent audit, any exact
adjudication/finalization, and strict read-only validation. Recall widening on
AI Jul 5 changed prior editorial history, so the affected AI suffix is being
rebuilt against the corrected audited history instead of accepting the earlier
otherwise-valid runs by recency.

The final web product is fail-closed behind one adjacent
`production-reconciliation-v2/manifest.json` and `report.json` pair. The
manifest must name all 18 audience/day cells, exact adjacent audits, optional
finalizations, and all 22 X Article snapshots. Twenty Articles must derive
exactly from the declared production-run event union. The Jul 10 rank-71
isRecord and Jul 11 rank-83 Loop Engineering Articles are the only additional
origins: their exact recall sample IDs and complete frozen recall-ledger hash
are manifest-bound, and they cannot be replaced by an arbitrary artifact
superset. The stored report must equal a fresh canonical evaluation
byte-for-byte. Until that pair exists and validates, the live Insights API
intentionally reports unavailable rather than guessing which superseding
directory is current. Runs with NULL proxy-reported cost remain ineligible;
only a numeric provider-reported zero is a known zero. The provider-safe AI
Engineering Jul 10 r4 rerun supersedes r2/r3, whose empty Nova fallback
responses left their exact costs unknown.

Exact closeout values intentionally remain pending until the canonical report
exists; copy them from that report, never from a directory scan:

- Base and effective published-item totals: **PENDING CANONICAL REPORT**.
- Candidate, completed, rejected, and failed totals: **PENDING CANONICAL REPORT**.
- Extraction/review/editor/audit input, output, cached, and cache-write tokens:
  **PENDING CANONICAL REPORT**.
- Provider-reported LLM cost and bound X Article credits: **PENDING CANONICAL
  REPORT**.
- Finalization count and exact per-audience/per-day yield: **PENDING CANONICAL
  REPORT**.

After reconciliation: build the SPA, use `agent-browser` against the live local
app for rendered two-audience QA, inspect every effective item at the senior-
reader product bar, update the exact values above, run `scripts/check-fast.sh`,
and archive the project.
