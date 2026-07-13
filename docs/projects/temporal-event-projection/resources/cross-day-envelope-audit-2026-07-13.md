# Cross-day Envelope Audit — 2026-07-13

## Finding

Exact grouping assigns one stable event ID correctly, but the day projection
loads every member of any cluster touching that day. Historical views therefore
include evidence collected later in the materialized run.

The bug is in the projection boundary, not the exact-clustering identity:

1. `event_day` selects clusters active on the requested day.
2. The read path then fetches all `event_member` and `event_link` rows for those
   cluster IDs without applying the requested day cutoff.
3. The root and attention candidate come from the selected day's Feed, while
   the displayed related evidence and `latest_evidence_at` come from the full
   cluster lifetime.

This produces a misleading hybrid: a day-specific score beside a future-aware
evidence bundle.

## Corpus Measurements

| Measure | Count |
| --- | ---: |
| Complete UTC days | 7 |
| Feed posts across date tabs | 10,552 |
| Envelope-day rows | 7,563 |
| Unique exact event IDs | 6,909 |
| Events present on more than one day | 581 |
| Rows occupied by multi-day events | 1,235 |
| Historical rows exposing future evidence | 655 |

Event span distribution:

| Active days | Unique events |
| --- | ---: |
| 1 | 6,328 |
| 2 | 519 |
| 3 | 54 |
| 4 | 6 |
| 5 | 1 |
| 6 | 1 |

## Concrete Regression Oracle

Anthropic's “A global workspace in language models” event:

- Stable event ID:
  `6f261e46230793d810476a22ff5c36884cd488b15fef26f2313e22cbb9105d60`
- Canonical/root post ID: `2074185348142280912`
- Root published: `2026-07-06T17:34:58Z`
- Current Monday attention: `99.4`
- Current Tuesday attention: `99.6`
- Current expanded evidence on both days: 72 members with
  `latest_evidence_at=2026-07-11T10:37:06Z`
- The Monday and Tuesday triage stores used the identical input SHA-256 and
  identical 48-related-post envelope.

Expected behavior after correction:

- July 6: stable root plus evidence published through July 6 only.
- July 7: same stable root, July 6 evidence as prior context, and July 7
  evidence identified as that day's continuation.
- Neither projection contains evidence from July 8–11.
- A weekly projection contains the canonical root and every deduplicated member
  through the week-end cutoff exactly once.

## Downstream Consequence

The bounded triage corpus contains 6,445 rows but 5,846 unique event IDs. It
also contains 452 repeated identical `(event_id, input_sha256)` inputs with zero
decision conflicts. A temporal snapshot contract can reuse identical decisions
and rerun only a genuinely changed event revision.

Daily insights can then distinguish a new event from a material update:

- first material snapshot: eligible for a new insight;
- later snapshot with no meaningful delta: no duplicate insight;
- later snapshot with a material delta: eligible for an update tied to the
  same canonical event.
