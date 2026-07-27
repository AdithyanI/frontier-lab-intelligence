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
  liability. Before migration approval, the defensible move was to preserve
  submitted evidence and explain the diagnostic. Once Adi explicitly approved
  a full replay, the defensible move became a clean versioned migration with
  every downstream lineage refreshed—not a silent in-place reinterpretation.
- Compute rank only after exact Event grouping. Adding post-level voter counts
  loses trusted reactions attached to other Event members and can count the
  source entity before the complete union is known.
- Lexicographic rules make priorities testable, but they do not eliminate the
  need for behavioral measurement. Trusted-voter count defines the bands;
  mean voter network position separated 79.4% of adjacent top-100 pairs in the
  17-day replay, so it is a load-bearing second layer and should be described
  honestly.
- Downstream relevance labels are useful diagnostics, not ground truth. The
  current top-100 labels show a monotonic 34.3% → 72.1% gradient by trusted
  vote bucket, but they remain censored by the rank gate and the router's
  freshness policy.
- Version the rank at every consumer boundary. Routing, per-Event Insight
  reuse, daily orchestration, APIs, PDFs, and persisted web projections can
  otherwise look current while retaining an older ordering.
- Exact Event/evidence/input reuse is the cost-control mechanism that matters:
  the routing migration reused 976 of 1,674 judgments and the Insight migration
  reused 524 of 1,482 outputs without weakening current rank provenance.
- A network percentile must account for tied population mass, not just dense
  support levels. Counting entities with strictly lower support makes equal
  support equal, preserves the intended 0–1 meaning, and avoids arbitrary gaps
  created by differently sized tie groups.
- Hash the full day of Event rank inputs, not only the selected Event or rank
  version. A route can have identical semantic evidence while its admission or
  feed rank changed because another Event changed; the full-day SHA makes that
  hidden dependency explicit.
- “Latest complete for this date” is not a sufficient read contract. Editorial
  and PDF/UI readers must prove exact current routing, cohort, Event, Feed, and
  rank lineage or fail closed to the current per-Event view.
- Weekly inherited daily rank is a different contract from one day's
  lexicographic rank. Reusing a final-day rank SHA on a seven-day projection
  made the response look more exact than it was; the weekly view now declares
  its inherited ordering without a false input hash.
- Reuse lookup can become the slow part even when external spend is tiny. The
  final Insight correction made only 23 model calls, but serial request
  freezing and repeated SQLite predecessor scans dominated wall time. A future
  harness pass should batch or index those reads without weakening exact reuse.
- The final tie-aware correction reused 1,647 of 1,674 routing judgments and
  1,451 of 1,474 per-Event Insight outputs. Strict lineage therefore made a
  mathematical correction cheap while still regenerating every genuinely new
  boundary item.
