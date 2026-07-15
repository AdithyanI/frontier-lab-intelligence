# Evidence Audience Routing — Project Learnings

## Summary

- This project defines one small routing boundary between ranked Evidence
  envelopes and any future audience-specific Insight generation.
- Capture learnings continuously because the preceding project accumulated
  costly complexity before the first product judgment was jointly understood.

## What Helped

- Exact envelope deep-links and copyable envelope IDs let Adi and an engineer
  discuss one concrete record instead of abstract pipeline stages.
- Clean primary-author artifact lineage gives the router a defensible evidence
  boundary.
- Starting with one visible envelope exposed data-linking and rank issues before
  bulk model work.
- A stratified contextual audit found policy-boundary errors that aggregate
  label counts and schema validation could not reveal.
- Rerunning only five disputed/borderline packets made prompt calibration fast,
  cheap, and interpretable while preserving the 90-record v4 run as immutable
  evidence.

## What Slowed Things Down

- Routing, extraction, editorial selection, verification, and publication were
  previously designed together, making the product hard to explain and debug.
- Multiple frozen ranks and generated tables appeared to compete with current
  Feed data.
- Implementing later-stage audit machinery before agreeing on the basic
  keep/audience decision created rework and cognitive load.

## Improvement Opportunities

### MCPs / Tools

- Add or preserve a deterministic one-envelope packet renderer so model inputs
  can be reviewed without running a model.

### Skills

- Use `$project` at every scope reset so archived experiments and active work
  cannot be confused.

### AGENTS / Docs

- Keep the one-source-of-truth rule explicit whenever derived UI values are
  introduced.

### Validation / Feedback Loops

- Require one-envelope human review and one-day audit before any bulk run.
- When a qualitative audit proposes a threshold rule, encode it as a general
  decision boundary and rerun the exact disputed cases plus nearby negatives.
  Do not treat one rewritten prompt as accepted until the reasons—not only the
  booleans—follow the intended policy.

### Delegation / Subagents

- Keep shared schema and prompt decisions in the parent task; delegate only
  read-only packet audits or isolated implementation after contracts freeze.

## Recommended Follow-Ups

- Treat `kept` as a UI/read-model derivation of the two audience booleans; do
  not add another model field or database authority for it.
- Build the packet renderer before the first routing model call.
- Start Insight generation as a separate project consuming positive routes;
  do not extend this routing schema with summary, confidence, rank, or
  publication fields.

## Notes For Future Runs

- Do not interpret archived prompts, schemas, or tests as the active product
  contract.
- A routing decision is not an Insight and should never contain generated
  claims or editorial ranking.
- Prompt wording such as “may qualify” can leave an intended boundary
  underdetermined. Put approved inclusion rules near the task definition, say
  what evidence is sufficient, and name the stronger proof requirement the
  model must not invent.
