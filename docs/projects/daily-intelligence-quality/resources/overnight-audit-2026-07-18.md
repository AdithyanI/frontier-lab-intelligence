# Daily Intelligence Overnight Audit — 2026-07-18

## Purpose

This file preserves the full cross-day audit and independent reviewer feedback
from the July 5–15 daily-intelligence run. It is evidence for iteration, not a
claim that every suggested improvement belongs in the product.

The audit has two evidence levels:

- **Mechanically verified** findings were reproduced against the newest
  complete imported run for each day, the bound daily workspaces, Feed data,
  or current code.
- **Provisional reviewer judgments** are qualitative labels or heuristic
  queues. They are useful for targeted review but are not formal ground truth
  until adjudicated and stored item by item.

## Executive Conclusion

The harness is mechanically strong: all eleven days are imported, every routed
audience pair is dispositioned, selected Insights have citations, and the UI
can read the normalized results. Editorial quality is useful but uneven. The
highest-leverage defect is chronology: the daily agent can write the brief day
into a citation even when the source is months old, and validation accepts it.

The smallest correction is not to ban old evidence. It is to make source dates
application-owned and visible. A daily brief can contain either a new
development or a synthesis of dated evidence. The run date and evidence dates
must never be conflated.

## Mechanically Verified Baseline

The canonical baseline selects the newest complete imported run for each day.

| Metric | Result |
| --- | ---: |
| Days | 11 (2026-07-05 through 2026-07-15) |
| Candidate Events | 616 |
| Routed audience pairs | 945 |
| Selected Insights | 105 |
| Included Event/audience pairs | 260 |
| Not-selected Event/audience pairs | 685 |
| Citation records | 196 |
| Distinct citation URLs | 193 |

Selected Insight counts by day:

| Day | Events | Audience pairs | Insights | Citation records |
| --- | ---: | ---: | ---: | ---: |
| Jul 5 | 32 | 48 | 9 | 27 |
| Jul 6 | 56 | 84 | 9 | 32 |
| Jul 7 | 71 | 105 | 13 | 11 |
| Jul 8 | 68 | 118 | 13 | 10 |
| Jul 9 | 66 | 110 | 9 | 11 |
| Jul 10 | 57 | 89 | 10 | 13 |
| Jul 11 | 54 | 76 | 7 | 7 |
| Jul 12 | 41 | 60 | 7 | 8 |
| Jul 13 | 58 | 81 | 8 | 26 |
| Jul 14 | 56 | 84 | 10 | 39 |
| Jul 15 | 57 | 90 | 10 | 12 |

### Citation and research mix

| Citation kind | Records | Distinct URLs |
| --- | ---: | ---: |
| Event | 89 | 89 |
| Artifact | 103 | 102 |
| Context | 3 | 1 |
| Web | 1 | 1 |

- Thirteen selected Insights use only Event citations and no artifact, context,
  or new web citation.
- Only one web citation was persisted. This proves that little external web
  evidence reached the final stored briefs; it does **not** prove that agents
  performed no uncited web research.
- Eleven of 48 Investment Insights map one development to five or more
  companies. These broad baskets deserve causal-chain review; breadth alone is
  not proof that a mapping is wrong.
- Thirteen exact-artifact groups contain repeated instances of the same Event.
  This is a deterministic retrieval defect, not an editorial judgment.

### Chronology audit

The selected briefs contain 114 Event-citation uses referencing 89 stored Event
citation records. Comparing their declared `published_at` values to the exact X
post IDs in the bound Feed store gives:

| Result | Event-citation uses |
| --- | ---: |
| Correct date | 80 |
| Wrong date | 20 |
| Missing date | 14 |

- Eleven uses rely on a source more than seven days older than the brief day.
- Five uses rely on a source more than thirty days older.
- The oldest gap is 360 days.
- All 2,187 X-source references across the canonical daily workspaces resolve
  to their workspace's bound Feed run, so the immediate correction can use
  existing data rather than new crawling or model calls.

Representative reproduced failures:

1. **Jul 10 Thinking Machines financing.** The selected citation assigns
   `2026-07-10` to post `1945166365834535247`; Feed truth is `2025-07-15`.
   The later Jul 10 discussion may still support a current synthesis, but the
   financing must be framed as dated context.
2. **Jul 14 teacher workspaces.** OpenAI post `1991218197530378431` is from
   `2025-11-19`; Anthropic post `2077047278078931243` is from `2026-07-14`.
   The comparison can be useful, but it cannot say both products were
   introduced that day.
3. **Jul 13 CaMeLs.** Seb Krier post `2060811780721418707` is from
   `2026-05-30`, not Jul 13. Accurate timing exposes resurfaced evidence; it
   does not by itself determine whether the linked paper belongs in a brief.
4. **Other older-source examples.** The review flagged the Jul 14 Matei Zaharia
   source (Jun 13), OpenAI beneficial-RL material (Jun 18), a health evaluation
   (Jun 27), and GPT-5.6 material (Jun 26) for dated framing.
5. **Jul 15 current-source control.** GPT-Red, Anthropic's agentic-misalignment
   post, and Perplexity SPACE all have current Jul 15 roots. Their synthesis
   should remain valid after chronology becomes deterministic.

### Current code boundary

- `src/fli/insights/editorial_runs.py::prepare_workspace` writes the stored
  routing packet into each daily Event file without source timing.
- `src/fli/insights/cli.py::_enrich_post_dates` already enriches the older
  per-Event Insight path from `feed_post.published_at`.
- Routing's optional `posted` field is deliberately excluded from its evidence
  hash, so chronology can be projected without invalidating routing truth.
- `src/fli/insights/editorial.py` validates Event/artifact URL membership and
  ISO date syntax, but it does not compare citation dates with source truth.
- `editorial_citation.published_at` already exists. The first fix does not need
  an editorial database migration.

## What Worked

- Every routed-positive Event/audience pair has one recorded disposition. Sparse
  publication is inspectable rather than silent.
- The BIT context packet gives the daily agent a useful public-thesis baseline,
  complete audited portfolio context, a clear outside-portfolio boundary, and
  a human decision boundary.
- The Engineering context supports bounded next steps and decision rules.
- Frozen workspaces, exact artifact groups, lexical search, and Event inspection
  provide a reusable deterministic research harness.
- Schema and persistence validation are complete: imported runs use the daily
  editorial contract, selected ranks are contiguous, rank rationales are
  nonempty, and every selected Insight has Event links and citations.
- Jul 15 was the strongest reviewed day and is a useful positive control.
- The canonical reader is substantially clearer than the earlier intermediate
  reasoning UI; detailed evidence remains available without dominating the
  first read.

## Provisional Qualitative Review

These labels came from independent review of all 105 selected Insights. No
durable item-level adjudication file was produced, so use them as a queue.

| Day | Strong | Usable, needs work | Weak / likely suppress |
| --- | ---: | ---: | ---: |
| Jul 5 | 3 | 5 | 1 |
| Jul 6 | 5 | 3 | 1 |
| Jul 7 | 6 | 4 | 3 |
| Jul 8 | 5 | 7 | 1 |
| Jul 9 | 5 | 4 | 0 |
| Jul 10 | 2 | 5 | 3 |
| Jul 11 | 3 | 3 | 1 |
| Jul 12 | 1 | 4 | 2 |
| Jul 13 | 2 | 5 | 1 |
| Jul 14 | 4 | 5 | 1 |
| Jul 15 | 8 | 2 | 0 |
| **Total** | **44** | **47** | **14** |

The reviewers judged 29 of 57 Engineering Insights strong versus 15 of 48
Investment Insights. Treat that delta as a useful hypothesis: Engineering's
bounded actions transferred more reliably from technical evidence, while many
Investment notes stretched a frontier-AI development across a generic basket
of cloud, chip, networking, or security names.

### Fourteen weak-item review queue

- Jul 5 — NVIDIA capital/rack-roadmap “offset” causal title.
- Jul 6 — conceptual document-context layer.
- Jul 7 — China export controls; Muse visual-generation experiment; Arabic ASR.
- Jul 8 — tree-masked robotics episode packing.
- Jul 10 — stale Thinking Machines financing; repeated model-routing judgment;
  repeated browser-permission judgment.
- Jul 11 — unconfirmed OpenAI safety-personnel reorganization.
- Jul 12 — speculative open-model licensing restriction; unconfirmed Vera CPU
  plan.
- Jul 13 — speculative model-weight memory.
- Jul 14 — misdated teacher-workspace comparison.

Each requires an explicit `keep`, `rewrite`, `suppress`, or `defer` decision.
The queue should not be bulk-suppressed merely because a reviewer marked it
weak.

### Repeated cross-day judgments

- Model-routing judgment repeats across Jul 9, 10, 11, 12, and 14.
- Premium-model price compression repeats across Jul 9, 10, 11, and 14.
- Browser/permission-boundary trials repeat across Jul 9 and 10.
- Visual abstention repeats across Jul 11 and 12.
- The open-model thesis recurs on Jul 5, 6, 13, and 14 without consistently
  stating the incremental update.

Chronology must be fixed first. Cross-day story lineage is the next likely
retrieval improvement if these duplicates survive accurate timing.

### Potential false negatives / omissions to adjudicate

- OpenWiki Brains.
- CRUX open-world evaluations.
- Reverse Information Paradox.
- METR time-horizon methodology.
- “Improving Agents is a Data Mining Problem.”
- Cognition SWE-1.7 compaction.
- Liam Fedus intent-aware evidence capture.
- Goodfire factuality.
- Bounded Codex Goals.
- Together AI provisioned throughput.
- Entire's agent-scale Git benchmark.
- Current agent-reliability keynote.
- Radiology handover readiness.
- Context-pruning guidance.
- Prime Intellect first-party evidence that may belong with a TechCrunch item.
- Apple lawsuit evidence that may have needed web verification.
- Sierra's internal Pinecone agent, which may have merited deeper inspection.

These are recall-review candidates, not presumed misses. Review each against
the audience decision bar and the complete evidence packet.

### Other reviewer heuristics to verify before enforcing

- Ninety of 260 selected Event-link reasons were described as generic.
- 124 of 685 not-selected reasons matched generic language patterns.
- Stronger Investment notes tended to use a company-specific operating and
  financial transmission path; weaker notes often used a broad category
  basket.
- Some Engineering notes recommended work that may not match the actual stack,
  including ASR, local B200/B300 operation, LoRA training, robotics policy
  training, or cross-cloud GPU storage.

These observations need exact-item adjudication before they become validation
rules. Generic prose may still be correct; an unusual Engineering experiment
may still be useful.

## Convergent Reviewer Requests

Independent reviewers repeatedly wanted the following agent-facing support:

1. Deterministic source chronology and freshness cues.
2. Cross-day prior-Insight search or story lineage.
3. A compact review matrix for the complete day's candidates and dispositions.
4. Source-authority classification and corroboration cues.
5. A machine-readable current Engineering stack.
6. Company-specific BIT operating/financial driver context.
7. Structured suppression categories.
8. Warnings—not bans—for secondary-only or social-only selected Insights.
9. Claim-specific Event-link reasons.
10. A bounded helper for persisting web citations.
11. Exact-artifact member deduplication.
12. A rank-rationale ordinal consistency check.
13. Source-family/corroboration visibility.
14. Artifact-relevance warnings when a linked artifact does not establish the
    claim attributed to it.

Only item 1 belongs in the immediate milestone. Items 2–14 remain preserved for
evidence-led prioritization after chronology is calibrated.

### Artifact timing and relevance follow-up

The Paper Glider citation exposed a second boundary during calibration. The Jul
14 Event retained Romain Huet's Jul 14 Codex post, while the Jul 15 reply that
disclosed the Paper Glider showcase was correctly pruned. The artifact itself
survived because the old routing packet did not carry its disclosure lineage,
and the saved Insight then cited it generically for a task-cost/capacity claim
the showcase did not establish.

A mechanical audit found 19 future artifact attachments across the Jul 7, 8,
9, 10, 12, 13, and 14 packet cohorts. Five distinct future artifacts appeared
in nine saved Insight citation uses. The bounded correction is therefore:

1. project the accepted artifact candidate's exact disclosure post from the
   catalog into the daily workspace;
2. retain the artifact only when that disclosure post survives the source
   window; and
3. require every artifact citation to carry a short excerpt verified against
   frozen artifact text plus a specific statement of what it supports.

This does not infer the artifact's own publication date and does not add a
second LLM relevance gate. The catalog owns availability and lineage; the daily
agent owns semantic relevance behind a deterministic citation boundary.

## Minimal Chronology Contract

### Decision after calibration discussion

Adi chose a stricter daily-product boundary on 18 July: first-party X sources
older than seven calendar days are excluded from routing and daily editorial
packets, while raw Feed/Event evidence remains unchanged. The full-corpus audit
supports why this is narrower than a same-day-only rule:

- 2,274 of 12,715 Feed Events had an old root under a same-day test;
- only 465 Feed Events, 61 routed top-100 Events, and 35 union-positive Events
  had a root more than seven days old;
- 52 routed audience pairs were affected, of which 10 were included and 42
  were not selected; and
- nine selected Insights touched evidence more than seven days old, but none
  depended exclusively on it.

The application rule is source-level. A current same-author quote or reply may
replace an old root. Independently authored reactions cannot rescue the packet.
If no current first-party X source remains, the candidate is excluded before
the daily agent sees it. Artifacts are not assigned an age from retrieval or
link time; when an old root is replaced and artifact lineage cannot be proven
to the retained continuation, the defensive workspace projection drops it.

The contract below records the audit's earlier, looser proposal. Its timing and
citation requirements remain valid; its “warning, never exclusion” decision is
superseded by the seven-day policy above.

The first implementation should:

1. Version the daily workspace and add derived timing for every X source:
   `published_at`, `first_discovered_at`, and `first_discovered_day`.
2. Leave the original routing packet and all routing/evidence hashes unchanged.
3. Show compact timing in search results and full timing in `inspect-event`.
4. Autofill Event citation `published_at` from the exact frozen source URL;
   reject a conflicting supplied date; leave it null when unavailable.
5. Add one editorial rule: the brief day is a review/selection day. Older
   evidence may support a useful synthesis, but its age must remain explicit
   and the prose must not call it a same-day release.
6. Emit age as a review cue if useful, never as an automatic validity failure.

Do not add a required Insight-type enum until calibrated examples show that
accurate dates and prose still leave the reader confused.

## Calibration Cases

- **Jul 10 / Thinking Machines:** financing date correct; newer discussion may
  support a synthesis; the old raise is context rather than current launch.
- **Jul 13 / CaMeLs:** resurfaced May 30 source is visible; separately judge
  whether the paper is relevant enough to select.
- **Jul 14 / teachers:** OpenAI and Anthropic retain their different dates; the
  comparison remains possible with honest language.
- **Jul 15 / control:** current GPT-Red, Anthropic, and SPACE synthesis remains
  unchanged in substance.
- **Synthetic historical synthesis:** an Insight with entirely old sources
  validates when every date is correct and the writing presents it as synthesis.

Under the adopted policy, the Jul 10 packet keeps Mira Murati's Jul 10 quote and
reply but removes the 2025 financing root. The Jul 14 teacher packet is excluded
because its only first-party semantic source is the November 2025 root. The
synthetic entirely historical case is now intentionally invalid for a daily
workspace, though it remains useful evidence for a future research product with
a different time horizon.

## Prioritized Next Work

1. Implement and test the minimal chronology contract.
2. Run only the calibration cases.
3. Decide whether an explicit synthesis label is still necessary.
4. Adjudicate the 14 weak items and strongest omission candidates.
5. Select the best 3–5 submission Insights.
6. Take later harness items only when they improve that proof before the
   deadline.
