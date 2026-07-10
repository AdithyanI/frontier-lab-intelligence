# Entity Spine Bootstrap Learnings

## Summary

This phase assembled several public X evidence sources, imported Adi's outgoing
following snapshot, and turned every observed channel into a visible provisional
entity cluster. It is worth preserving because the real data exposed taxonomy
problems that were invisible in the initial schema sketch.

## What Helped

- Fetching and inspecting real evidence before locking the schema exposed the
  difference between an X account, a real-world entity, and a tracked subject.
- The Registry UI made obvious that many accounts previously presented as
  people were actually organizations, products, publications, or communities.
- Source facts and channel observations preserved Digg rank, PageRank, list
  membership, follower counts, and bios without turning those observations
  into canonical identity labels.
- The repo tracker, architecture overview, registry-curation reference, and
  JSONL build log provided enough durable context to recover from long threads.

## What Slowed Things Down

- The first schema used `lab` as a structural entity kind. A lab is better
  treated as an organizational role, while the first structural question is
  person versus organization.
- Earlier UI copy treated unclassified accounts as people, which gave the
  impression that a classification pass had already occurred.
- Identity resolution, kind classification, and track/reject curation were
  discussed together at first. Separating them made the next task much simpler.
- The one-time Adi-following cleanup was intentionally not encoded as importer
  policy. That respected the request but means rerunning the import or channel
  sync can restore rows that were manually removed.
- Hand-curated lab seeds labeled every endpoint `official`; an arXiv affiliation
  query is a monitoring query, not an owned official channel.

## Improvement Opportunities

### MCPs / Tools

- The official `openai-docs` skill and OpenAI Developer Docs MCP are now routed
  to this repo for Responses API and Structured Outputs work.
- Playwright exposed 24 tools and roughly 3,300–4,000 static input tokens. Adi
  disabled it during the data/classification phase; re-enable it through the
  agents control plane only when visual UI verification is active again.

### Skills

- Use `$project` at every long-running phase boundary so the active tracker does
  not accumulate unrelated historical work.
- Use `$openai-docs` before implementing OpenAI SDK or structured-output code.
- LiteLLM is runtime infrastructure, not a skill. Its local endpoint and key
  already live in the shared machine-secret lane.

### AGENTS / Docs

- Keep `docs/references/registry-curation.md` as the narrow contract for kind,
  identity, and curation decisions.
- Label implemented schema separately from proposed target schema everywhere.
- Record one-time data mutations and their replay limitations next to the
  import command that could undo them.

### Validation / Feedback Loops

- Validate row counts, ownership invariants, and SQLite integrity directly
  before every classification or migration batch.
- Start LLM work with a varied bounded sample, inspect systematic errors, then
  run the complete corpus with the same versioned prompt.

### Delegation / Subagents

- No subagents were needed for this tightly coupled bootstrap and taxonomy
  discussion.

## Recommended Follow-Ups

- Implement the minimal `person | organization | unsure` classifier.
- Keep the model response to `classification` and `reason`; attach identifiers
  and run metadata in deterministic application code.
- Build channel merging only after independent kind classification is working.
- Build track/reject curation only after entities have stable identities.

## Notes For Future Runs

- Current snapshot: 2,967 graph accounts, 2,966 visible entities, 2,998
  channels/links, 12,664 source facts, 361,863 edges, and 21,133 observations.
- `@adithyan_ai` is intentionally retained only as the source node for 638
  outgoing-follow edges.
- Do not rerun the following import or channel sync casually; read the active
  tracker's one-time-cleanup warning first.
