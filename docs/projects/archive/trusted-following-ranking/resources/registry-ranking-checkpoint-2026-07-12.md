# Registry and Ranking Checkpoint

Date: 2026-07-12

## Executive Summary

Frontier Lab Intelligence now has a cleaned, typed, reason-bearing Registry and
a fresh X following graph that can rank both known identities and people
outside the Registry. The system is technically working and inspectable. What
has not yet been proven is the product thesis: whether the highly ranked
accounts actually produce timely, novel, useful intelligence.

That is now the only important question. Broad identity cleanup is closed. The
next step is a small end-to-end information-yield experiment, not more Registry
polishing.

## What Was Built

### 1. A stable identity spine

- One real-world entity can own multiple independently observed channels.
- Structural kind is limited to `person`, `organization`, or `unsure`.
- Registry admission is separate from structural kind.
- Rejected is a reason-bearing Registry state, not an entity kind.
- Rejections are reversible and do not delete the underlying identity,
  channel, cached posts, or ranking evidence.
- Internal lab provenance remains internal; it is not exposed as a competing
  public kind.

The live Registry currently contains:

| State | Count |
| --- | ---: |
| Active people | 2,104 |
| Active organizations | 93 |
| Rejected identities | 23 |
| Unsure | 0 |
| Unknown | 0 |
| Total identities | 2,220 |

There are 2,293 channels and 2,256 stored X accounts. Organizations may own
more than one X channel, so X-account and entity counts are intentionally not
identical.

### 2. A cleaned and auditable Registry

The initial universe was structurally classified through LiteLLM. Subsequent
curation separated three questions that had originally become tangled:

1. Is this a person or an organization?
2. Is this identity useful enough for the active Registry?
3. Is its public channel currently collectable?

Organization aliases and product accounts were consolidated through reviewed
manifests. Major missing organizations such as Microsoft, Amazon, Apple,
NVIDIA, AMD, and Intel were added as stable parents with official channels.
Protected and off-mandate accounts use explicit rejection reasons.

The final person-cleanup pass corrected an important failure mode. Missing bios
and narrow 20-post samples were causing durable AI contributors to look
irrelevant. A required-search identity-context stage now grounds current role,
organization, durable contributions, and source URLs without overwriting the
observed X bio. The final mutation rejected only 10 identities where both the
v3 evaluator and bottom-decile trusted-follow support agreed. Eleven stronger
network cases stayed active, and two provider failures were left untouched.

### 3. A fresh following evidence layer

The original 361,863-edge Digg graph was rejected as a ranking foundation
because its meaning and provenance were not defensible. It was removed from
the active system rather than quietly reused.

A new immutable snapshot was collected from the outgoing follows of the
cleaned Registry cohort:

| Measure | Value |
| --- | ---: |
| Complete active source accounts | 2,219 |
| Directed following edges | 2,456,305 |
| Distinct ranked X accounts | 463,180 |
| Currently active Registry X accounts in the graph | 2,230 |
| Currently rejected Registry X accounts in the graph | 23 |
| Discovered accounts outside the Registry | 460,927 |

The snapshot is local-first, resumable, checksum-bound, and backed up as a
verified compressed object. Raw pages are retained for recovery and replay;
normalized edges are used for analysis.

### 4. Two ranking experiments

The accepted baseline is `entity-overlap-v2`: rank an account by how many
distinct active Registry entities follow it. This is simple to explain and
does not confuse raw audience size with trust.

Personalized PageRank was also implemented over the same snapshot. It
converged correctly, but only 37.9% of its top 100 overlapped with entity
overlap. The reviewed personalization seeds and their immediate neighbors
dominated the result, exposing a dangling-node/seed-proximity bias. PageRank is
therefore retained as a diagnostic, while entity overlap drives the current
Ranking page and candidate discovery.

### 5. Reusable content and model evidence

Recent X evidence is no longer a transient API response:

| Stored evidence | Count |
| --- | ---: |
| Immutable TwitterAPI.io responses | 4,419 |
| Normalized authored posts | 63,736 |
| Exact model-input post bundles | 2,207 |

Each bulk model run has a separate resumable SQLite artifact containing exact
inputs, hashes, Response IDs, output, model, usage, cache counters, web actions,
sources, and proxy-reported cost. All LLM traffic goes through the shared
LiteLLM route; no direct Azure OpenAI calls are used.

## Important Experiments and Results

### Prompt caching

Prompt caching worked on GPT-5.4-mini but not consistently on Luna through the
same Azure/LiteLLM route. The complete mini evaluation observed 13.60 million
cached tokens out of 19.88 million input tokens. Luna comparisons repeatedly
reported zero cache reads. The system therefore records cache counters rather
than assuming an eligible prompt received a cache hit.

### Registry evaluation stability

- GPT-5.4-mini evaluated 2,207 active X identities: 1,855 keep, 201 remove,
  and 151 review.
- Luna re-evaluated the 192 mini person removals using the exact same evidence:
  119 keep, 60 remove, and 13 review.
- This disagreement proved that model output alone was not safe as a deletion
  boundary.
- Adding grounded identity context to the 192-person cohort produced 157 keep,
  21 remove, 12 review, and two held-out provider failures.
- Only 10 low-network-support removals became reversible Registry rejections.

### Recorded spend

Cost is telemetry, not a quality gate. The major recent model runs were:

| Run | Proxy-reported stored-result cost |
| --- | ---: |
| Full GPT-5.4-mini Registry evaluation | $13.4861493 |
| Luna comparison of 192 person removals | $3.3719360 |
| Missing-bio identity research | $6.1166097 |
| Final v3 evaluation | $1.2583785 |

The immutable following crawl has a best-available provider-cost estimate of
`$27.81218`. Earlier calibrations and small calls remain itemized in the build
log; this table is not claimed as the project's complete lifetime spend.

## What We Learned

1. **Follower count is reach, not trust.** It is useful for display and gross
   eligibility checks, but not as the ranking score.
2. **A graph is evidence, not truth.** Even trusted-source overlap can surface
   famous or adjacent people; candidates still need an admission or utility
   test.
3. **Recent posts are not a biography.** Quiet or narrowly focused feeds can
   hide durable contributions and current roles.
4. **Missing data must not become negative evidence.** Blank bios caused
   confident false removals until grounded identity research was added.
5. **One model pass is not a safe deletion mechanism.** Model disagreement was
   substantial even with identical evidence.
6. **Personalized PageRank was not automatically better.** Its first measured
   result amplified the chosen seeds and their immediate neighborhoods.
7. **Preserving raw evidence paid off.** Exact post bundles and following pages
   allowed comparisons, retries, and prompt revisions without repeating
   provider calls.
8. **Registry completeness is not the product outcome.** A beautifully curated
   watchlist is useless unless it produces important, cited intelligence.

## What Is Proven—and What Is Not

Proven:

- the identity/channel model works;
- ingestion is resumable and provenance-complete;
- the fresh graph is isolated from the rejected legacy graph;
- entity overlap produces an explainable ranking;
- discovered accounts can be traced back to the Registry sources following
  them;
- the complete workflow is inspectable in the Registry and Ranking UI.

Not yet proven:

- that ranked sources produce better intelligence than the original curated
  sources;
- that discovered accounts add novel signal rather than more noise;
- that the system can turn current evidence into 3–5 strong cited insights;
- that the final delivery is useful to the case-study audience.

## Exact Next Experiment

Run one bounded, utility-first vertical slice:

1. Freeze 20 highly ranked active people and 20 highly ranked discovered
   people as an evaluation cohort.
2. Collect or reuse their recent public posts without admitting or rejecting
   the discovered accounts first.
3. Deduplicate and cluster the evidence into events.
4. Extract cited intelligence candidates from the surviving events.
5. Judge usefulness, novelty, and actionability, while retaining which cohort
   produced each candidate.

Success means producing at least 3–5 genuinely useful, non-obvious, cited AI
insights and learning whether discovered sources contribute meaningfully. If
the batch is mostly noise, stop expanding the social graph and pivot the proof
toward higher-signal sources such as official lab blogs, releases, GitHub, and
papers.

This experiment validates the product thesis and starts the actual information
pipeline at the same time. No further broad Registry filtering should happen
before it.

## Durable References

- System map: `docs/architecture/overview.md`
- Archived tracker: `docs/projects/archive/trusted-following-ranking/tasks.md`
- Following storage contract: `docs/references/following-snapshot-storage.md`
- Accepted overlap baseline: `resources/m3-overlap-baseline.md`
- PageRank comparison: `resources/m3-pagerank-comparison.md`
- Full evaluator run: `resources/registry-evaluation-full-run.md`
- Luna comparison: `resources/registry-evaluation-luna-person-remove-comparison.md`
- Final cleanup: `resources/registry-evaluation-v3-final-cleanup.md`
- Chronological record: `docs/references/build-log.md`
