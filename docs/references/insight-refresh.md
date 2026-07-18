# Insight Batch Refresh

Last verified: 2026-07-15

## Purpose

`fli insights refresh` turns the current positive audience routes into durable
Insight requests. It is deliberately downstream of Evidence and audience
routing: it does not collect posts, rebuild Events, retrieve artifacts, or
invent another Event representation.

The normal calibration loop is:

```bash
fli insights refresh \
  --through 2026-07-13 \
  --limit-per-day 10 \
  --dry-run \
  --json

fli insights refresh \
  --through 2026-07-13 \
  --limit-per-day 10 \
  --workers 8 \
  --json
```

After reviewing those results, expand the same day without repeating them:

```bash
fli insights refresh \
  --through 2026-07-13 \
  --all-routed \
  --workers 8 \
  --json
```

Use `--days 9` to select the same bounded cohort across the nine-day window.
The limit counts positively routed Events per day. An Event relevant to both
audiences produces two independent requests, so `request_count` can be larger
than `event_count`.

## Contract

- Only complete routing databases whose Event and Feed run IDs match the
  current publication are eligible.
- Selection is Feed-rank ordered and includes only positive routes for the
  requested audience or audiences.
- The same Event appearing on two requested days is a contract failure, not a
  silent deduplication; canonical Event publication must be repaired first.
- Every Event/audience run ID is derived from the Event, exact routing run,
  prompt/schema identity, model, and reasoning effort. Batch size is excluded.
- The complete cohort's exact request JSON freezes in
  `data/derived/insights/insights.db` before any model call starts. Completion
  or failure is then committed immediately per request.
- Rerunning the same command reuses completed local results and retries failed
  requests. Expanding from ten Events to all routed Events reuses the overlap.
- Requests execute in bounded parallel. Progress goes to stderr; the final
  stable JSON object goes to stdout.
- `--dry-run` reads and validates the cohort but does not create the Insight DB,
  request dumps, or model calls.
- Result telemetry separates new `model_requests` and incremental cost/tokens
  from `reused_results`; historical spend is never counted as new batch spend.

The default model remains `gpt-5.6-terra` with high reasoning while calibration
is active. A new routing publication, prompt version, model, or reasoning effort
creates new immutable request identities rather than relabeling old results.
