# Seven-day envelope-triage validation

Date: 2026-07-13  
Model: `gpt-5.4-mini`, medium reasoning, through shared LiteLLM  
Prompt: `envelope-triage-v1` (unchanged from the calibration)  
Cohort: top 100 attention envelopes for each complete UTC day, 2026-07-05
through 2026-07-11

## Outcome

The frozen one-stage triage contract completed all 700 rows. It kept 487 and
dropped 213. After deduplicating event IDs across overlapping daily snapshots,
that is 407 unique kept events and 209 unique dropped events. Kept envelopes
identify 737 unique signal posts for later artifact resolution and extraction.

This is enough downstream inventory. Do **not** expand to ranks 101–200 before
the extraction oracle and one-day cited-insight path work end-to-end. The
lowest tested band still contains useful evidence, but another 700 calls would
primarily enlarge an already oversized extraction queue rather than answer an
open validation question.

## Per-day results

| UTC day | Keep | Drop | Repair | Cache read ratio | Proxy-reported accepted-run cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2026-07-05 | 42 | 58 | 0 | 52.30% | $0.197965 |
| 2026-07-06 | 69 | 31 | 0 | 51.89% | $0.265892 |
| 2026-07-07 | 81 | 19 | 0 | 51.62% | $0.256395 |
| 2026-07-08 | 72 | 28 | 0 | 51.59% | $0.295891 |
| 2026-07-09 | 78 | 22 | 1 | 43.71% | $0.367463 |
| 2026-07-10 | 83 | 17 | 1 | 46.41% | $0.381345 |
| 2026-07-11 | 62 | 38 | 0 | 50.18% | $0.301571 |
| **Total** | **487** | **213** | **2** | **49.6%** | **$2.066522** |

The accepted run rows contain 1,555,506 input tokens, including 770,560 cache
reads. The cost total is the sum stored from LiteLLM response headers for the
successful logical rows, including the two schema-constrained repair calls.
One diagnostic call added $0.0206595. Four pre-fix responses that failed local
semantic validation predated repair telemetry and are not included in the run
total; this is recorded rather than presenting the accepted-row sum as total
experiment spend.

## Yield by attention rank

| Attention rank | Keep | Drop | Keep rate |
| --- | ---: | ---: | ---: |
| 1–20 | 106 | 34 | 75.7% |
| 21–40 | 105 | 35 | 75.0% |
| 41–60 | 100 | 40 | 71.4% |
| 61–80 | 91 | 49 | 65.0% |
| 81–100 | 85 | 55 | 60.7% |

Attention remains a useful candidate-ordering signal, not a relevance
classifier. Useful yield falls gradually instead of reaching a clean cutoff.
The ranks 81–100 audit found real releases, benchmark claims, incidents,
papers, interviews, policy positions, and first-hand product reports alongside
banter, event announcements, vague promotion, and off-topic material.

## Decision and category behavior

| Category | Rows |
| --- | ---: |
| `technical_development` | 218 keep |
| `source_material` | 89 keep |
| `attributed_view` | 79 keep |
| `business_or_people` | 56 keep |
| `strategy_or_policy` | 31 keep |
| `safety_or_incident` | 14 keep |
| `insufficient_substance` | 102 drop |
| `off_topic` | 61 drop |
| `banter_or_meme` | 50 drop |

The contract cleanly separates keep and drop categories. Manual review of all
55 drops in ranks 81–100 found the decisions directionally sound. Borderline
items were mostly evidence-boundary limitations—unnamed conference papers,
image/video demonstrations whose content was not captured, and unlabeled
links—rather than a reason to relax the text-only gate.

## Cross-day stability

- 700 daily rows represent 616 unique event IDs; 84 rows repeat an event seen
  in another daily snapshot.
- 80 events occur on multiple days. Decision consistency is 100%: no repeated
  event switched between keep and drop.
- 75 repeated events had identical frozen inputs. Five gained or lost evidence
  across snapshots.
- Four repeated events changed primary category while staying `keep`; one had
  identical input and three had changed evidence. Category is a routing hint,
  not a publication claim.

Production extraction should deduplicate by `(event_id, input_sha256)`: reuse
an existing decision for identical evidence, but evaluate a new snapshot when
its evidence hash changes.

## Provenance repair finding

One OpenAI launch envelope appeared on both 2026-07-09 and 2026-07-10. The
model repeatedly selected a real supplied post semantically but transcribed
one digit of its 19-digit post ID incorrectly. The application did not guess
the intended ID. It now performs at most one narrowly scoped repair call only
for this exact validation failure, constraining the structured-output enum to
the frozen envelope's valid IDs. Normal calls and the stable cacheable prompt
remain unchanged. Each repair, tokens, and combined proxy-reported cost are
stored explicitly.

## Storage and replay

Each daily run is immutable and resumable at:

`data/derived/cited-insights/triage/triage-<UTC-day>-top100-v1/triage.db`

Every database stores run metadata, cohort and input hashes, full frozen
envelopes, rendered inputs, decisions, selected post IDs, reasons, response
IDs, model, token/cache usage, response-header cost, request tags, errors,
attempts, and repair count. These are derived audit stores; they do not mutate
the Feed evidence database or Registry.

## Decision

Freeze triage. The next step is the five-record extraction oracle followed by
artifact resolution and `insight-v1` extraction for one day. The long tail and
ranks 101–200 stay available as later recall expansion if the delivered daily
briefing lacks 3–5 excellent cited insights.
