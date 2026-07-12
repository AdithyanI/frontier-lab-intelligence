# M3 Personalized PageRank Comparison

Date: 2026-07-11  
Status: experimental run complete; not accepted as the product ranking.

## Experiment

The tracked `trusted-personalization-2026-07-11-v1` manifest assigns uniform
weight to 30 active Registry entities with complete snapshots. The set spans
frontier labs, academia, systems, open models, safety, evaluation,
interpretability, and policy. Each row records an exact X ID, one representative
channel per entity, category, weight, and short selection reason.

PageRank uses damping `0.85`, redirects dangling mass to the personalization
vector, initializes from that vector, and requires L1 residual at most `1e-10`.
It uses the same 2,456,305 eligible edges as entity-overlap. NumPy vectorizes
the 2,219-source core; SQLite performs the final all-target score projection.

Run id: `f00269b4d87471f65af0c74b7e8383cbfaadde99fba1819763b2c0424e44258a`  
Personalization SHA-256: `5b5918aa50e9483802da9d2aee5319b867eb0eccd773e02b71e79f13d739055b`

The run converged after 104 iterations with final L1 delta
`9.832307204490251e-11`; stored scores sum to exactly `1.0`. An identical replay
reused the deterministic run and passed full node/result reconciliation.

## Result

The top PageRank results are Karpathy, Yann LeCun, Jeff Dean, Demis Hassabis,
Google DeepMind, Fei-Fei Li, Chelsea Finn, Jack Clark, Soumith Chintala, and AI
at Meta. All 30 personalization seeds appear in the top 100.

Only 37.9% of the PageRank and overlap top-100 sets intersect. The overlap top
100 contains 95 active Registry accounts and five unknowns. PageRank contains
82 active accounts and 18 unknowns, but its new unknowns are often narrow
one-hop neighbors of individual seeds: the first include `@testingham`,
`@openainewsroom`, `@aievalforum`, and several low-consensus accounts. Many
large rank gains come from accounts followed by only one seed.

This is the predicted dangling-node failure mode. Only the frozen Registry
cohort has outgoing edges; almost all 463,180 discovered targets do not. The
personalization vector therefore dominates the stationary distribution, making
seed membership and direct seed adjacency more important than broad community
endorsement.

## Decision

Personalized PageRank is valid and reproducible, but it is not presently a
better general importance ranking than entity-overlap. Keep it as a diagnostic
and possible niche-personalization signal. Use entity-overlap as the default
known-account ordering and unknown-candidate generator for M4 human review.
Do not promote any unknown automatically.

Review artifacts:

- `pagerank-top-100-comparison.csv` — PageRank top 100 with overlap positions.
- `pagerank-top-100-unknown.csv` — PageRank's top 100 unknown accounts.
- `overlap-top-100.csv` and `overlap-top-100-unknown.csv` — baseline review.

## Reproducible command

```bash
.venv/bin/fli following-ranking pagerank \
  --snapshot-db data/raw/following/registry-following-2026-07-11-v1/snapshot.db \
  --registry-db data/fli.db \
  --analysis-db data/derived/following/registry-following-2026-07-11-v1/analysis.db \
  --personalization data/following/personalizations/trusted-personalization-2026-07-11-v1.json \
  --top-k 100 \
  --export-comparison-csv docs/projects/archive/trusted-following-ranking/resources/pagerank-top-100-comparison.csv \
  --export-unknown-csv docs/projects/archive/trusted-following-ranking/resources/pagerank-top-100-unknown.csv \
  --no-input
```

## Next step

Label a bounded overlap top-k across active and unknown accounts. Record
precision, obvious omissions, relevance failures, and organization/person mix.
That review—not the existence of a more complex algorithm—decides whether to
keep, change, or stop this ranking milestone.
