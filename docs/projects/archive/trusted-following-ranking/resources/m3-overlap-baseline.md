# M3 Screened-Source Overlap Baseline

Date: 2026-07-11  
Status: implemented and run over the frozen snapshot.

## Question

Can a simple, explainable graph signal rank the current Registry more usefully
than raw X followers while also surfacing important accounts that the Registry
does not yet contain?

## Metric

For each discovered account, `cohort_follow_count` is the number of distinct
complete, active Registry **entities** that follow it. Several official X
channels owned by one organization contribute at most one vote to a target.
Raw follower count is
display evidence only and never changes the score. Protected, missing, and
rejected sources do not contribute. Rejected targets remain in the derived
store for audit but are excluded from candidate promotion.

This baseline answers “how broadly is this account attended to by our screened
AI cohort?” It does not by itself answer relevance, current activity, identity
kind, credibility, or whether an unknown account belongs in the Registry.

## Reproducible run

```bash
.venv/bin/fli following-ranking overlap \
  --snapshot-db data/raw/following/registry-following-2026-07-11-v1/snapshot.db \
  --registry-db data/fli.db \
  --analysis-db data/derived/following/registry-following-2026-07-11-v1/analysis.db \
  --top-k 100 \
  --export-csv docs/projects/archive/trusted-following-ranking/resources/overlap-top-100.csv \
  --export-unknown-csv docs/projects/archive/trusted-following-ranking/resources/overlap-top-100-unknown.csv \
  --no-input
```

Run id: `181d539ebc7ec1adee8c28adbec0c0a578f151eb116f9bba021094d915dab0f9`

Context id: `43b1e9e98e4c66a76928a5bea844c21cccac95fed22d9bd8298f462eaadb2eec`

| Reconciliation fact | Count |
| --- | ---: |
| Complete active source X accounts | 2,219 |
| Distinct voting Registry entities | 2,197 |
| Eligible directed edges | 2,456,305 |
| Deduplicated entity→target votes | 2,456,084 |
| Ranked discovered accounts | 463,180 |
| Active Registry matches | 2,240 |
| Rejected Registry matches | 13 |
| Unknown accounts | 460,927 |

The second identical invocation reused the same deterministic context and run;
it created no duplicate rows.

## First result

The top active accounts are Andrej Karpathy (1,795 entity follows), Jeff Dean
(1,591), Ilya Sutskever (1,440), Yann LeCun (1,434), OpenAI (1,406), Sam
Altman (1,397), Demis Hassabis (1,329), and Google DeepMind (1,316). The result
already differs materially from raw reach: Jeff Dean ranks second with roughly
448K followers, while Elon Musk ranks 63rd despite roughly 241M followers.

The first unknowns include `@_akhaliq` at global position 25, Paul Graham at 55,
Marc Andreessen at 64, Riley Goodside at 100, PyTorch at 135, MIT CSAIL at
163, ICML at 171, and ICLR at 173. This is useful candidate-generation
evidence, but the presence of broad public figures also proves overlap is not a
final relevance decision.

Review artifacts:

- `overlap-top-100.csv` — highest global overlap.
- `overlap-top-100-unknown.csv` — highest unknown accounts for bounded review.

## Storage and isolation

`data/derived/following/<snapshot-id>/analysis.db` is ignored, recomputable,
and separate from both the curated Registry and immutable raw snapshot. It
stores the snapshot and Registry checksums, stable active/rejected/unknown
mapping, deterministic run metadata, and complete ranking results. A SQLite
authorizer permits Registry reads only from identity and rejection tables and
explicitly denies legacy `graph_edges` access. The command snapshots the live
Registry transactionally before hashing it, rejects colliding input/output
paths, validates the complete frozen snapshot, includes zero-score targets,
and gives tied evidence one shared dense `score_rank` plus a deterministic
`position` for display.

## Next decision

The experimental personalization set and PageRank comparison are recorded in
`m3-pagerank-comparison.md`. Overlap remains the stronger default candidate
baseline pending human top-k review.
