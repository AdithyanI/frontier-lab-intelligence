# Digg Ranking Baseline

Digg's frozen 2026-07-08 ranking is retained only to compare against the future
trusted-following ranking. Rank values are not imported into `data/fli.db` and
must not be blended into PageRank.

The active database contains only a neutral `digg_bootstrap.candidate_origin`
marker for the 2,308 accounts actually observed through Digg: 1,308 graph-only,
one ranking-only, and 999 present in both. This records origin without restoring
rank, score, edges, or PageRank.

## Artifact

- Path: `data/digg/rankings.csv`
- Rows: 1,000 ranked X accounts
- SHA-256: `2bea5f07e4449b9f313eb5e0c82ccb324dd12fb5ca60dc5e1ab77cf77bec1ce7`
- Source: `https://digg.com/tech/x/rankings`

The removed Digg follower edges, raw graph files, derived PageRank, and reload
commands are intentionally not part of this baseline.

## Later Comparison

After the trusted-following ranking passes its own evaluation, compare:

- top-k account overlap;
- rank correlation on shared accounts;
- important accounts unique to each ranking;
- disagreements that reveal either discovery value or noise.

Do not tune the trusted ranking to imitate Digg. The comparison is diagnostic,
not ground truth.
