# Implementation spec — layered Event rank (`daily-rank-v2`)

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
3. author_position         float  network position of the Event root author, 0–1
4. public_interactions     int    peak one-post likes + replies + reposts + quotes
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

1. **The complete Event is the ranking unit.** Do not score individual posts
   and then choose a winning member. First construct the canonical-day Event,
   then union the trusted voters from every same-day member post and rank that
   Event once.
2. **One entity, one vote.** A canonical Registry entity contributes at most
   one vote to the complete Event regardless of how many member posts it
   authored, quoted, or reposted.
3. **Only `active` Registry entities vote.** `rejected` entities are excluded
   at read time, as today. Registry curation must keep changing derived views
   without touching raw evidence.
4. **The Event root author is not a voter.** Resolve the canonical
   presentation/source root author after Event construction, then remove that
   entity from the complete voter union. The author's standing enters at layer
   3 only. A root author interacting with another Event member cannot create a
   free vote.
5. **Canonical-day scoped.** Voters and public interactions come only from
   candidates visible on the Event's canonical publication day. Later Event
   activity may enrich the card but must never retroactively change that
   historical rank.
6. **Root-author semantics.** Layer 3 is the entity-level network position of
   the canonical presentation/source root author, or `0.0` when that author is
   not a ranked Registry entity. It is never the highest-ranked member author.
7. **Public-interaction semantics.** Calculate
   `likes + replies + reposts + quotes` for each canonical-day member post and
   use the maximum one-post total. Do not sum across the Event: that would
   reward Events merely for having more member posts. Do not include views or
   bookmarks.
8. **Day-scoped.** Ranks from different UTC days are never compared.
9. **Editorial-blind.** Audience routing judgments and editorial outcomes
   never enter any layer.
10. **Deterministic.** Equal inputs must produce an identical order across
   runs and processes. `event_id` is the terminal tiebreak.

### Network position (used by layers 2 and 3)

`position = entities_below / (total − 1)`, where `entities_below` is the count
of ranked canonical entities with a **strictly lower** entity-union
`support_count`, and `total` is the count of ranked canonical entities in that
run. The top unique support level → `1.0`; entities tied on support receive the
same position; the bottom support level → `0.0`. If `total == 1`, position is
`1.0`. An entity absent from the ranking run has position `0.0`.

Use `support_count` only to order entities into this tie-aware percentile; do
not put its raw magnitude into the Event rank. `support_count` is severely
right-skewed (top entity 2,041; median in the low tens), so using its magnitude
would let a handful of accounts dominate layer 2 — reintroducing the celebrity
problem the layering exists to avoid. A dense `support_rank` transform is also
wrong because it spaces support levels equally regardless of how many entities
are tied at each level. Use `fli.network.view.entity_network_ranks()` as the
source, specifically `network_entities_below` and `network_rank_total`. Do not
use account-level `ranking_result.position`: a multi-channel organization is
one canonical entity and must receive its entity-union position.

---

## 3. Where the data already is

| Input | Source today | Notes |
| --- | --- | --- |
| Voters per member post | `amplifiers` on Feed candidates, built in `src/fli/web/feed.py` | Deduplicated per post and excludes rejected entities. Event projection unions these again by `entity_id` and then excludes the Event root author. |
| Event membership and root | `src/fli/web/events.py::_project_component()` | This is the first seam where the complete canonical-day Event, root author, and same-day candidates are all known. Ranking belongs here. |
| Public interactions | `_public_engagement(row)` in `feed.py` | One-post sum of likes, replies, reposts, and quotes. Event projection takes the maximum across canonical-day members. |
| Entity rank table | `fli.network.view.entity_network_ranks()` over `entity_support_result` | Keyed by canonical `entity_id`; exposes the audit-only `network_rank`, plus `network_entities_below` and `network_rank_total` for the tie-aware position. |

**Gap to close:** amplifier rows carry raw account-derived `network_support`
but not the canonical entity position. Add the entity position derived from
`entity_network_ranks()` and use it for both voters and the root author.

---

## 4. Code changes

### 4.1 `src/fli/scoring/attention.py` — replace, do not extend

Delete `AttentionFormula`, `ATTENTION_V1_1`, `ATTENTION_V2_CANDIDATE`,
`percentiles`, `saturating_log`, and `score_components`.

Replace with a small pure module:

```python
DAILY_RANK_VERSION = "daily-rank-v2"

@dataclass(frozen=True)
class Voter:
    entity_id: int
    position: float          # 0–1 network position

@dataclass(frozen=True)
class RankInputs:
    voters: tuple[Voter, ...]        # deduplicated, author excluded
    author_position: float           # 0–1, 0.0 if unranked
    public_interactions: int
    event_id: str

def sort_key(inputs: RankInputs) -> tuple:
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

### 4.3 `src/fli/web/feed.py` — expose Event inputs, not a post score

Remove `apply_attention_scores()` and every percentile/weight/scalar-score
field. Feed candidates remain the raw member-post input to Event projection:

- attach the canonical entity network position to each amplifier;
- retain one-post `public_interactions`;
- retain author identity so Event projection can resolve the root author;
- do not assign a final daily rank to a member post.

The public Feed product consumes Events, so no user-facing surface should claim
that this intermediate post ordering is the daily Event rank.

### 4.4 `src/fli/web/events.py`

`_project_component()` is the scoring boundary. After the complete Event and
root are known:

- union canonical-day member voters by `entity_id`;
- remove the root author's entity;
- resolve voter and author positions from `entity_network_ranks()`;
- take the maximum one-post canonical-day public interaction count;
- attach one top-level `rank_components` object to the Event.

Delete `peak_attention_score`, `daily_score_basis`, and the highest-scoring
member/template rule. Root presentation must not decide rank inputs. Sort the
complete unfiltered daily Event projection once, attach stable `daily_rank`,
then apply lane, routing, search, and pagination controls.

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

Historical routing rows remain useful only as censored outcome labels. Join
them to freshly projected Events by `(day, event_id)`; never reconstruct the
new rank from old stored `score_components`.

### 4.6 `src/fli/cli.py`

`daily-rank evaluate` replaces the old score command cleanly. Remove any
subcommand, flag, or output field referring to formula versions, weights,
`amplifier_cap`, or `support_knee`.

---

## 5. API contract change

`FeedRankComponents` in `frontend/src/shared/api/evidence.ts` and its Python
producer become a top-level Event field. New shape:

```jsonc
{
  "trusted_votes": 5,
  "voters": [                        // ordered by position desc
    { "entity_id": 42, "entity_name": "roon", "position": 0.995 }
  ],
  "mean_voter_position": 0.936,
  "author_position": 0.957,
  "public_interactions": 14602,
  "decided_at_layer": 1              // 1-5 against the adjacent lower Event
}
```

Remove `network_attention_percentile`, `originator_support_percentile`,
`public_engagement_percentile`, `network_attention_factor`,
`originator_support_factor`, `public_engagement_factor`,
`originator_network_support`, `attention_score`, `peak_attention_score`, and
`daily_score_basis`. Do not keep aliases.

`decided_at_layer` is what makes the UI honest and is worth the small cost:
it names which question first separates this Event from the Event ranked
immediately below it. For the final Event, compare with the one immediately
above. Layer `5` means the four substantive layers tied and `event_id` supplied
determinism only.

---

## 6. UI changes

### 6.1 Feed rank disclosure — `frontend/src/features/evidence/FeedPage.tsx`

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

Keep the existing limitation footer, updated: the rank prioritizes what to
inspect; it is not importance, truth, or quality; days are not comparable.

### 6.2 How page — already done

`ScoreLayersFigure` in
`frontend/src/features/system/DecisionFigures.tsx` and the surrounding
narrative in `HowNarrative.tsx` were updated on 2026-07-26 and already
describe the layered contract. Verify they still match the shipped behaviour
at the end of the migration, particularly the final
34.3/53.9/64.2/72.1 routing-label gradient.

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
3. **Replay** (`fli daily-rank evaluate --json --no-input`) over every
   currently published saved day. Record the output under `resources/`. The
   **required** check is
   that the vote-count hit-rate gradient survives. The final current cohort is
   1 vote 34.3%, 2 votes 53.9%, 3–4 votes 64.2%, and 5+ votes 72.1%. If the
   gradient inverts or flattens, stop and report; the primary signal is the
   whole basis of the design.
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
   has a snapshot. Do not attempt to preserve the old ordering. An
   old-versus-new comparison is optional and must not block the clean
   migration.
2. **Public engagement cannot currently be validated.** Only 5 of 1,442 judged
   Events (0.3%) sit below the 50th engagement percentile, because engagement
   was itself part of the score that selected the judged set. Demoting it to
   layer 4 is defensible; asserting it is useless is not supported by evidence.
   Write it up as untestable-under-current-censoring, not as disproven.
3. **Frontier-lab cold start remains unsolved.** 34% of frontier-lab Events
   receive zero trusted votes and will still rank low. This is a disclosed
   limitation, not a bug to patch with a seed vote.
4. **The recall probe is not part of this task.** Routing ranks 101–200 for one
   day is tracked separately and does not block the migration.
5. **Downstream state must move atomically as a product contract.** A new top
   100 with old routing, Insights, or briefs is not a completed migration.
   Refresh routing first, then per-Event Insights, then daily editorial
   workspaces/briefs. Regenerate content-addressed PDFs and UI projections from
   the completed new editorial state. Reuse exact cached judgments where the
   current tools prove Event/evidence/input/model identity.

---

## 10. Done when

- [x] `attention.py` exposes only the layered contract; `trusted_attention.py`
      is deleted; no weight, cap, or knee constant remains in `src/fli/scoring/`.
- [x] Events, CLI, and API emit the new `rank_components` with no
      legacy aliases.
- [x] Feed disclosure and `/how#why-rank` describe exactly the shipped
      behaviour.
- [x] Unit, web, and regression tests pass and cover every invariant in §2.
- [x] Replay output over every currently published day is stored under
      `resources/`, including the hit-rate gradient and layer-attribution
      shares.
- [x] Routing, per-Event Insights, daily editorial briefs, PDFs, and UI
      projections are complete for the migrated cohorts.
- [x] All documents in §8 updated.
- [x] `scripts/check-fast.sh` passes and the local UI is visually verified.
