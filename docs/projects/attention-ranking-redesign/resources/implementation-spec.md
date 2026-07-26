# Implementation spec — layered daily score (`daily-score-v2`)

Owner: assigned engineer. Written 2026-07-26 for an overnight implementation
pass. Read `layered-score-proposal.md` first for the reasoning, and
`v1-1-behaviour-audit.md` for the measured defect this replaces.

This spec is a **clean migration**. Adi has snapshotted the databases and has
explicitly ruled out backward compatibility: do not add dual-read paths,
version fallbacks, compatibility shims, or "legacy formula" toggles. Remove
`attention-v1.1` and the `attention-v2-candidate` grid experiment entirely.
Rollback, if ever needed, is a snapshot restore, not a code path.

---

## 1. What is being built

A ranking that answers exactly one question: *which Events did the trusted
network independently vouch for on this day?*

It is a **lexicographic (layered) ordering**, not a weighted sum. Sort by
layer 1; only when layer 1 ties does layer 2 decide; and so on.

```text
1. trusted_vote_count      int    distinct trusted Registry entities that vouched
2. mean_voter_position     float  average network position of those voters, 0–1
3. author_position         float  network position of the author, 0–1
4. public_interactions     int    likes + replies + reposts + quotes
5. event_id                str    stable final tiebreak, determinism only
```

Descending on 1–4, ascending on 5.

There are **no tunable constants anywhere in this design**. If the
implementation introduces a weight, a cap, a knee, or a magic multiplier,
something has gone wrong — stop and re-read the proposal.

### Explicitly rejected variants (do not reintroduce)

- Any weighted blend of the four layers.
- The `1 + 0.5 × trust` participant weight. Averaging is affine, so
  `mean(1 + 0.5p) = 1 + 0.5·mean(p)`, which cannot change an ordering. The
  constants would be unjustifiable and inert. Layer 2 uses raw position.
- Summing voter trust instead of averaging. Summing re-encodes vote count into
  layer 2 and collapses it back into layer 1.
- A seed vote for organizations, first-party posts, or artifact-bearing posts.
  Rejected on measured evidence; see the proposal's org table.
- Percentile transforms on the vote count. That is the exact defect being
  removed.

---

## 2. Definitions and invariants

These are product invariants. Enforce them in code and assert them in tests.

1. **One entity, one vote.** A canonical Registry entity contributes at most
   one vote to an Event regardless of how many posts it contributed. The
   existing `amplifiers` dict in `src/fli/web/feed.py` is already keyed by
   `entity_id`, so this holds today — keep it.
2. **Only `active` Registry entities vote.** `rejected` entities are excluded
   at read time, as today. Registry curation must keep changing derived views
   without touching raw evidence.
3. **No self-voting.** An author cannot amplify their own post into a vote.
   `feed.py` already filters `entity_id != author entity_id`; keep it.
4. **Author is not a voter.** The current production behaviour excludes the
   author from `amp_values`. Keep that. The author's standing enters at layer
   3 only. (Note: `candidate-comparison.md` invariant 3 proposed counting the
   author as a participant. That is superseded — do not implement it. Layer 3
   already carries author standing, and counting the author would give every
   first-party post a free vote, which is the seed-vote idea rejected above.)
5. **Day-scoped.** All layers are computed within one frozen UTC day. Scores
   and positions from different days are never compared.
6. **Editorial-blind.** Audience routing judgments and editorial outcomes
   never enter any layer.
7. **Deterministic.** Equal inputs must produce an identical order across
   runs and processes. `event_id` is the terminal tiebreak.

### Network position (used by layers 2 and 3)

`position = 1 − (rank − 1) / (total − 1)`, where `rank` is the 1-based
`support_rank` from the accepted entity-overlap ranking run and `total` is the
count of ranked entities in that run. Top-ranked entity → `1.0`, lowest → `0.0`.
If `total == 1`, position is `1.0`. An entity absent from the ranking run has
position `0.0`.

Use **rank**, not raw `support_count`. `support_count` is severely
right-skewed (top entity 2,041; median in the low tens), so using it would let
a handful of accounts dominate layer 2 — reintroducing the celebrity problem
the layering exists to avoid. `trust_percentile()` in
`src/fli/scoring/trusted_attention.py` already implements this correctly;
reuse it.

---

## 3. Where the data already is

| Input | Source today | Notes |
| --- | --- | --- |
| Voters per Event | `amplifiers` list on each Event root, built in `src/fli/web/feed.py` (~line 360–410) | Already deduplicated by `entity_id`, already excludes the author and rejected entities. Each carries `entity_id`, `entity_name`, `entity_kind`, `network_support`. |
| Author network support | `support` map in `feed.py` from `_network_support()` | Keyed by author `x_id`. |
| Author rank position | `positions` map from `_network_support()` (`_originator_rank`) | 1-based `position` column of `ranking_result`. |
| Public interactions | `_public_engagement(row)` in `feed.py` | Sum of likes, replies, reposts, quotes. |
| Entity rank table | `data/derived/following/*/analysis.db`, tables `ranking_result` and `entity_support_result` | Loaded and cached by `_network_support_cached()`. |

**Gap to close:** amplifier rows carry `network_support` (a raw count) but not
a rank position. Layer 2 needs positions for voters. Extend
`_network_support_cached()` to also return an `entity_id → position` map, or
resolve each amplifier's `x_id` through the existing `positions` map when the
amplifier candidate is built. Prefer the latter — it avoids a second lookup
table and keeps one source of truth.

---

## 4. Code changes

### 4.1 `src/fli/scoring/attention.py` — replace, do not extend

Delete `AttentionFormula`, `ATTENTION_V1_1`, `ATTENTION_V2_CANDIDATE`,
`percentiles`, `saturating_log`, and `score_components`.

Replace with a small pure module:

```python
DAILY_SCORE_VERSION = "daily-score-v2"

@dataclass(frozen=True)
class Voter:
    entity_id: int
    position: float          # 0–1 network position

@dataclass(frozen=True)
class ScoreInputs:
    voters: tuple[Voter, ...]        # deduplicated, author excluded
    author_position: float           # 0–1, 0.0 if unranked
    public_interactions: int
    event_id: str

def sort_key(inputs: ScoreInputs) -> tuple:
    """Lexicographic ordering key. Descending on layers 1-4."""
    votes = len(inputs.voters)
    mean_position = (
        sum(v.position for v in inputs.voters) / votes if votes else 0.0
    )
    return (
        -votes,
        -mean_position,
        -inputs.author_position,
        -inputs.public_interactions,
        inputs.event_id,
    )
```

Validation to enforce in `__post_init__`: positions finite and within `0–1`,
`public_interactions >= 0`, voter `entity_id`s unique.

`mean_position` must be `0.0` when there are no voters. Guard the division.

### 4.2 `src/fli/scoring/trusted_attention.py` — fold in and delete

This module was the offline candidate sandbox. Its `trust_percentile()` is
correct and moves to `attention.py`. Delete `TRUST_UPLIFT`,
`bounded_weight`, `FLAT_CONVERGENCE`, `WEIGHTED_CONVERGENCE`,
`DAILY_BUDGET`, `score_event`, `rank_events`, `candidate_contract`, and
`participant_touch_counts`. Then delete the file.

### 4.3 `src/fli/web/feed.py` — emit the new components

`apply_attention_scores(items)` is called once per complete visible day. It
becomes an ordering pass rather than a scoring pass:

- Build `ScoreInputs` per item from the existing `amplifiers` list, resolving
  each amplifier to a network position.
- Attach a stable `daily_rank` derived from the sorted order.
- Replace the `score_components` payload (see §5).
- Keep the existing behaviour that the **complete visible day** is ranked
  before lane filtering and search, so filtering never changes an item's rank.
- Keep the existing "Event uses its highest-scoring member" selection, but
  "highest" now means "first under `sort_key`".

Remove `_network_raw` and the percentile plumbing.

### 4.4 `src/fli/web/events.py`

`peak_attention_score` and `daily_score_basis` must move to the new
contract. `peak_attention_score` becomes meaningless as a float — replace it
with the winning member's rank/components rather than a synthetic number.
Check every reader before renaming; `_daily_score_basis()` is the seam.

### 4.5 `src/fli/scoring/evaluation.py` — rewrite as the replay harness

Currently it grid-searches weights. There are no weights now, so the grid
goes. It becomes the **validation harness** described in §7:

- Load the same complete `audience-routing-v9` days it loads today.
- Re-rank each day under `sort_key`.
- Report, per day and pooled: hit rate by vote bucket, rank correlation
  against the frozen v1.1 order, top-20/50/100 overlap, Events moving ≥25
  places, gate churn (which Events enter and leave the top 100), and how many
  admissions were decided by each layer.
- Keep the `--json` and `--no-input` CLI contract.

`load_labeled_days()` reads `score_components` from stored routing runs. Those
stored rows carry the **old** component names. Since routing runs are
immutable historical artifacts, the harness must read the raw inputs it needs
(`registry_amplifiers`, `originator_network_support`, `public_interactions`)
from the Event projection rather than from the frozen payload where the names
have changed. Verify this before assuming the replay works.

### 4.6 `src/fli/cli.py`

`attention-score evaluate` keeps its name and JSON contract. Remove any
subcommand, flag, or output field referring to formula versions, weights,
`amplifier_cap`, or `support_knee`.

---

## 5. API contract change

`FeedScoreComponents` in `frontend/src/shared/api/evidence.ts` and its Python
producer both change. New shape:

```jsonc
{
  "trusted_votes": 5,
  "voters": [                        // ordered by position desc
    { "entity_id": 42, "entity_name": "roon", "position": 0.995 }
  ],
  "mean_voter_position": 0.936,
  "author_position": 0.957,
  "public_interactions": 14602,
  "decided_at_layer": 1              // 1-4: which layer settled this Event's place
}
```

Remove `network_attention_percentile`, `originator_support_percentile`,
`public_engagement_percentile`, `network_attention_factor`,
`originator_support_factor`, `public_engagement_factor`, and
`originator_network_support`. Do not keep aliases.

`decided_at_layer` is what makes the UI honest and is worth the small cost:
it names which question actually settled this Event's position against its
neighbour. Compute it during the sort by comparing each item to the one ranked
immediately above it — the first layer where they differ.

---

## 6. UI changes

### 6.1 Feed score disclosure — `frontend/src/features/evidence/FeedPage.tsx`

The disclosure at ~line 310–430 currently renders three lanes with
`weight`, "Higher than X% of that day's scored posts", and "N points". All of
that is gone. Render the four layers instead:

```text
1  Trusted vouches          5 entities              ← decided this rank
2  Who vouched              average position 0.94
3  Author standing          position 0.96
4  Public engagement        14,602 interactions
```

Mark the layer named by `decided_at_layer`. Show the voter names — they are
the evidence, and they are already in the payload. Remove `networkWeight`,
`originatorWeight`, `engagementWeight` and the `formula` prop entirely.

Keep the existing limitation footer, updated: the score prioritizes what to
inspect; it is not importance, truth, or quality; days are not comparable.

### 6.2 How page — already done

`ScoreLayersFigure` in
`frontend/src/features/system/DecisionFigures.tsx` and the surrounding
narrative in `HowNarrative.tsx` were updated on 2026-07-26 and already
describe the layered contract. Verify they still match the shipped behaviour
at the end of the migration, particularly the 43/57/65/70 validation figures.

### 6.3 Anything rendering a 0–100 score

Search for score rendering and remove it. There is no longer a synthetic
score number, only a rank and its components. Do not invent a display score
to preserve the old layout.

---

## 7. Validation — required before this is called done

1. **Unit tests** (`tests/scoring/test_attention.py`, rewritten):
   - one entity voting several times counts once;
   - a rejected entity does not vote;
   - the author never appears as a voter;
   - self-amplification adds no vote;
   - layer 2 breaks a layer-1 tie in the expected direction;
   - layer 2 does **not** override a layer-1 difference (3 low-position voters
     beat 2 high-position voters);
   - `mean_position` is `0.0`, not a division error, at zero voters;
   - identical inputs produce identical order across shuffled input.
2. **Regression tests**: update `tests/test_web_feed.py` and
   `tests/test_web_events.py` to the new payload. Assert that lane filtering
   and search do not change an item's rank.
3. **Replay** (`fli attention-score evaluate --json --no-input`) over the 15
   saved days. Record the output under `resources/`. The **required** check is
   that the vote-count hit-rate gradient survives: 1 vote ≈ 43%, 2 ≈ 57%,
   3–4 ≈ 65%, 5+ ≈ 70%. If the gradient inverts or flattens, stop and report;
   the primary signal is the whole basis of the design.
4. **Layer attribution**: report what share of top-100 admissions each layer
   decided, per day. Expect layer 1 to dominate on busy days and layers 2–4 to
   decide most admissions on quiet days (2026-07-19 has 397 Events at ≥1 vote
   for 100 slots). This number must go in the write-up — do not present the
   tie-breakers as decorative.
5. **`scripts/check-fast.sh`** passes.
6. **Visual proof**: build the SPA (`npm --prefix frontend run build`), reload
   the always-on app at `127.0.0.1:8797`, and confirm the Feed disclosure and
   `/how#why-rank` both render the layered contract. Keep captures in `tmp/`.

---

## 8. Documentation to update in the same change

Do not leave these describing the old formula:

- `docs/references/signal-feed.md` — the "Daily Score and Daily Rank" section
  states the 55/25/20 split and calls engagement "log-scaled". Both become
  false. (The `log1p` was in any case provably inert under a rank transform;
  do not carry that claim forward.)
- `docs/references/scoring-validation.md` — section 3 describes the
  attention-v1.1 → top-100 gate. Add the vote-count gradient as the primary
  scoring validation, and keep the top-100 censoring limitation.
- `docs/architecture/overview.md` and `docs/architecture/code-map.md` —
  scoring module ownership changes; `trusted_attention.py` is deleted.
- `docs/references/implementation-contracts.md` — any score contract text.
- `docs/STATUS.md` — the Feed + daily score row, and the "Deliberately
  Deferred" bullet that currently says Attention Score v2 is archived and
  production stays on the day-relative formula.
- `docs/references/build-log.md` — one entry, per the build-log contract:
  this is a material decision, not routine work.

---

## 9. Known consequences the engineer must not silently absorb

1. **Reranking changes the submitted proof.** The five showcase Insights and
   the numbers in `scoring-validation.md` were produced under
   `attention-v1.1`. After migration the live product will order days
   differently from what was submitted on 20 July. Adi has accepted this and
   has a snapshot. Do not attempt to preserve the old ordering — but **do**
   report, in the replay output, which of the five submission Events change
   rank, so the interview answer can be precise.
2. **Public engagement cannot currently be validated.** Only 5 of 1,442 judged
   Events (0.3%) sit below the 50th engagement percentile, because engagement
   was itself part of the score that selected the judged set. Demoting it to
   layer 4 is defensible; asserting it is useless is not supported by evidence.
   Write it up as untestable-under-current-censoring, not as disproven.
3. **Frontier-lab cold start remains unsolved.** 34% of frontier-lab Events
   receive zero trusted votes and will still rank low. This is a disclosed
   limitation, not a bug to patch with a seed vote.
4. **The recall probe is not part of this task.** Routing ranks 101–200 for one
   day is tracked separately and needs Adi's approval before spending.

---

## 10. Done when

- [ ] `attention.py` exposes only the layered contract; `trusted_attention.py`
      is deleted; no weight, cap, or knee constant remains in `src/fli/scoring/`.
- [ ] Feed, Events, CLI, and API emit the new `score_components` with no
      legacy aliases.
- [ ] Feed disclosure and `/how#why-rank` describe exactly the shipped
      behaviour.
- [ ] Unit, web, and regression tests pass and cover every invariant in §2.
- [ ] Replay output over 15 days is stored under `resources/`, including the
      hit-rate gradient, layer-attribution shares, and submission-Event moves.
- [ ] All documents in §8 updated.
- [ ] `scripts/check-fast.sh` passes and the local UI is visually verified.
