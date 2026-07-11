# M3 Screened-Source Overlap Baseline

Date: 2026-07-11  
Status: implemented and run over the frozen snapshot.

## Question

Can a simple, explainable graph signal rank the current Registry more usefully
than raw X followers while also surfacing important accounts that the Registry
does not yet contain?

## Metric

For each discovered account, `cohort_follow_count` is the number of distinct
complete, active Registry-cohort sources that follow it. Raw follower count is
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
  --export-csv docs/projects/trusted-following-ranking/resources/overlap-top-100.csv \
  --export-unknown-csv docs/projects/trusted-following-ranking/resources/overlap-top-100-unknown.csv \
  --no-input
```

Run id: `ea52882c21b773e411d5ff993276ad7de0a6dd7268588c52857df714f71c5126`  
Context id: `a590f79fe1159cdaa91f4cb2af37221874b402f6b09d0574a0ac89f817c67fda`

| Reconciliation fact | Count |
| --- | ---: |
| Complete active sources | 2,219 |
| Eligible directed edges | 2,456,305 |
| Ranked discovered accounts | 463,180 |
| Active Registry matches | 2,240 |
| Rejected Registry matches | 13 |
| Unknown accounts | 460,927 |

The second identical invocation reused the same deterministic context and run;
it created no duplicate rows.

## First result

The top active accounts are Andrej Karpathy (1,795 source follows), Jeff Dean
(1,593), Ilya Sutskever (1,440), Yann LeCun (1,434), OpenAI (1,406), Sam
Altman (1,397), Demis Hassabis (1,331), and Google DeepMind (1,321). The result
already differs materially from raw reach: Jeff Dean ranks second with roughly
448K followers, while Elon Musk ranks 63rd despite roughly 241M followers.

The first unknowns include `@_akhaliq` at global rank 25, Paul Graham at 55,
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
explicitly denies legacy `graph_edges` access.

## Next decision

Freeze a smaller, reviewable personalization set with short reasons, then run
personalized PageRank over the same snapshot. Compare it with this baseline on
the same known and unknown review sets rather than assuming PageRank is better.
