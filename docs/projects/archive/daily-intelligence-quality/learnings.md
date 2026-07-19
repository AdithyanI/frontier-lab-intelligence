# Daily Intelligence Quality Learnings

## Summary

This project repaired chronology and citation grounding in the daily editorial
pipeline, proved a resumable Codex handoff, regenerated the evaluated corpus,
and curated five submission Insights. It is worth preserving because the main
failures were not schema failures: structurally valid briefs could still be
stale, over-selected, or weakly supported.

## What Helped

- The source store already had the chronology needed to prevent the largest
  editorial failure; the gap was propagation and validation, not ingestion.
- Structural completeness is necessary but does not establish senior-reader
  usefulness. Preserve mechanical checks and qualitative adjudication as
  separate layers.
- A daily run date is a publication/selection fact, not evidence that every
  supporting source was published that day.
- A source-level seven-day window is a better precision boundary than
  same-day-only Event suppression: it removes low-value old-root resurfacing
  while preserving substantive current same-author updates.
- Raw audit history and semantic authoring evidence are different products.
  Keeping the former does not require presenting all of it to the daily agent.
- Event membership establishes that an artifact was discovered near an Event,
  not that it supports every claim derived from that Event. Exact disclosure
  lineage and excerpt grounding solve different parts of that failure.
- Audit metrics need precise units. The current baseline has 196 citation
  records, 193 distinct URLs, and 114 Event-citation uses; calling all three
  “unique citations” obscures the result.
- Immutable workspaces and atomic imported runs made parallel editorial work
  inspectable even when host-level task concurrency was noisy.
- The company context packet and Engineering context narrowed the audience
  question before web research, while still leaving daily direction to the
  evidence.
- Verified artifact excerpts caught semantic citation failures without adding
  another automated relevance model.
- A compact pair-coverage ledger and focused run projections removed repeated
  bookkeeping from later agents without automating their editorial decisions.

## What Slowed Things Down

- Brief date, source publication, discovery, disclosure, and retrieval were
  initially conflated, causing repeated clarification and reruns.
- Full run payloads made simple coverage and import checks unnecessarily hard
  for agents to inspect.
- Unbounded multi-task execution produced `Bad file descriptor` failures even
  though imported state remained isolated.
- The first cross-day audit remained temporarily stale after 16 July was
  regenerated, showing that evaluation records need a final closeout pass.
- The corpus had no prior-story fingerprint, so repeated model-routing,
  permission, and open-model conclusions had to be caught editorially.

## Durable Decisions

- Daily X evidence uses a seven-day inclusive first-party source window; raw
  Feed/Event evidence remains unchanged.
- Artifact timing is visible but not an automatic exclusion gate. Every cited
  artifact must instead contribute a verified frozen-text excerpt that supports
  the Insight claim.
- Direction labels express a potential development-specific company
  read-through. `uncertain` is not a safe harbor for a weak mapping.
- Preflight and compact projections are inspection aids only. Grouping,
  selection, ranking, causal direction, and company impact remain agent
  judgments.
- The complete corpus is an audit surface. The final submission proof is the
  curated five-Insight set, not the entire reader.

## Recommended Follow-ups

After submission, consider compact cross-day development fingerprints,
historical web-availability metadata, exact source-text windows, and bounded
task concurrency. Take them only when a new evaluation shows that they improve
novelty, source review, or operating reliability.

## Closeout Answers

- Application-owned chronology and honest reader-facing prose removed the need
  for a new Insight-type field before submission.
- The highest-leverage editorial improvement was verified source chronology
  plus claim-specific artifact excerpts. The highest-leverage agent-experience
  improvement was the compact coverage preflight.
- Company context, Engineering context, direction calibration, and compact
  inspection were useful. Automated semantic merging, a new development
  entity, a second artifact-relevance model, a generalized workflow engine,
  and broad corpus pruning would have added process without improving the
  locked submission proof.
