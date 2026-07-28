# Learnings — Interview Readiness Audit

Operational notes for anyone picking this up. Saves re-discovering the same
things.

## Closeout Summary

This project combined a read-heavy interview audit with a small amount of UI
work. Its strongest contribution was measurement: it separated upstream
coverage limits from downstream selection quality and showed where model
judgment overrode deterministic evidence rank for legible reasons.

The tracker was archived as superseded on 2026-07-28, not because every
original preparation task was complete. The pipeline changed materially after
the audit: exact Events now project into shared-artifact Developments, daily
Development rank is deterministic, the top 100 are routed by the
self-contained Luna v13 contract, and all 37 Investment companies have
source-bearing memos. Future implementation should start from those current
contracts instead of executing the old B0–B10 list literally.

## How to query the live data

The service runs at `http://127.0.0.1:8797`. Everything in `findings.md` came
from it or from the repo databases.

**Parameter name is `date`, not `day`.** `/api/insights`, `/api/artifacts` and
`/api/events` all require `date=YYYY-MM-DD`. Passing `day` returns a 422 with a
`{"detail": [...]}` body, which is easy to mistake for an empty result.

**Pulling a full corpus.** Seventeen days of one audience:

```bash
for d in 2026-07-05 ... 2026-07-21; do
  curl -s "http://127.0.0.1:8797/api/insights?audience=investment&date=$d&status=kept"
done > tmp/inv_kept.jsonl
```

The responses concatenate without separators. Split with
`raw.replace('}{', '}\n{')` before parsing line by line.

**Two different statuses, two different payloads.** This tripped up an earlier
session badly enough to be worth stating plainly:

| `status=kept` | `status=suppressed` |
| --- | --- |
| `content_kind: daily_editorial` | `content_kind: candidate_decisions` |
| the published brief | the insight-editor gate |
| 21 Jul: 66 reviewed → 6 published, 58 declined | 21 Jul: 66 all → 30 kept, 36 suppressed |

They are sequential pipeline stages, not two halves of one list. Their
rejection counts for the same day are different and both correct. See the
recorded Decision in `tasks.md` about why they are not one click apart in the
UI.

**Useful shapes:**

- `declined[]` items carry `event_id`, `feed_rank`, `author`, `excerpt`,
  `reason`. The written reason is the highest-value field in the whole API for
  demonstrating judgment.
- `items[].events[]` carry `feed_rank` and `role`
  (`primary` / `supporting` / `context` / `counterevidence`).
- `/api/events?date=...` returns `daily_rank_total` (1,360 on 21 July) and
  `routing_counts` — the denominators for any funnel claim.
- `/api/registry` returns `entities`, not `items`, and needs pagination
  (`limit=400`) to see all 2,400+.
- `/api/insights/dates` carries `item_count`, `candidate_count`,
  `included_candidate_count`, `not_selected_candidate_count` per day.

## What made findings strong or weak

**Free measurements beat expensive ones.** The two most useful results in this
audit — the concentration diagnosis (finding 1) and the rank correlation
(finding 9) — cost nothing. Both were regexes and a Spearman over data already
stored. Before proposing any spend, check whether the question is answerable
from what is already on disk.

**Compare kept against declined, not kept against nothing.** The concentration
finding looked damning at 83% mega-cap until the declined pool was measured too.
Kept Insights reach outside the mega-caps 16x more often than declined
candidates. A single-sided number will usually mislead.

**Anchor model judgment to a deterministic quantity rather than replacing it.**
Finding 9 is the template: the editorial rank cannot be made formulaic without
becoming the "arbitrary weighted sum" the prompt calls a red flag, but it can be
correlated against `daily-rank-v2` and the disagreement inspected. Low
correlation plus a legible direction is a much stronger result than a formula.

**Read `docs/references/daily-intelligence-batch-audit-2026-07-05-17.md`
early.** It was found late in this audit and it independently contained two of
the findings, with better diagnoses and — for finding 12 — five named defects.
Eleven pipeline agents each wrote a retrospective after their day's run; the
"Agent feedback" and "Follow-up implementation status" sections are the closest
thing the repo has to a harness-gap log. Three of six follow-ups are still
deferred (items 2, 4, 5).

## Tooling gotchas

- `timeout` is not available on this macOS box.
- Use `.venv/bin/python` for ad-hoc analysis; there is no `python` on PATH.
- `agent-browser eval` with `scrollIntoView` sometimes does not move for
  already-visible elements. `window.scrollTo(0, N)` is more reliable.
- CSS custom property is `--font-mono`, not `--mono`. `--border-strong` exists.
- Keep browser captures under `tmp/` and delete them after each batch.

## Working agreements with Adi

- One idea at a time. No information dumps. He will say when he wants depth.
- Verify before asserting — every number needs the command that produced it.
- Corrections matter more than confidence. Several claims in this session were
  wrong on first pass (the funnel-view gap, "dedup doesn't work", the
  concentration cause, "two of six follow-ups") and were caught by measuring.
  Say so plainly when it happens.
- Audit-only unless he explicitly asks for implementation. The frozen 17-day
  corpus is the demo and must not break.

## Recommended Follow-Up

- Evaluate downstream judgment with the upstream router held stable. Tuning
  routing before observing company mapping and Insight suppression optimizes
  one stage in isolation.
- Preserve negative verdicts. An auditable "no affected company" or
  "insufficient technical consequence" is part of the product, not discarded
  model exhaust.
- Keep one narrow project tracker for the current pipeline boundary. Large
  interview-readiness lists become stale quickly when the underlying lineage
  changes.
