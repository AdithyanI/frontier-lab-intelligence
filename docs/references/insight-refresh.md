# Investment Insight Refresh

Last verified: 2026-07-29

## Purpose

One path produces current Insights: the company-aware Investment agent. It
starts from Developments with a current positive Investment route, screens the
37-company compact universe, opens only causally plausible company memos, and
publishes one complete daily cohort.

This workflow does not collect X posts, rebuild Events or Developments, retrieve
artifacts, or run audience routing. Those upstream stages must already be
current.

AI Engineering has no current Insight generator. Its API returns an explicit
unavailable reason rather than older content.

## Inspect before spending

Read the live contract instead of assuming a prompt or schema version:

```bash
.venv/bin/fli insights contract --json --no-input
.venv/bin/fli insights summary --json --no-input
```

Resolve the exact Investment-routed cohort without model calls, trace writes,
database writes, or publication:

```bash
.venv/bin/fli insights run-investment-agent \
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
```

The runner:

1. warms the stable prompt prefix with one Development;
2. fans out the remaining targets with bounded parallelism;
3. writes every request, response, tool call, response ID, retry, token count,
   and reported cost under
   `data/derived/insights/investment-agent-traces/<day>/`;
4. validates and imports each completed result; and
5. publishes a day only when every selected Development completes.

Publication is atomic. A partial batch may store successful rows and traces,
but it cannot replace the visible daily cohort.

A retry runs the requested targets again and writes new traces. It does not
claim that completed model calls are free or automatically reused. Use
`--rank N` only for focused diagnosis of one current Investment-routed daily
rank; a single-rank run does not publish the whole day.

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
- every opened memo is used or appears in `rejected_after_memo`; and
- the UI, PDF, and delivery preview read the same published cohort.

## Current checkpoint

The published July 19–21 top-ten cohorts still use Investment agent v8/v9. The
active contract is v11, and only two unpublishing v11 proof rows currently
exist. The next refresh should therefore preview and then replace those three
published cohorts with one complete v11 run.

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
