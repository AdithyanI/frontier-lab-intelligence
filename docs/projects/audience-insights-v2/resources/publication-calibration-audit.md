# Independent publication calibration audit

Status: implemented contract for the Audience Insights v2 calibration,
holdout, and production quality gates. This audit is an independent quality proof; it is not the pre-editor
item-review filter and it does not reuse that filter's judgments.

## Frozen cohort

One audit database reads exactly one immutable audience run and copies:

- every active `publication_selection` item (the immutable `daily_selection`
  remains the editor's original shortlist when a padding tail is reconciled);
  and
- up to five highest-Feed-ranked candidates rejected by the completed
  pre-editor item review.

The highest rank is used only to choose a deterministic reject sample. The
auditor input contains an opaque audit ID, the audience, sanitized frozen
evidence blocks, and the extracted audience item. It excludes Feed rank,
selection/rejection state, source candidate ID, original review judgments and
rationale, editorial rank, editor reasons, popularity, engagement, and day-set
audit metadata. Investment and AI Engineering runs remain separate audits.

## Independent model boundary

- Module: `fli.audience_insight_publication_audit`
- Prompt: `audience_insight_publication_auditor_v1.txt`
- Prompt version: `audience-insight-publication-audit-v1.0`
- Schema version: `audience-insight-publication-audit-output-v1`
- Default route: `gpt-5.6-luna`, high reasoning
- Cache namespace: `audience-insights-v2-<audience>-publication-audit`
- Metadata job tag: `job:publication-calibration-audit`

The strict output independently judges citation fidelity, attribution
fidelity, epistemic discipline, audience usefulness, actionability, and
specificity. Every request attempt stores hashes, prompt/model versions, raw
output, response IDs, token/cache telemetry, request tags, proxy-reported cost,
and any error in the audit database. Completed items are never called again;
schema failures can be retried once and then become terminal rejects.

## Gate and diagnostics

For published selections, the audit requires complete coverage, zero
mechanical or model-judged citation failures, zero attribution failures, zero
epistemic failures, and at least 80% passing usefulness, actionability, and
specificity together. Dimension-level ratios are also reported. Same-day and
cross-day duplication and padding remain the separate day-set gate's job.

A sampled pre-editor reject is counted as a false negative when this fresh
auditor passes all six dimensions and the citation binds mechanically. These
counts diagnose an over-strict filter; they do not automatically publish the
candidate. Every such result requires an exact, human- or agent-reviewed
`adjudications.json` beside the audit. `would_enter` remains blocking;
`would_not_enter` is accepted only when the exact immutable item would not enter
or materially diversify the set. The file binds source contract, audit cohort,
and audit-result hashes, so it cannot clear changed evidence or outputs.

## Unattended commands

```bash
RUN_DIR=data/derived/audience-insights-v2/2026-07-11/investment/RUN

fli audience-insight-audit freeze \
  --audit-id publication-audit-RUN \
  --source-run-db "$RUN_DIR/insights.db" \
  --audit-db "$RUN_DIR/publication-audit-v1/audit.db"

fli audience-insight-audit run \
  --audit-db "$RUN_DIR/publication-audit-v1/audit.db"

fli audience-insight-audit run \
  --audit-db "$RUN_DIR/publication-audit-v1/audit.db" \
  --retry-failed

fli audience-insight-audit summary \
  --audit-db "$RUN_DIR/publication-audit-v1/audit.db"

fli audience-insight-audit validate \
  --source-run-db "$RUN_DIR/insights.db" \
  --audit-db "$RUN_DIR/publication-audit-v1/audit.db" \
  --expected-selected-count SELECTED_COUNT
```

`freeze` never calls a model. The audit must be frozen separately for each
audience/day source run. Always pass the adjacent audit path explicitly: web
publication, audited editorial history, and the combined gate all require
`RUN_DIR/publication-audit-v1/audit.db`. The `run` command can finish its model
work while a false-negative adjudication is still missing; only `validate`
proves the exact fail-closed publication boundary and may authorize the next
chronological day.
