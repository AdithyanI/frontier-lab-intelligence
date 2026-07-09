# Frontier Lab Intelligence — Tracker

Active execution state for the BIT Capital case-study product.

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

## Current Batch

**Resume here.** The source-import batch is complete. Do not import another
list or design a larger classification system yet. First consolidate the
current evidence into a reviewable candidate view and inspect it with Adi.

| Status | Work item | Evidence / notes |
| --- | --- | --- |
| done | Freeze the initial evidence layer. | Digg graph + PageRank, AI High Signal list, and smol.ai `prefPeople` are in `data/fli.db` with source facts and pinned provenance. |
| todo | Build the smallest consolidation view over existing accounts. | Group candidates by source agreement and expose handle, bio, follower count, Digg rank, PageRank, AI High Signal membership, and smol.ai membership. Start with read-only output; do not add a large registry schema first. It must include the 294 curated-only accounts currently omitted from `/api/registry`. |
| todo | Review the consolidation with Adi and agree on the first decision rule. | Begin with the 17 accounts present in Digg + AI High Signal + smol.ai, then inspect the 4 in both curated lists and the 10 smol-only accounts. Likely output is simply `track` or `reject`, but this is not decided yet. |
| later | Add person/org classification, optional person-to-lab affiliation, and durable registry decisions after the review. | People may belong to labs, but affiliation is optional and should not block independent researchers. |

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
- **Current DB:** 2,608 X accounts, 2,640 channels, 12,026 account source facts,
  361,225 graph edges, 17,656 channel observations, 10 lab entities, and 42
  entity-channel links.
- **Model distinction:** `accounts` is the legacy X-specific graph table.
  `channels` is the canonical cross-source location model: 2,608 X channels
  plus 10 websites, 9 GitHub channels, 8 arXiv channels, and 5 blogs. Each X
  account is currently mirrored one-to-one into an X channel.
- **Source semantics:** list membership is evidence only. It must not
  automatically create a tracked person or imply quality. Preserve provenance
  in `account_source_facts` / `channel_observations`.
- **Paid provider:** TwitterAPI.io imported the AI High Signal X list using the
  machine-local key at `~/.secrets/twitterapi-io/api-key`; Adi added about $10
  credit. The smol.ai import used public GitHub and cost nothing.
- **Durable detail:** read `docs/architecture/overview.md` for schema and
  `docs/references/research-notes.md` for source provenance before changing
  ingestion or classification.

### Exact Source Partition

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

### Decisions Already Made

- Keep the first version simple. Merge evidence before classification; do not
  create many status labels, roles, or confidence tiers just because the schema
  can support them.
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
- `/api/registry` returns 10 seeded lab entities plus 2,305 people candidates
  selected only when they have Digg rank or PageRank. Those rows are honestly
  candidates, not promoted/tracked person entities.
- The UI currently calls that combined surface “Registry” and its copy says
  “Every entity the system tracks,” even though people are still candidates.
  Treat this as known provisional copy/model debt; consolidation should make
  the distinction truthful rather than silently promoting everyone.
- The major current visibility gap is that `/api/registry` does not expose
  curated-list membership and omits the 294 accounts added by the curated
  imports because they have neither Digg rank nor PageRank.
- Of 2,608 accounts, 1,333 currently have a non-empty bio and 2,600 have a
  follower count. The eight new smol-only account rows have handles and source
  provenance but no fetched profile metadata yet.

### Next-Step Acceptance Check

Before any automatic curation or schema migration, produce a read-only
consolidation that:

1. Covers all 2,608 X accounts, including curated-only and graph-only rows.
2. Shows explicit booleans/values for Digg, PageRank, AI High Signal, and
   smol.ai rather than collapsing them into one opaque score.
3. Makes the seven source groups above filterable or at least countable.
4. Preserves missing data honestly; do not infer missing bios, roles, or lab
   affiliations.
5. Reproduces these invariants: Digg 1,000; AI High Signal 609; smol.ai 31;
   curated-only new rows 294; all-three 17; total accounts/X channels 2,608.
6. Is inspected with Adi before adding `track`/`reject`, an LLM classifier,
   person entities, affiliation tables, or another source.

## Open Questions / Blockers

- **First decision rule:** deliberately undecided until the consolidation view
  is inspected with Adi. Do not assume source count alone equals importance.
- **DB schema:** the final people/affiliation/decision schema remains unlocked
  until candidate evidence is reviewed.
- **Legacy migration:** `accounts` and `account_source_facts` still back graph
  code while `channels` and `channel_observations` are the product model. Do
  not delete the legacy layer until graph consumers have migrated.
- **Database artifact policy:** prompt asks for schema + real data; decide
  packaging/commit policy after modeled schema exists.
- **More sources:** pause source expansion. Revisit Anthropic staff or X
  following data only after the current evidence has been consolidated.
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

- Latest commands: AI High Signal X-list import via TwitterAPI.io; pinned
  smol.ai `prefPeople` import from public GitHub; SQLite integrity/parity
  queries; `scripts/check-fast.sh`.
- Latest results: 2,608 X accounts mirror exactly to 2,608 X channels;
  `PRAGMA integrity_check` is `ok`; 31 smol.ai facts are stored; all 19 tests
  pass. The local app remains at `http://127.0.0.1:8797/`.
- Known limitations: no candidate consolidation or track/reject decision exists
  yet. Public browser access requires Cloudflare Access login; no external
  submission was performed.
- Submission package path:

## Progress Log

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
