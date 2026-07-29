# Workflow Economics

Last verified: 2026-07-29

This is the glanceable cost map for the current Frontier Lab Intelligence
workflow. It separates measured spend from provider estimates and local replay
work. Exact run telemetry is authoritative; these are dated checkpoints, not
price guarantees.

## Current Development Routing

The July 5–28 `audience-routing-v15` top-100 stores contain 2,339 completed
Developments with zero unresolved failures: 167 both audiences, 92
AI-Engineering-only, 46 Investment-only, and 2,034 neither. The deterministic
evidence-readiness gate handled 1,717 packets without an LLM call: 1,472
contained native media the system does not inspect, 153 were short unsupported
text, and 92 had only unavailable linked evidence.

The remaining 622 `gpt-5.6-luna` medium calls reported 2,039,826 input tokens,
2,032,543 cache-write tokens, 166,390 output tokens, zero cached-input hits,
and $3.044634. The refresh reused stored X and artifact evidence and made no
provider collection calls.

## Current Investment Agent

The company-aware agent uses `gpt-5.6-sol` at xhigh reasoning. Each Development
screens the compact 37-company universe, then opens only the complete memos
needed to test causal matches.

| Published checkpoint | Developments | Input tokens | Cached tokens | Output tokens | Measured cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| July 5–28, up to ten per day, v15 | 186 | 4,809,068 | 1,218,283 | 298,619 | $27.521637 |

All 24 visible daily cohorts use `investment-agent-v15`: 64 Developments were
surfaced and 122 were suppressed.

The runner warms one request before bounded parallel fan-out. Every turn stores
its request, response ID, tool calls, retry history, usage, and reported cost.
Prompt caching is measured best-effort behavior; the uncached input price
remains the safe planning bound.

PDF generation, UI projection, and delivery preview are deterministic local
work over the published cohort and add no model cost.

## Current AI Engineering Agent

The surface-linked agent uses `gpt-5.6-sol` at high reasoning. Each Development
is judged in one call against the seven versioned Aion surfaces; it has no
company-memo tool loop or Investment materiality gate.

| Published checkpoint | Developments | Input tokens | Cached tokens | Output tokens | Measured cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| July 5–28, up to ten per day, v2 | 212 | 663,081 | 0 | 89,335 | $5.995455 |

All 24 visible daily cohorts use `engineering-agent-v2`: 27 Developments were
surfaced and 185 were suppressed. A day remains below ten when fewer eligible
positively routed Developments exist after canonical cross-day ownership.
Engineering web projection is local and adds no model cost; PDF and delivery
are intentionally Investment-only.

## What a Normal Refresh Pays For

The marginal cost depends on the boundary that changed:

- A ranking implementation change replays locally from saved evidence.
- A routing prompt or evidence-readiness change pays only for model-eligible
  Developments in the selected ranked cohort.
- An Investment prompt or company-packet change pays for every selected
  Investment-routed Development that is run again.
- An Engineering prompt or surface-map change pays for every selected
  Engineering-routed Development that is run again.
- A new complete day normally pays for new X timeline pages, new artifact
  bodies, routing for up to the top 100 Developments, and the selected
  Investment and Engineering cohorts.
- Extending the Registry or following graph is a separate operation and is not
  required for a normal daily brief.
- PDF rendering and the web read models remain local.

Use each audience dry-run before paid analysis:

```bash
.venv/bin/fli insights run-investment-agent \
  --through YYYY-MM-DD --days N --top-ranked 10 \
  --dry-run --json --no-input

.venv/bin/fli insights run-engineering-agent \
  --through YYYY-MM-DD --days N --top-ranked 10 \
  --dry-run --json --no-input
```

The dry-run resolves the exact target count, prompt, model, and reasoning level
without model calls, trace writes, database writes, or publication.

## Historical Cost Evidence

Earlier Event-rank, per-Event annotation, and App Server editorial experiments
remain useful build-history evidence but are no longer production stages. Their
measured LiteLLM increment was $18.974288, with $31.797248 of known stored
cohort cost including compatible historical outputs. Do not add those numbers
to a current Investment refresh estimate.

The immutable chronological record, including model experiments and reported
spend, lives in the build log. Query it with:

```bash
.venv/bin/python scripts/build-log.py recent
```

## X Provider Units

TwitterAPI.io responses do not consistently expose attributable billed spend,
so X costs are recorded as requests, returned items, or documented credits
unless a command can calculate a defensible estimate.

| Operation | Current evidence |
| --- | --- |
| Profile lookup | Approximately $0.00018 per profile at the documented $0.18 per 1,000 profiles used by the repository's estimators. |
| Timeline collection | Historical complete refreshes recorded 3,147 and 4,246 provider requests. The provider did not expose attributable run spend; returned-tweet pricing and cache reuse make request count alone an unsafe dollar conversion. |
| X Article body | 100 credits per Article, or approximately $0.001 with the repository's `credits / 100,000` estimate. The checkpoint store recorded 353 requests and 35,300 estimated credits, about $0.353 cumulatively. Cache hits make later replays free. |
| Outgoing-follow graph | The incremental World's Fair expansion was estimated at $4.37070. The earlier projected full 2,231-source crawl from cold state was $27.83826. Page caches make later extensions materially cheaper than a cold rebuild. |

Provider prices can change. Recheck the live provider contract before approving
a broad crawl; never infer exact billed spend from endpoint count when the
provider did not return it.

## Reading the Numbers

1. **Incremental cost** is what one exact run charged.
2. **Published-cohort cost** is the recorded cost of the rows currently visible
   to the reader.
3. **Replacement cost** is a planning estimate and must include an uncached
   input bound.

Cost is telemetry used to explain and improve the workflow. It is not a reason
to silently lower the model or reasoning quality of an in-scope run.
