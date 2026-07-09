# Frontier Lab Intelligence - Agent Guide

Frontier Lab Intelligence tracks frontier AI labs and key people, turns public
output into scored/cited signal, and delivers reports + alerts. Origin: BIT
Capital AI Engineer case study.

## Start Here

1. `docs/references/case-prompt.md` - external requirements.
2. Active `docs/projects/<project>/tasks.md` - execution state; use `$project`.
3. `docs/architecture/overview.md` - system map.
4. `PRODUCT.md` / `DESIGN.md` - product and UI contracts.
5. `docs/references/research-notes.md` / `docs/references/build-log.md` -
   provenance and history.

If docs conflict with chat, note it in the active tracker and follow the
preserved prompt until Adi decides.

## Hard Rules

- No external action without explicit current-session Adi approval: submitting,
  uploading, publishing, public pushes, or contacting BIT/Lars/Marc/Vlad. Before
  asking, prepare artifacts, message text, validation evidence, limitations, and
  prompt-requirement check.
- Keep Dobby/person-memory architecture out of this product repo.
- Put scratch in `tmp/`; put durable facts, decisions, provenance, and spend in
  repo docs.

## Work Contracts

- Data first: fetch raw evidence, inspect, then model; the DB schema is not
  locked yet.
- Product principles live in `PRODUCT.md`; do not trade away quality for the
  EUR100 budget unless actual spend approaches it.
- Build log: append one JSON object to `docs/references/build-log.jsonl` after
  meaningful chunks; `scripts/check-fast.sh` renders markdown.
- Update `docs/architecture/overview.md` when pipeline, schema, source classes,
  or module boundaries change.
- Run `scripts/check-fast.sh` before handoff, or record why validation was
  skipped in the active tracker.

## Skill Routing

- AGENTS/docs/harness review: `$agent-native-repo-playbook`.
- Tracker planning, refresh, or closeout: `$project`.
- UI review or frontend polish: `$impeccable`.
