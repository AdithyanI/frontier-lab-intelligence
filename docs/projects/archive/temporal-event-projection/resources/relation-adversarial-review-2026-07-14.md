# Relation Adversarial Review — 2026-07-14

## Post-repair resolution

The original findings below are retained as the pre-repair adversarial record.
Current source, regression fixtures, and the final July 5–13 corpus resolve
the structural defects as follows.

| Review item | Resolution | Status / evidence |
| --- | --- | --- |
| Opaque targets split components | ID-only provider targets are stored as non-renderable `feed_anchor` rows and participate in exact unioning without fabricated content or timestamps. | **Implemented** in `src/fli/signal_feed.py`; covered by opaque-anchor Feed, Event, and API tests. |
| Nested quote/retweet relations | Embedded relations are traversed recursively with cycle protection; richer duplicate occurrences retain their nested edges. | **Implemented**; covered by recursive-chain, direct/rich embedded, and order-independence tests. |
| Root and event identity drift | Daily/weekly identities derive from the provider-edge component visible at cutoff rather than mutable full-run membership or inbound popularity; a later-disclosed bridge cannot rewrite an earlier projection. | **Closed for cutoff projections.** Seven-day fingerprints are unchanged inside the independent nine-day build. A general cross-generation alias ledger remains deferred. |
| Rejected Registry bridge | The visible surviving graph is re-componentized after Registry filtering so disconnected survivors cannot remain in one envelope or disappear. | **Implemented** in `src/fli/web/events.py`; covered by `test_rejected_bridge_preserves_every_surviving_exact_component`. |
| Duplicate embedded snapshots | Canonical occurrence selection is deterministic and richness-based rather than traversal-order-based; Feed v8 preserves the selected raw snapshot and first-disclosure provenance. | **Closed.** Independent repeat builds have identical run IDs and semantic audit hashes. |
| Missing reply flag | A non-empty reply-parent ID independently classifies a post as a reply and creates the exact parent relation. | **Implemented** in `src/fli/signal_feed.py`; covered by reply-parent tests. |
| Provider-unsafe conversation grouping | Conversation IDs are metadata only and never union keys. Quote, retweet, and explicit reply-parent are the only provider-qualified grouping edges; singleton identities are provider-qualified posts. | **Closed.** The final largest-component audit found no conversation-only merge. |
| Implicit latest-run activation | Readers use the explicitly published Event run and its validated Feed run rather than the newest-created experiment. | **Implemented** via `signal_publication`; covered by atomic-publication regression. |
| Known Greg/OpenAI/Ben duplicate | The recursive structural contract now absorbs quoted wrappers into the canonical target envelope instead of emitting an independently triaged top-level row. | **Closed.** Final corpus preserves OpenAI ← Greg ← Ben inside one 69-member event and one hash-bound triage input. |
| Final adversarial proof | Full nine-day relationship-loss, future-disclosure, absorbed-top-level, false-split/merge, and independently-triaged-duplicate audit after final regrouping. | **Closed.** Final audit returns `ok=true`, zero failures; see the rebuild audit. |

## Verdict

The recursive relation repair is the correct direction and fixes the reported
quote-of-quote split. It is not yet safe to call the relation layer finished.
The remaining risks are narrow and testable: opaque/deleted targets still cause
false splits, legitimate component merges can invalidate event IDs, and
Registry filtering can disconnect an already-materialized component.

This review is deliberately limited to exact provider-declared structure. It
does not recommend semantic clustering, URL clustering, or additional scoring.

## Intermediate corpus proof

The counts below predate Feed v8 / Event v3 and the provider-edge-only
contract. They remain useful diagnosis, not final closeout evidence.

The review rebuilt the July 5–11 slice into temporary stores from the immutable
raw X corpus.

| Measure | Existing event build | Recursive repair build |
| --- | ---: | ---: |
| Direct posts | 11,062 | 11,062 |
| Normalized posts | 15,642 | 16,078 |
| Exact relations | 8,232 | 9,347 |
| Event clusters | 4,814 | 4,136 |
| Event members | 13,436 | 13,897 |
| Event links | 8,898 | 10,059 |

Provider payloads reach three embedded levels. The repaired build found no
directed cycles in this slice. It merged 344 repaired components that had been
split across 1,022 old event IDs. The largest repaired components corresponded
to recognizable cascades such as the Anthropic workspace research post,
Prime Intellect funding announcement, OpenAI GPT-Live launch, and Muse Spark
launch. That is strong evidence that the recursive repair is recovering real
structure rather than merely inflating groups.

Large exact components still deserve a bounded visual spot-check before the
production rebuild: 115 of 4,136 components have more than one terminal
structural target, and 26 contain more than one conversation anchor. Those
counts are ambiguity indicators, not proof of incorrect merges.

## Findings

### P1 — Opaque embedded targets still create false splits

`signal_feed._post_record()` rejects any target without both an ID and a
parseable timestamp (`src/fli/signal_feed.py`, around lines 195–204). The
recursive walker then skips the relation entirely when `_post_record()` returns
`None` (around lines 420–430).

In the reviewed slice:

- 169 distinct embedded target IDs were present only as non-renderable stubs;
- 20 of those target IDs were referenced by more than one selected wrapper;
- 46 wrappers are therefore known candidates for false splitting;
- one opaque target was referenced by six wrappers.

These are often deleted, withheld, or incomplete provider objects. Their text
does not need to be rendered, but their immutable post ID is still valid exact
relationship evidence.

**Recommendation:** preserve a relation anchor when the target ID exists even
if the target cannot become a `feed_post`. The smallest clean model is an
opaque provider-post anchor (provider + post ID) which can participate in
unioning but is never rendered as evidence. Do not fabricate a timestamp or
text. Expose a run counter for `opaque_target_count` and
`shared_opaque_target_count`.

### P1 — Component merges need explicit event lineage

The new canonical identity correctly stops inbound popularity from changing a
root. The concrete failure that prompted this review was:

- original `2075534978788536572` (@antirez);
- reply `2075556530976350484` in the same conversation;
- one retweet of the original and one quote of the reply on July 10;
- one new quote and two new retweets of the reply on July 11.

The earlier inbound-count rule changed the representative from the original to
the reply merely because the reply gained more wrappers. Using the unique
conversation anchor fixes that specific instability.

There is a more general issue: when a later exact edge joins two components,
both prior event IDs cannot remain canonical. Comparing cumulative July 5–10
and July 5–11 builds after the conversation-anchor repair showed 81 shared posts
moving across 18 old-to-new event-ID mappings. Those are primarily legitimate
new bridges, not necessarily clustering errors, but any triage keyed only by
the discarded event ID becomes stale.

**Recommendation:** treat this as event lineage, not as a hash trick. On a
rebuild, record old event ID → new event ID aliases for merged components and
use the alias when carrying forward triage. If lineage is intentionally
deferred for the submission, rerun triage after the repair and document that
event IDs are rebuild-scoped rather than permanently stable.

### P1 — Registry filtering can leave a disconnected visible envelope

Exact components are built before Registry state is applied. The web projection
then removes rejected authors member-by-member (`src/fli/web/events.py`, around
lines 355–400) but does not recompute connectivity. For a chain `A → B → C`,
rejecting bridge `B` can leave unrelated visible nodes `A` and `C` inside one
envelope, or make the whole group fall back to singleton rows depending on
which node is the canonical root.

**Recommendation:** after visibility filtering, compute connected components
over the surviving links. Render only the connected component containing the
canonical root; project other surviving components independently or suppress
them according to an explicit product rule. A rejected source may be excluded
from attention without discarding an embedded non-Registry target that is
needed solely as structural provenance.

### P2 — Multiple embedded snapshots overwrite one another arbitrarily

`_insert_post()` updates every normalized field on conflict
(`src/fli/signal_feed.py`, around lines 263–289). The recursive traversal can
encounter the same non-direct embedded post many times, and the last traversal
wins.

In the reviewed slice, 424 non-direct IDs had multiple normalized variants.
Almost all differences were engagement counters captured at different times,
but five IDs also varied in inferred `post_type` because one occurrence carried
the nested quote and another did not. This does not currently erase relation
edges, but it can change display metadata and root tie-breaking.

**Recommendation:** choose one canonical occurrence before insertion. Prefer a
direct observation; otherwise prefer the occurrence with the richest exact
relationship payload, then the latest provider observation. Merge non-null
metadata rather than depending on traversal order. Keep engagement snapshots
separate from canonical post identity when that becomes useful.

### P2 — Reply classification has a schema inconsistency

`_post_record()` labels a reply only from `isReply` / `is_reply` while it stores
`inReplyToId` independently (`src/fli/signal_feed.py`, around lines 208–235).
The current reviewed payloads are internally consistent, so this did not cause
an observed split. It is still a fragile provider boundary.

**Recommendation:** classify as reply when either the explicit reply flag or a
non-empty parent ID is present. Add a fixture containing only `inReplyToId`.

### P2 — Conversation grouping is not provider-safe for future sources

`replies_by_conversation` is keyed only by conversation ID
(`src/fli/signal_events.py`, around lines 347–379) and chooses the provider from
the first member. The current store has one provider, so there is no present
bug. With a second provider, equal-looking IDs could fail to group correctly or
collide conceptually.

**Recommendation:** key conversation groups by `(provider, conversation_id)`.
This is a small boundary fix; it does not require implementing RSS or GitHub.

### P2 — Latest-created run is not necessarily the intended publication run

Both feed/event readers select the latest `created_at` run. A later narrow
seven-day experiment can silently replace a wider official run in the UI. A
fresh July 5–13 proof must use nine days; running the CLI default of seven days
would drop July 5–6 and fragment temporal lineage.

**Recommendation:** either persist an explicit published/current run pointer or
require the reader to choose a run covering the requested day and expected
window. For the immediate rebuild, pass `--days 9` explicitly and assert all
nine dates before publication.

## Projection behavior that is now correct

The current web projection filters members whose publication day is later than
the selected day and uses the event store's canonical representative rather
than choosing a root from only that day's ranked candidates. Keep this model:

- Monday shows the event as known by Monday cutoff;
- Tuesday shows the same canonical event with Monday context plus Tuesday's new
  evidence;
- the event appears on Tuesday only when `event_day` records direct Tuesday
  activity;
- weekly output can deduplicate by canonical event lineage.

This behavior needs regression coverage because it is the central temporal
contract.

## Required regression fixtures

1. **Recursive quote chain:** `C quotes B`, `B quotes A`; all three members,
   both edges, root `A`, and only one top-level envelope.
2. **Nested retweet/quote chain:** retweet of a quote of an original; preserve
   both edge types and absorb the middle wrapper.
3. **Original plus quoted wrapper:** the Greg Brockman / OpenAI shape; the quote
   must be evidence inside the OpenAI-rooted envelope, never a second top-level
   candidate.
4. **Wrapper amplification cannot move root:** add arbitrary quotes/retweets to
   a reply; event root and ID remain the conversation root.
5. **Component merge lineage:** two prior components become connected by one
   later exact wrapper; assert alias/carry-forward behavior for prior triage.
6. **Cross-day cutoff:** Monday response excludes Tuesday member; Tuesday
   response includes Monday context and Tuesday delta; both share canonical
   lineage.
7. **No future leak:** adding Wednesday evidence cannot change serialized
   Monday snapshot content/hash.
8. **Opaque shared target:** two wrappers point to an ID-only/deleted target;
   they group through a non-renderable anchor without a fabricated post.
9. **Missing reply flag:** `inReplyToId` without `isReply`; preserve
   `reply_parent` relation.
10. **Cycle:** `A quotes B`, `B quotes A`; traversal terminates, stores both
    edges once, and chooses a deterministic fallback root.
11. **Rich/poor duplicate occurrence:** one embedded occurrence contains a
    nested target and another does not; canonical post metadata and both edges
    are independent of input row order.
12. **Rejected bridge:** `A → B → C`, reject `B`; never render disconnected
    `A` and `C` as one envelope and never duplicate either top-level.
13. **Multi-provider conversation IDs:** identical conversation strings from
    two providers remain separate.
14. **Run coverage:** a later narrow run cannot make previously published dates
    disappear from the read model.

## Acceptance bar for the overnight rebuild

- The known Greg/OpenAI/Ben nested-quote example produces one envelope rooted
  at the OpenAI post.
- All direct members absorbed by an exact component disappear as independent
  top-level rows.
- July 5–13 is rebuilt as one explicit nine-day source window.
- Triage is rerun only after the corrected event build; stale event IDs are not
  silently reused.
- The cross-day and rejected-bridge fixtures pass.
- The top 20 largest repaired components and every component with more than one
  terminal root receive a bounded automated summary plus a manual sample; any
  false merge is recorded before publication.
- Fast checks pass, and the final tracker records before/after counts and the
  exact production run IDs.
