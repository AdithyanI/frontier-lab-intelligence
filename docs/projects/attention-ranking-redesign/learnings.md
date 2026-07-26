# Attention ranking redesign learnings

## 2026-07-26

- Check component scales before presenting a formula. A fixed `+0.25`
  adjustment cannot carry meaningful product semantics beside an open-ended
  sum that can exceed 100.
- Separate the ranking objective from the formula. “What the network paid
  attention to” is not the same as relevance, usefulness, source authority, or
  public popularity.
- Preserve explanatory figures when adding formula detail. The rank-order
  figure explains the output of ranking; a formula figure explains its inputs.
  One should not silently replace the other.
- Audit the score you already shipped before designing its replacement. The
  rejected candidate's flaw was visible on paper; production's larger flaw was
  only visible in the data. A percentile transform is correct for a continuous
  heavy-tailed input and wrong for a zero-inflated count — applying one
  transform uniformly across lanes is how a 55% weight quietly becomes a
  binary flag and a 25% weight quietly takes over the ordering.
- Nominal weights are a claim, not a measurement. Check per-lane contribution
  spread *inside the window the score actually decides*, not across the whole
  day. A lane that saturates near its ceiling has stopped discriminating no
  matter how large its coefficient looks.
- A found-and-measured flaw in your own system is an interview asset, not a
  liability, when the fix would invalidate frozen submitted evidence. The
  defensible move is to arrive with the diagnostic and the reasoned decision
  not to rerank, rather than to silently swap the formula.
