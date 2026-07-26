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
