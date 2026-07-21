# Frontier Lab Intelligence agent guide

Frontier Lab Intelligence tracks frontier AI labs and key people, turns public
output into scored and cited signal, and delivers audience-specific reports.
It began as the BIT Capital AI Engineer case study.

## Start here

1. Read `docs/references/case-prompt.md` for the external requirements.
2. Read `docs/STATUS.md` for proven, active, missing, and deferred work.
3. Read `docs/architecture/code-map.md` for code, store, command, and test ownership.
4. Read only the relevant part of `docs/architecture/overview.md`.
5. Use `PRODUCT.md` and `DESIGN.md` when changing product or UI behavior.
6. Read an active tracker only when Adi explicitly invoked `$project`.

`README.md` is the public human landing page. If chat and docs conflict, follow
the preserved case prompt until Adi decides, then record the resolution in the
relevant durable document.

## Submission north star

Until the 20 July 2026 submission, optimize for a coherent, defensible, working
case study that earns the next interview. Prefer a narrow end-to-end proof and
3 to 5 excellent cited Insights over platform breadth.

## Guardrails

- Do not submit, publish, publicly push, upload, or contact BIT, Lars, Marc, or
  Vlad without Adi's explicit approval in the current session. Prepare the
  artifact, message, validation, limitations, and prompt check first.
- Keep Dobby and person-memory architecture out of this repository.
- Put scratch under `tmp/`. Put durable facts, decisions, provenance, and spend
  in the relevant repository document.
- Do not commit `data/raw/`, `data/derived/`, secrets, or private inputs. The
  public reviewer snapshot contract lives in `docs/references/demo-release.md`.
- Treat cost as telemetry, not a reason to lower in-scope quality, unless Adi
  sets an explicit cap.

## Implementation contracts

- Work data first: fetch raw evidence, inspect it, then model it. Preserve the
  schema and provenance invariants documented for the owning stage.
- Follow `docs/architecture/code-map.md` for ownership and
  `docs/references/data-lifecycle.md` before moving or deleting data.
- Route every LLM call through the shared LiteLLM endpoint. The exact model,
  metadata, cost, reasoning, and prompt-cache rules live in
  `docs/references/model-routing.md`.
- Use the build log only for the material decisions and milestones defined in
  `docs/references/build-log.md`. Routine work does not get an entry.
- Update `docs/architecture/overview.md` when a pipeline, schema, source class,
  or module boundary changes.
- Update `docs/STATUS.md` only when conceptual status, the critical path, or a
  proven/planned boundary changes.
- Run `scripts/check-fast.sh` before handoff, or report why it was skipped.

## UI preview

- The always-on app serves the built SPA at `http://127.0.0.1:8797`. Do not
  start a throwaway preview server on another port for screenshots.
- Build UI changes with `npm --prefix frontend run build`, then reload the
  always-on app.
- Prefer the in-app Browser for collaborative inspection. Use `$agent-browser`
  for repeatable automation or as a fallback. Keep captures under `tmp/` unless
  they are requested durable presentation assets.
- The product is desktop-first until Adi requests mobile work.

## Skill routing

- Repository harness, docs, or guardrail review: `$agent-native-repo-playbook`.
- Daily brief generation, review, or reruns: `$fli-daily-intelligence`.
- UI review or frontend polish: `$impeccable`.
- Project tracking is opt-in. Use `$project` only when Adi explicitly invokes it.
