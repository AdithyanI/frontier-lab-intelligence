# Final `daily-rank-v2` replay validation

Recomputed 2026-07-27 after the complete-Event migration and final tie-aware
network-position correction.

## Scope

- 17 complete UTC days: 2026-07-05 through 2026-07-21.
- 19,657 projected Events.
- 1,700 daily top-100 positions.
- 1,674 current v9 routing labels; the router's separate first-party freshness
  boundary omitted 26 selected Events.
- No X API request. The replay used the preserved local evidence snapshot.

## Primary-signal check

| Distinct trusted Event voters | Top-100 Events | Labeled | Routing-relevant | Hit rate |
| --- | ---: | ---: | ---: | ---: |
| 1 | 213 | 204 | 70 | 34.3% |
| 2 | 703 | 692 | 373 | 53.9% |
| 3–4 | 499 | 495 | 318 | 64.2% |
| 5+ | 285 | 283 | 204 | 72.1% |

The relationship is monotonic. This supports using distinct trusted
convergence as the first ranking layer. It is not a precision or recall
estimate: routing labels are model judgments and exist only inside the
rank-selected, freshness-eligible window.

## What actually decides the top 100

The first layer separating each selected Event from its adjacent lower-ranked
Event was:

| Layer | Events | Share |
| --- | ---: | ---: |
| Distinct trusted voters | 182 | 10.7% |
| Mean voter network position | 1,362 | 80.1% |
| Source-author network position | 22 | 1.3% |
| Maximum same-day one-post public interactions | 99 | 5.8% |
| Stable Event ID | 35 | 2.1% |

This makes the trade-off explicit: trusted-voter count defines the primary
bands, while voter network position does most ordering inside equal-vote
bands. Source authority and public response are late tiebreaks, and Event ID
supplies determinism only.

## Position contract

Network position is the six-decimal fraction of ranked canonical entities with
a strictly lower entity-union support count, divided by `total − 1`. Equal
support receives equal position. Raw support magnitude does not enter the
Event rank.

## Reproduce

```bash
.venv/bin/fli daily-rank evaluate --json --no-input
```

The authoritative reusable narrative lives in
`docs/references/scoring-validation.md`; this file preserves the project-close
replay checkpoint.
