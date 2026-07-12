# Trusted-Following Ranking — Learnings

## Summary

This project replaced an untrustworthy legacy graph with a provenance-complete
outgoing-follow snapshot, compared two ranking algorithms, and made the result
inspectable in the product. Its key output is not “PageRank solved relevance.”
It is a clean, reusable network-support feature plus evidence about where graph
ranking fails.

## What Helped

- Freezing raw following pages before modeling made every ranking reproducible.
- One ignored database per immutable snapshot kept 2.0 GB of evidence out of
  the small canonical Registry while preserving replay.
- Counting one vote per canonical entity prevented multi-channel organizations
  from dominating overlap.
- Starting with the simplest baseline exposed the personalized PageRank bias
  quickly: only 37.9% of its top 100 overlapped entity overlap, and seeds plus
  immediate neighbors dominated.
- Stable X IDs made cross-database Registry/ranking reconciliation possible.
- Read-only web adapters and current-schema endpoint fixtures caught the
  analysis-to-product contract regression.
- Preserving raw post and following responses enabled later comparisons without
  repeating provider calls.

## What Slowed Things Down

- Registry cleanup and graph ranking became interleaved, which repeatedly
  tempted the project toward broader curation rather than its ranking goal.
- “Trust,” “importance,” “reach,” structural kind, Registry admission, and
  collectability were initially discussed as if they were one label.
- Follower count was repeatedly mistaken for importance even though it mostly
  measured fame.
- Missing bios and narrow recent-post samples produced confident false removal
  recommendations until identity research was separated from source evidence.
- Model disagreement showed that a second expensive pass does not manufacture
  ground truth.
- The active tracker accumulated historical completed work in Current Batch;
  shrinking it to the live boundary made the next decision much clearer.

## Improvement Opportunities

### Tools and Data

- Keep stable author X IDs normalized in every future post relation; handles
  are display keys and can change.
- Materialize quote/retweet relationships from existing raw JSON only after a
  bounded slice proves the query is useful.
- Keep engagement observations and event scores derived/versioned rather than
  mutating canonical posts or entities.

### Validation

- Freeze scoring baselines before human labeling.
- Blind reviewers to ranking features and compare against chronological and
  raw-engagement baselines.
- Do not claim recall without labeling the complete evaluated day.

### Project Boundaries

- Close a project when its distinct engineering question is answered. The
  moment work changes from “who deserves attention?” to “what happened and why
  does it matter?”, open the signal-intelligence project rather than expanding
  the ranking tracker.

## Recommended Follow-Ups

- Treat `entity-overlap-v2` as network support/candidate evidence, not proven
  epistemic trust.
- Rank deduplicated events, not individual tweets.
- Begin downstream scoring with inspectable feature columns and lexicographic
  baselines; do not invent a weighted scalar.
- Recompute derived signal runs when Registry membership changes; never rewrite
  historical results in place.
- Defer graph expansion, extra engagement-actor APIs, and learned ranking until
  one complete day produces useful, grounded insights.

## Notes For Future Runs

- Raw engagement is a poor global ordering because famous accounts dominate.
- Retweets and quote tweets observed in tracked timelines provide identifiable
  trusted amplification; aggregate likes do not identify who engaged.
- A first-hand X announcement can itself be a primary source. External URLs are
  a verification path, not an eligibility gate.
