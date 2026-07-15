# Audience Insights v2

## Goal

Build two useful cited-insight views—AI Engineering and Investment—from one
clean, inspectable Evidence envelope. Rebuild the product with Adi one visible
step at a time: route one envelope, extract one audience insight, inspect it,
then expand only after the simple version is trustworthy.

The product bar is not pipeline sophistication. A reader should discover a
specific claim that changes an engineering action or investment question, with
an exact source passage and honest attribution.

## Current State

- Feed and Evidence are live and inspectable.
- Artifact admission was rebuilt around the root X account and its same-author
  reply thread. The deterministic lineage audit currently passes with zero
  violations across 1,859 accepted candidates and 1,334 artifacts.
- Reaction-owned artifacts no longer leak into the root envelope.
- All previously generated `data/derived/audience-insights-v2/` data was
  intentionally deleted. The live Insights product is honestly empty.
- Old prompts, runners, reviewers, editors, audits, tests, and design resources
  remain as historical implementation evidence, not as the active product
  contract.
- No persistent autonomous Codex goal is active. Work proceeds collaboratively
  from the current batch.

## Active Product Shape

```text
accepted Feed envelope
  -> application validates immutable evidence and provenance
  -> one audience router
       -> AI Engineering: useful yes / no
       -> Investment: useful yes / no
  -> separate extractor for each yes audience
  -> application binds one exact quote to source provenance
  -> simple audience view
```

The four routes—Engineering only, Investment only, both, neither—are derived
from two independent booleans. Feed remains the only owner of `keep` / `drop`;
Insights must not introduce a second general relevance decision under the same
name.

## Frozen Decisions

1. **One shared evidence core.** Root, same-author continuations, reactions,
   and canonical artifacts remain discrete numbered blocks with their own
   authorship, relation, URL, and source hash.
2. **Reaction text and reaction artifacts are different.** Replies and
   quote-posts already frozen in the Feed envelope may be routed or cited as
   independently authored claims. Their linked artifacts do not attach to the
   root author's artifact lineage.
3. **No popularity inputs.** Router and extractors do not see Feed rank,
   engagement, followers, Registry prominence, or editorial scores.
4. **One combined router, separate outputs.** The first version uses one model
   call with separately defined AI Engineering and Investment standards and
   two independent yes/no results. It does not generate insight prose.
5. **Separate extraction.** Only positive routes receive an audience-specific
   extraction call. Each extractor may still return no insight on closer review
   and returns at most one Insight per envelope for the initial MVP.
6. **Application-owned citations.** The model chooses a numbered block and
   exact contiguous quote. The application validates and binds source identity,
   URL, author, hash, and offsets.
7. **No old publication stack yet.** Daily editor, item reviewer, publication
   audit, finalization, recall, and historical reconciliation remain preserved
   but are not part of the rebuilt first version.
8. **No compatibility layer.** The new canonical schema may replace the old
   generated schema cleanly; deleted run data will not be migrated or restored.

## Open Product Decisions

- Inspect the exact cleaned block list for envelope
  `56ec1710fbc2f39b18aad549d21b38581a115b5dcf09d9b79dd4522d56bef56d`.
- Confirm verified author metadata for its X Article. The old packet left the
  artifact author empty; the rebuilt packet must not ask the model to infer it.
- Freeze the short audience-router prompt and minimal two-boolean JSON schema.
- Freeze the smallest reader-visible extraction fields for each audience.
- Decide how the first simple Insight result is stored and selected as active.

Initial reaction policy: include all independently authored reactions already
frozen into the Feed envelope. Do not fetch arbitrary additional X replies and
do not rank or truncate reactions until measured packet sizes or quality show a
real need.

## Current Batch

| Status | Work Item | Evidence |
| --- | --- | --- |
| done | Reset generated Insight data and remove the reviewed/publication mode from the active product. | `data/derived/audience-insights-v2/` absent |
| done | Rebuild and mechanically audit primary-author artifact lineage. | `fli artifacts audit-lineage --no-input` passes |
| done | Audit the proposed architecture and record the two-stage design with guardrails. | `resources/minimal-envelope-routing-v0.md` |
| in_progress | Inspect the exact Satya envelope blocks with Adi and freeze the minimal router prompt/schema. | envelope `56ec1710...bef56d` |
| pending | Run only that envelope through the router and inspect both decisions. | no model call before prompt agreement |
| pending | Freeze minimal per-audience extraction schemas and run positive routes for that envelope. | exact citation required |

## Milestones

- [x] **M0 — Clean evidence boundary.** Artifact lineage is primary-author
  scoped, audited, and guarded by fast checks; old generated Insight data is
  removed.
- [ ] **M1 — One-envelope routing proof.** The complete Satya envelope is
  rendered with verified authorship; the jointly reviewed router returns two
  inspectable audience decisions.
- [ ] **M2 — One-envelope extraction proof.** Positive audiences yield at most
  one concise result each with an application-bound exact quote.
- [ ] **M3 — One-day product proof.** One inspected day is stored and rendered
  in both audience views using current Feed rank only as dynamic provenance.
- [ ] **M4 — Bounded quality check.** Audit several clear yes, clear no, both,
  and neither envelopes; compare the combined router against separate audience
  judgments for cross-audience bias.
- [ ] **M5 — Controlled expansion.** Expand to additional days only after Adi
  approves the one-day proof. Add daily selection or further audits only when a
  demonstrated product failure requires them.

## Done When

- One immutable envelope can independently route to AI Engineering,
  Investment, both, or neither.
- Every positive result is audience-specific, concise, and bound to one exact
  source passage with correct authorship.
- False-positive routing can safely terminate as no insight during extraction.
- One inspected day works end to end in the live UI without old reviewed/editor
  data or stored Feed-rank divergence.
- Focused tests, `scripts/check-fast.sh`, production build, and rendered browser
  checks pass for the implemented slice.
- Expansion beyond the inspected day is explicitly approved after review.

## Validation Plan

- Run `PYTHONPATH=src python -m fli.cli artifacts audit-lineage --no-input`
  after evidence/artifact changes.
- Fixture-test block authorship, relations, immutable hashes, reaction text,
  and exclusion of reaction-owned artifacts.
- Schema-test both router booleans and all four derived outcomes.
- Verify extractors never receive rank or engagement fields.
- Reject altered, absent, repeated, or wrong-block quotations mechanically.
- Inspect the first envelope and first day in the live desktop UI with
  `$agent-browser` after implementation.
- Run `scripts/check-fast.sh` before each implementation handoff.

## Historical Resources

- `resources/audience-contracts.md` — previous extraction/editor/evaluation
  contract; useful design evidence, not active scope.
- `resources/minimal-envelope-routing-v0.md` — current design handoff.
- `learnings.md` — durable findings from the previous implementation.
- Git history before the 2026-07-15 reset preserves the detailed autonomous
  plan and progress log removed from this active tracker.

## Recent Progress

- 2026-07-15: Deleted all generated Audience Insights v2 run/audit data while
  preserving implementation and learnings.
- 2026-07-15: Rebuilt Artifact Store admission around the primary X account and
  same-author reply lineage; corpus audit passes with zero violations.
- 2026-07-15: Simplified the visible Insights product to one Feed-linked path;
  reviewed/publication stages are not active UI modes.
- 2026-07-15: Audited the proposed redesign and adopted one complete-envelope,
  two-boolean audience router followed by separate positive-route extraction.
  The exact schema and prompts remain intentionally unfrozen for review with
  Adi in the next session.
