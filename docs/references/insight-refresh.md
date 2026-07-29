# Audience Insight Refresh

Last verified: 2026-07-29

## Purpose

Two independent agents produce current Insights from the same frozen
Development and audience-routing lineage.

- Investment starts from a positive Investment route, screens the 37-company
  compact universe, opens only causally plausible company memos, and returns
  bet-linked read-throughs.
- AI Engineering starts from a positive Engineering route and compares the
  Development with the seven versioned Aion surfaces in one model call.

This workflow does not collect X posts, rebuild Events or Developments, retrieve
artifacts, or run audience routing. Those upstream stages must already be
current.

## Inspect before spending

Read the live contract instead of assuming a prompt or schema version:

```bash
.venv/bin/fli insights contract --json --no-input
.venv/bin/fli insights summary --json --no-input
```

Resolve either exact routed cohort without model calls, trace writes, database
writes, or publication:

```bash
.venv/bin/fli insights run-investment-agent \
  --through 2026-07-21 \
  --days 3 \
  --top-ranked 10 \
  --dry-run \
  --json \
  --no-input

.venv/bin/fli insights run-engineering-agent \
  --through 2026-07-21 \
  --days 3 \
  --top-ranked 10 \
  --dry-run \
  --json \
  --no-input
```

The dry-run output is the spend boundary. Inspect `targets`, `prompt_version`,
`model`, `reasoning_effort`, and `counts.requested` before removing
`--dry-run`.

## Run the cohort

```bash
.venv/bin/fli insights run-investment-agent \
  --through 2026-07-21 \
  --days 3 \
  --top-ranked 10 \
  --workers 6 \
  --json \
  --no-input

.venv/bin/fli insights run-engineering-agent \
  --through 2026-07-21 \
  --days 3 \
  --top-ranked 10 \
  --workers 6 \
  --json \
  --no-input
```

The runner:

1. warms the stable prompt prefix with one Development;
2. fans out the remaining targets with bounded parallelism;
3. writes every request, response, tool call, response ID, retry, token count,
   and reported cost under the audience's trace directory in
   `data/derived/insights/`;
4. validates and imports each completed result; and
5. publishes a day only when every selected Development completes.

Publication is atomic. A partial batch may store successful rows and traces,
but it cannot replace the visible daily cohort.

The v15 Investment agent uses progressive disclosure. Its first turn receives
the complete Development and compact standing-bet titles for all 37 companies.
It may request zero to eight full company memos. The continuation then returns
only:

```text
headline · what_changed · decision
connections[].mechanism
connections[].companies[].ticker
connections[].companies[].bet_id
connections[].companies[].threshold_met
connections[].companies[].impact
no_match_reason
```

Direction is not generated per Development. Every cited `bet_id` must belong to
the named company, and readers resolve its memo-owned binary direction. A false
threshold is an early signal; true means the memo's explicit gate is already
established and the thesis deserves review now.

A retry runs the requested targets again and writes new traces. It does not
claim that completed model calls are free or automatically reused. Use
`--rank N` only for focused diagnosis of one current audience-routed daily
rank; a single-rank run does not publish the whole day.

The Engineering agent has no memo tool loop. Its one call receives the complete
Development and the complete seven-surface map, then returns `surface` with at
most two decision-changing landings or `suppress` with one reason.

## Verify after the run

Confirm durable state:

```bash
.venv/bin/fli insights summary --json --no-input
```

Confirm the live read model:

```bash
curl -s \
  "http://127.0.0.1:8797/api/insights?audience=investment&status=all&date=2026-07-21"
```

Check that:

- the date appears in `published_days`;
- the published `prompt_version` matches the live contract;
- the candidate count matches the dry-run target count;
- surfaced and suppressed Developments sum to the complete cohort;
- every surfaced company cites a valid bet from a memo the run opened;
- direction shown in Insights exactly matches the cited BIT Lens bet;
- `threshold_met` is true only when the Development establishes the memo's
  threshold rather than merely firing the bet; and
- the UI, PDF, and delivery preview read the same published cohort.

## Current checkpoint

The active Investment contract is v15 over `company-memos-v3`: 37 companies
and 176 binary standing bets. The active Engineering contract is v2 over seven
versioned Aion surfaces. One frozen July 5–28 lineage currently publishes 186
Investment candidates (64 surfaced) and 212 Engineering candidates (27
surfaced) across 24 complete daily cohorts per audience. Historical rows remain
auditable but cannot satisfy or render a current publication.

## Failure handling

- Authentication failures are terminal until the shared LiteLLM credential is
  repaired.
- Timeouts, connection failures, HTTP 408/409/429/499, and 5xx Responses
  failures use bounded, trace-preserving retries inside each target.
- A target that still fails leaves its day unpublished.
- Never infer success from stored rows alone; the publication and live API are
  the reader boundary.
- Never send Slack or email output without Adi's explicit approval in the
  current session.
