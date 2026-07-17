# Registry Evaluation Operations

Exact operating contract for the reusable X evidence and Registry-evaluation
workflow. The architecture overview explains why the stages exist; this file
records where they live and how an agent can inspect or resume them safely.

## Boundaries

| Layer | Location | Role |
| --- | --- | --- |
| Canonical Registry | `data/fli.db` | Tracked entities, channels, structural kind, and reason-bearing Registry rejections. |
| Reusable X evidence | `data/raw/x/x-content.db` | Ignored immutable provider responses, normalized posts, and exact post bundles. |
| Evaluation runs | `data/derived/registry-evaluation/*.db` | Ignored cohort, hashes, model results, identity context, sources, usage, cache counters, and spend. |
| Prompt contracts | `src/fli/registry/prompts/identity_context_v1.txt`, `src/fli/registry/prompts/registry_evaluation_v3.txt` | Versioned stable prompt prefixes. Keep old prompt versions when historical runs reference their hashes. |
| Request contracts | `src/fli/registry/identity_contexts.py`, `src/fli/registry/evaluation.py` | Structured schemas, rendering, validation, LiteLLM tags, search, and cache keys. |
| Resumable orchestration | `src/fli/registry/evaluation_runs.py` | Cohort freezing, local evidence reuse, missing-bio research, evaluation, persistence, and status. |

The run databases never mutate the Registry. Promotion or rejection is a
separate curation action. Missing-bio identity context is research-derived and
is rendered separately from the observed profile bio; it never rewrites source
data.

## Normal Commands

Inspect a run without making provider or model calls:

```bash
fli registry-evaluation status \
  --run-db data/derived/registry-evaluation/<run>.db
```

Start or resume a full active-Registry evaluation:

```bash
fli registry-evaluation run --all \
  --registry-db data/fli.db \
  --x-content-db data/raw/x/x-content.db \
  --run-db data/derived/registry-evaluation/<run>.db \
  --run-id <stable-run-id> \
  --model gpt-5.4-mini \
  --reasoning-effort high
```

Reuse the exact evidence for a filtered comparison without another X request:

```bash
fli registry-evaluation run --all \
  --source-run-db data/derived/registry-evaluation/<source>.db \
  --source-kind person \
  --source-decision remove \
  --run-db data/derived/registry-evaluation/<comparison>.db \
  --run-id <stable-run-id> \
  --model gpt-5.4-mini \
  --reasoning-effort high
```

`--all` is an intentional acknowledgement for a bulk run. Completed evidence,
identity-context, and evaluation rows are skipped on resume. Application
retries are disabled; provider retries/fallback remain the LiteLLM boundary.
Every request carries stable app, pipeline, job, scope, prompt, and run tags.

## Current Local Evidence

All three run databases passed `PRAGMA integrity_check` on 2026-07-12:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `active-registry-gpt-5.4-mini-high-2026-07-12.db` | 29,196,288 | `1c62617bafe96fe2a2ac9edac65e90cc509bbc48bda101df749f201cbe401ec8` |
| `person-remove-luna-high-comparison-2026-07-12.db` | 2,867,200 | `ea41ec484cc4a72812cacaee0d9e7ddf43c797d85bd8eb267d4ecf1b955939fc` |
| `person-remove-identity-v3-gpt54mini-high-2026-07-12.db` | 5,603,328 | `8ba7c39d1c22a65d92312315ea17072f42180d72045e3bad58fca545504f410d` |

These databases and the 772 MiB X-content store are deliberately ignored by
Git. The tracked project resources preserve decisions, counts, cost, and
failure modes, but not every raw response. They currently exist only on this
machine. Creating an off-machine content-addressed backup requires explicit
current-session approval because it is an external upload.

## Invariants

- Route every model call through shared LiteLLM; never call Azure OpenAI
  directly from this repository.
- Keep model kind and Registry decision as independent output fields.
- Do not treat a missing bio, recent inactivity, or a 20-post sample as
  negative evidence about durable identity relevance.
- Required identity research must retain at least one observed web-search
  action. Final evaluation web search remains optional.
- Keep stable prompt content before entity-specific evidence and verify actual
  `cached_tokens`; cache eligibility is not proof of a cache hit.
- Reuse `x-content.db` before calling TwitterAPI.io. Use `--refresh-x-content`
  only when freshness is part of the explicit task.
- Never apply a bulk model removal set directly. The accepted final cleanup
  required model evidence plus a separately justified curation boundary.
- Preserve historical prompt files referenced by stored prompt hashes.

## Validation

Focused coverage lives in:

- `tests/test_identity_contexts.py`
- `tests/test_registry_evaluation.py`
- `tests/test_registry_evaluation_runs.py`

Run `scripts/check-fast.sh` before handoff. For a live bulk artifact, also run
`fli registry-evaluation status`, `PRAGMA integrity_check`, and reconcile the
expected cohort count with complete, failed, and pending rows.
