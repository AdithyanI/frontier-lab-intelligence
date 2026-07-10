# Entity Spine Bootstrap — Archived Tracker

Status: archived 2026-07-10. This tracker preserves the evidence-import and
entity-spine phase of the BIT Capital case-study product. The overall product is
not complete; execution continues in
`docs/projects/entity-kind-classification/tasks.md`.

Full prompt and original materials:
- Prompt capture: `docs/references/case-prompt.md`
- Original PDF + OCR text: `docs/references/source-material/`

Build history, tools, budget, and learning notes now live in
`docs/references/build-log.md`.

## Deadline / Deliverable

- **Deadline:** 2026-07-20, from Lars's email.
- **Deliverable:** working system + code + database/schema/real data +
  architecture/model rationale + prompts + evals + tokenomics + final report.
- **Rubric:** registry 20%, signal-vs-noise 20%, scoring/validation 20%,
  actionable delivery 15%, ingestion 10%, extraction 10%, web UI 5%.
- **Budget:** €100 reimbursable API/services budget; log spend in
  `docs/references/build-log.md`.

## Closeout Summary

The scoped bootstrap phase is complete:

- Frozen Digg, AI High Signal, smol.ai, and Adi-following evidence is stored
  with provenance.
- The visible Registry contains 2,966 provisional entity clusters: 10 seeded
  labs and 2,956 unknowns.
- All 2,998 channels have exactly one owner; the legacy graph contains one
  additional hidden source account, `@adithyan_ai`.
- The Registry UI exposes the full entity universe without presenting rank,
  follower count, or list membership as identity labels.
- Structural kind classification, channel merging, and track/reject curation
  were deliberately transferred to later projects rather than conflated here.

The one-time 2,000-follower cleanup is the only reproducibility exception:
rerunning the following import restores the unfiltered snapshot, and a later
channel sync may rematerialize Adi's source node. This limitation is accepted
for this archived phase and carried into the next tracker.

## Fresh-Agent Context

- **Product:** frontier-lab intelligence from public evidence; Digg is a frozen
  bootstrap source, not the intended long-term product or data provider.
- **Local preview:** `http://127.0.0.1:8797/`, served by launchd
  `com.dobby.frontier-lab-intelligence`. Rebuild UI with
  `npm --prefix frontend run build`; do not start another preview server.
- **Original Digg import:** 1,000 ranked accounts. Loading their full follower
  graph produced 2,314 distinct account rows and 361,225 directed edges because
  edge endpoints include accounts outside the ranked 1,000.
- **Curated additions:** AI High Signal has 609 members. smol.ai `prefPeople`
  has 33 raw entries / 31 unique handles. Their union is 619 unique handles;
  after overlap with existing graph accounts, the database grew from 2,314 to
  2,608 accounts, a net addition of 294 account rows.
- **Current source agreement:** among the 31 smol.ai handles, 17 occur in Digg
  + AI High Signal + smol.ai, 4 occur in both curated lists but not Digg, and
  10 occur only in smol.ai. The smol import added eight account rows:
  `akhaliq`, `danhendrycks`, `labenz`, `lucidrains`, `philschmid`,
  `rohanpaul_ai`, `thebloke`, and `tom_doerr`.
- **Current DB:** 2,967 X graph accounts, 2,998 channels, 12,664 account source facts,
  361,863 graph edges, 21,133 channel observations, 10 lab entities, and 2,998
  entity-channel links.
- **Model distinction:** `accounts` is the legacy X-specific graph table.
  `channels` is the canonical cross-source location model: 2,966 X channels
  plus 10 websites, 9 GitHub channels, 8 arXiv channels, and 5 blogs. Each X
  candidate account is mirrored one-to-one into an X channel; `@adithyan_ai`
  remains only as the graph source node.
- **Source semantics:** list membership is evidence only. It must not
  automatically create a tracked person or imply quality. Preserve provenance
  in `account_source_facts` / `channel_observations`.
- **Paid provider:** TwitterAPI.io imported the AI High Signal X list using the
  machine-local key at `~/.secrets/twitterapi-io/api-key`; Adi added about $10
  credit. The smol.ai import used public GitHub and cost nothing.
- **Durable detail:** read `docs/architecture/overview.md` for schema and
  `docs/references/research-notes.md` for source provenance before changing
  ingestion or classification.

### Baseline Source Partition Before Adi Following

These groups use explicit list/ranking membership facts, not mere presence as
an endpoint in the Digg graph:

| Digg ranked | AI High Signal | smol.ai | Accounts | Meaning |
| --- | --- | --- | ---: | --- |
| yes | yes | yes | 17 | Strongest cross-source agreement; review first. |
| yes | yes | no | 213 | Confirmed by Digg ranking and the broad curated list. |
| yes | no | no | 770 | Digg-ranked only; likely contains much of the noise Adi wants filtered. |
| no | yes | yes | 4 | Independent curated agreement despite no Digg rank. |
| no | yes | no | 375 | Broad-list-only evidence; review more cautiously. |
| no | no | yes | 10 | Tiny-list-only anchors; inspect individually. |
| no | no | no | 1,219 | Accounts present only as Digg graph endpoints; PageRank may still make some useful. |

The first six rows contain 1,389 accounts with explicit membership/ranking
evidence. The seventh group explains why the account table is much larger than
the 1,000 ranked Digg accounts. “379 AI High Signal members new versus Digg”
means no Digg ranking fact; only 286 created new rows during that import because
many were already graph endpoints. smol.ai then created eight more rows, for a
net 294 accounts beyond the original 2,314-row Digg graph load.

### Adi Following Snapshot

The 2026-07-10 `adi_following` import fetched all 767 accounts followed by
`@adithyan_ai`. Of those, 282 already existed and 485 followed accounts were
new; the source account itself was also new, bringing the current universe to
3,094 accounts before cleanup. Adi then chose a one-time 2,000-follower floor:
638 source links remain, 129 were removed, 127 Adi-only accounts were deleted,
two accounts with independent evidence were preserved, and Adi's source account
was hidden from the Registry. Remaining overlap: 177 Digg-ranked, 126 AI High
Signal, 10 smol.ai, and 256 present in the prior graph. All 638 have follower
counts and 628 have non-empty bios. The provider returned pages 200/200/200/167. One
validation/repair rerun plus a 20-profile shape probe put the documented
following-page estimate at about $0.01928 total for this session; profile lookup
cost is negligible and separately unquantified.

### Decisions Already Made

- Keep the first version simple. Merge evidence before classification; do not
  create many status labels, roles, or confidence tiers just because the schema
  can support them.
- **Entity is identity, not endorsement.** Every observed channel resolves to
  one entity so imports are immediately usable. An unresolved identity has
  kind `unknown`; it is not silently treated as a person.
- The complete current Registry universe is 2,966 provisional identity clusters: 10
  known labs own their X and other official channels, while 2,956 clusters
  remain `unknown` under the current implementation.
- Kind classification answers only `lab` / `person` / `unknown`. Tracking
  answers `track` / `reject` later. Keep these as separate, evaluable stages.
- Digg rank, PageRank, follower count, list membership, and Digg role remain
  provenance/attention observations. They are not kind labels and should not
  enter the first kind-classifier input contract.
- The implemented `entities` table intentionally has no
  `frontier`/`emerging`/`candidate` status. Do not reintroduce those labels
  without a concrete product need. The older `labs.status` field and target
  sketches in architecture docs are legacy, not the current entity contract.
- Mental model: **entity = who**, **channel = where**, **entity-channel = proof
  that the channel belongs to the entity**, **observation = what was seen there
  at a time**.
- Labs are a small hand-curated seed because lab judgment is cheap and stable.
  People are evidence-derived candidates. A person may link to a lab later,
  but affiliation is optional and independent people remain valid.
- Do not treat Digg's `role` field as the final classification. Adi explicitly
  wants our own later classification and expects irrelevant names (for example
  broad celebrities or general-interest accounts) to be rejected.
- List membership is an input to judgment, not the judgment itself. The
  immediate likely decision vocabulary is only `track` / `reject`, with a
  reason, but Adi has not approved the final rule yet.
- Stop adding sources for now. The Anthropic staff list and broad Scoble lists
  are deferred. The former is lab-specific; the latter are likely noisy.
- Digg is retained only because the current graph/PageRank implementation still
  depends on its frozen edges. The desired future graph source is our own
  snapshot of **who trusted researchers follow**, not who follows them and not
  another live Digg pull.
- Lab X accounts are usually broadcast channels and relatively weak discovery
  seeds. Individual researchers/builders are more useful seeds for a future
  following graph.
- Avoid tooling expansion. The X-list importer stays generic by list id and
  source key; it has no provider selector, named-list shortcut, or artificial
  member/page cap. The smol.ai static list was imported once from pinned public
  source without adding another command.
- The product pipeline must eventually run end-to-end automatically and remain
  human-correctable. Human decisions become durable override evidence, not a
  mandatory per-item approval gate.

### Import And Provider Notes

- Generic command: `fli sources import-x-list --list-id <id> --source <key>`.
  It emits structured JSON, reads the TwitterAPI.io key from
  `~/.secrets/twitterapi-io/api-key`, writes each fetched page transactionally,
  and syncs X accounts into channels.
- AI High Signal command used list id `1585430245762441216`, source
  `ai_high_signal`, and `--page-sleep-seconds 0.4`. It completed 32 cursor pages
  and returned 609 members.
- X-list pages cannot be fetched in parallel because each request needs the
  previous response's `next_cursor`. Faster sequential pacing worked after Adi
  recharged the provider.
- The first live attempt failed with HTTP 402 before writes because credits
  were depleted. Adi then added about $10; exact EUR reimbursement has not been
  recorded. Never expose the API key in docs, logs, commands, or responses.
- smol.ai source is `oneoffs/preferredTags.ts` in
  `smol-ai/ainews-web-2025`, pinned at commit
  `0fc45e2c56e2b0cad71478bbee9cf5976c9e573e`. It required no paid API.

### Current UI And API Reality

- The SPA has only `/` (Registry) and `/architecture`. Unknown routes redirect
  to `/`; the old `/system` page was intentionally removed.
- `/api/status` still exists as a JSON health/pipeline endpoint. It is not a
  user-facing System page and should not be removed merely because `/system`
  was removed.
- `/api/accounts` is a compatibility workbench over X channels.
- `/api/registry` returns the complete 2,966-cluster universe: 10 labs, zero
  resolved people, and 2,956 unknowns. The frontend exposes the same counts and
  filters.
- The main Registry should stay lean. Raw source agreement, ranks, and follower
  observations remain available for later curation/evaluation rather than
  becoming permanent table columns.
- Of 2,967 graph accounts, 1,746 currently have a non-empty bio and 2,960 have a
  follower count. The eight smol-only account rows still have handles and source
  provenance but no fetched profile metadata.

### Next-Step Acceptance Check

The first entity-spine batch is accepted when:

1. All 2,998 channels link to exactly one provisional cluster.
2. The current visible universe contains exactly 2,966 rows: 10 labs, 0 resolved
   people, and 2,956 unknowns before resolver work begins.
3. Before the one-time personal-follow cleanup, re-running synchronization
   created no rows or material DB diff. The cleanup itself is intentionally
   not encoded as reusable policy, so this invariant no longer holds if the
   following import or channel sync is rerun.
4. `/api/registry` and the SPA expose all 2,966 clusters with only truthful,
   identity-bearing fields; Digg role is absent from the canonical UI.
5. Missing bios remain missing and no lab/person kind is inferred from rank,
   followers, or list membership.
6. Evidence invariants hold: Digg 1,000; AI High Signal 609; smol.ai 31;
   `adi_following` 638; graph edges 361,863.

## Residual Risks Handed Forward

- **Kind classifier:** Adi approved a narrow first pass with only
  `person` / `organization` / `unsure` and a short reason. The implementation
  and calibration set are owned by the next tracker.
- **Track/reject rule:** deliberately separate and undecided. Do not assume
  source count alone equals importance.
- **Legacy migration:** `accounts` and `account_source_facts` still back graph
  code while `channels` and `channel_observations` are the product model. Do
  not delete the legacy layer until graph consumers have migrated.
- **Database artifact policy:** prompt asks for schema + real data; decide
  packaging/commit policy after modeled schema exists.
- **More sources:** pause further expansion after the explicitly approved Adi
  following snapshot. Revisit additional trusted-person following seeds only
  after the current evidence and resolution contract are consolidated.
- **One-time cleanup semantics:** Adi explicitly did not want the 2,000-follower
  floor encoded in the importer. Re-running `import-x-following` would restore
  the full 767-account snapshot and require repeating the cleanup. A later
  `channels sync` can also rematerialize the retained `@adithyan_ai` graph node
  as a provisional Registry channel; remove it again if that command is run.
- **Private cleanup:** before external sharing, strip or rewrite private
  context from `docs/references/context.md` and the build log.

## Execution Plan

1. **Registry:** candidate review table, identity evidence, first modeled
   people/labs schema.
2. **Ingestion:** productionize scheduled public-source pulls around the
   accepted registry.
3. **Extraction:** structured, cited insights tied to people/labs/documents.
4. **Scoring/validation:** defensible dimensions, validation set, precision
   or rank-quality checks.
5. **Delivery:** persona digest, alert path, final report, tokenomics.
6. **UI:** light browse/config/report surface after real modeled output exists.
7. **Submission cleanup:** remove private context, finalize reviewer guide,
   package exact artifacts, ask Adi before any external send.

## Proof Of Work

Update before each handoff when meaningful work lands.

- Latest commands: `fli sources import-x-following --username adithyan_ai
  --source adi_following`; focused source tests; SQLite invariant/overlap
  queries; `scripts/check-fast.sh`.
- Latest results: 2,966 visible clusters (10 lab, 0 person, 2,956 unknown), 2,998 owned
  channels, zero unowned channels, zero duplicate owners; 638 directed
  `adi_following` edges and facts; SQLite integrity is `ok`.
  Repository validation passes all 28 tests.
- Known limitations: no resolution agent, calibration/evaluation set, or
  track/reject decision exists yet. The current database still encodes
  `lab` / `person` / `unknown` pending the taxonomy decision. PageRank was not
  recomputed because Digg follower edges and trusted-person following edges
  need an explicit weighting policy. No external submission was performed.
- Submission package path:

## Progress Log

2026-07-10 — Bootstrap phase archived and classification work handed forward:

- Verified the final snapshot directly from SQLite and the live API: 2,967
  graph accounts, 2,966 visible entities, 2,998 channels/links, 12,664 source
  facts, 361,863 edges, 21,133 observations, and SQLite integrity `ok`.
- Froze the next classifier contract as `person` / `organization` / `unsure`,
  with model output limited to `classification` and `reason`.
- Moved remaining implementation into
  `docs/projects/entity-kind-classification/tasks.md` and archived this phase.

2026-07-09 — Initial source layering complete; pause ingestion and consolidate:

- Digg remains a frozen bootstrap: 1,000 ranked accounts, 2,314 distinct graph
  accounts after loading edge endpoints, and 361,225 edges.
- AI High Signal imported 609 X-list members through TwitterAPI.io.
- smol.ai imported 31 unique preferred people from pinned GitHub commit
  `0fc45e2c56e2b0cad71478bbee9cf5976c9e573e`; 23 matched existing accounts
  and eight were new.
- Current database: 2,608 accounts and 2,640 channels. The difference is the
  32 non-X lab channels (websites, GitHub, arXiv, blogs).
- The next agent should build a small read-only consolidation view and review
  the evidence groups with Adi before adding another source, LLM classifier,
  affiliation model, or broad registry schema.

2026-07-09 — Canonical entity spine and truthful Registry landed:

- Every observed channel now has exactly one owner. Ten seeded lab entities
  claim their 42 official channels; the remaining 2,598 X channels each have
  one provisional `unknown` entity.
- The Registry API/UI is one complete 2,608-entity universe with only name,
  `lab` / `person` / `unknown`, bio, and channels. Old Digg role/rank fields
  remain source evidence but are not canonical identity fields.
- Synchronization is hash-idempotent. Tests, lint, build, detector, live API,
  and browser interaction checks pass.
- Next: choose a stratified calibration sample with Adi, then write and
  evaluate the versioned kind-classification agent before full-dataset use.
