# Architecture Overview

Frontier Lab Intelligence turns public frontier-AI activity into inspectable
evidence and two audience-specific intelligence views. The system deliberately
separates deterministic evidence construction from model judgment: agents can
rebuild and audit the evidence before asking a model what it means.

Use the [code and data map](code-map.md) to locate an owner, command, store, or
test. Exact schemas, run telemetry, and historical implementation facts live in
[implementation contracts](../references/implementation-contracts.md) and the
other documents under `docs/references/`.

## System Shape

```mermaid
flowchart TD
    R["Registry<br/>entities and channels"] --> C["Collection<br/>immutable provider evidence"]
    R --> N["Trusted network<br/>frozen following snapshots"]
    C --> F["Feed<br/>complete daily evidence"]
    F --> E["Events<br/>exact structural groups"]
    E --> A["Artifacts<br/>first-party source extraction"]
    N --> S["Attention<br/>transparent ordering"]
    R --> S
    E --> S
    E --> Q["Audience routing<br/>AI Engineering and Investment"]
    A --> Q
    S --> Q
    Q --> I["Daily editorial agent<br/>ranked, cited Insights per audience"]
    I --> W["Web and CLI<br/>inspection and operation"]
    E --> W
    A --> W
    N --> W
```

The dependency direction is downward. Raw and deterministic stages never
depend on a downstream model decision. Rebuilding a later stage cannot mutate
or reinterpret its upstream evidence.

## Main Parts

| Area | Package | Responsibility |
| --- | --- | --- |
| Registry | `fli.registry` | Canonical people, organizations, channels, provenance, admission, and curation. |
| Ingestion | `fli.ingestion` | Public-source adapters, raw X storage, and date-complete collection. |
| Trusted network | `fli.network` | Frozen outgoing-follow evidence and derived entity-support rankings. |
| Evidence | `fli.evidence` | Deterministic Feed snapshots, exact structural Events, and one refresh workflow. |
| Artifacts | `fli.evidence.artifacts` | Canonical source links, lineage, retrieval, and extracted text. |
| Attention | `fli.scoring` | Versioned, inspectable ordering formulas and offline evaluation. |
| Audience routing | `fli.routing` | Independent AI Engineering and Investment relevance decisions with durable runs. |
| Insights | `fli.insights` | Per-Event working annotations plus agent-authored daily synthesis, strict validation, atomic storage, and the canonical read model. |
| Product adapters | `fli.web`, `fli.cli` | HTTP/UI composition and non-interactive commands; no domain truth belongs here. |

Cross-domain provider behavior belongs in `fli.llm_responses`; compact tracked
product state belongs in `fli.store`. Those are the only shared runtime modules
at the root of `fli`.

## Main Flow

1. The Registry defines the tracked identities and their source channels.
2. Collection stores immutable provider responses and normalized observations.
3. Feed materialization selects complete UTC days and preserves exact relation
   and discovery history.
4. Events group only provider-declared structural relationships. They do not
   perform topic clustering.
5. Artifact enrichment admits source links only from the root author and that
   author's same-conversation continuation.
6. Attention provides a transparent daily ordering aid. It is not an Insight
   or a quality judgment.
7. Audience routing independently decides whether the packet matters to AI
   Engineering and Investment. New routing freezes admit only first-party X
   sources no more than seven days old; a current same-author continuation may
   replace an older root, while old-only packets are excluded. A multi-day
   refresh freezes every requested date against one global Event publication,
   then routes days in parallel. New publication-qualified runs automatically
   reuse a predecessor judgment only when the same Event has exact frozen
   evidence and rendered model input under the same routing contract; changed
   or newly ranked Events alone require model work.
8. A daily editorial agent reviews the complete routed-positive cohort, reads
   the skill-owned BIT thesis, audited 2025 portfolio, and source-graded company
   profiles for Investment. It loads a compact profile index once and retrieves
   only matching profiles by canonical name, ticker, or alias. It may use
   per-Event notes as annotations, researches missing transmission paths, and
   writes the ranked cited Insights that clear the audience bar. Each selected
   Insight stores the qualitative rationale for its audience-local priority;
   the rank is not a synthetic score. Every
   candidate is linked once to an Insight or explicitly not selected. Its
   workspace applies the same seven-day X-source projection defensively to
   existing routing runs, attaches application-owned publication times, and
   projects exact catalogued artifact disclosure lineage without automatically
   pruning artifacts.
9. Deterministic validation binds the draft to its frozen workspace and imports
   Insights, Event roles, dispositions, and citations in one transaction.
   Artifact citations require an excerpt verified against the frozen artifact
   text; the agent still owns the semantic judgment that the passage supports
   the Insight.
   Optional embedding retrieval may find paraphrases but never decides a merge.
   Investment Insights persist one causal interpretation, company read-through,
   key uncertainty, watchpoints, and a diligence step; intermediate reasoning
   scaffolds are not separate reader fields.
10. The date-keyed daily runner checkpoints the existing Evidence, routing,
   and strict-v3 workspace stages, then may hand the exact workspace to one
   named Codex task. Model and reasoning may inherit Codex configuration, but
   service speed defaults to an explicit Standard override (`serviceTier:
   null`) so a user-level Fast preference cannot leak into an unattended run.
   It records the effective model, reasoning effort, and service tier returned
   by App Server and validates that frozen tuple before any resume work. A
   complete imported editorial run is terminal product proof: retries close
   from that durable row before opening App Server, so a task later reused by a
   human is outside orchestration control.
11. The web and CLI expose the frozen evidence, decisions, provenance, and
   operational status without becoming alternate data owners. For a complete
   daily editorial run, the web adapter can deterministically render the same
   audience/date projection as a linked A4 PDF. The content-addressed derived
   cache is an acceleration layer, not another report or editorial store.

## Important Boundaries

- **Immutable inputs:** paid or irreproducible provider responses are cached
  under `data/raw/`; normalized and derived stores can be rebuilt from them.
- **Current versus historical state:** current readers use only canonical paths
  documented in the code map. Historical run identity remains in manifests,
  prompt/schema versions, hashes, and archived project records.
- **Parallel historical authoring:** publish Feed and Events once through the
  maximum requested date, route the complete date range against that one
  snapshot, then fan out immutable per-day workspaces and Codex tasks. Several
  full `run-day` Evidence publishers must not compete for the global pointer.
- **Exact Event identity:** quote, retweet, reply-parent, and first-party thread
  relationships may group evidence; shared topic or conversation text may not.
- **Dynamic curation:** Feed and Event readers overlay current Registry state so
  rejected identities disappear without rewriting raw history.
- **First-party model evidence:** independent reactions remain auditable in the
  Feed but cannot silently become primary artifact or Insight evidence.
- **Fresh semantic evidence:** raw Events retain their history, while routing
  and daily authoring use only first-party X posts from the brief day through
  seven days earlier. Current same-author continuations may replace old roots;
  third-party reactions may not rescue them.
- **Artifact availability versus support:** the artifact catalog owns exact
  disclosure lineage, and the workspace exposes it without a second automatic
  artifact gate. The daily agent audits timing and relevance, then grounds any
  citation in a verified passage relevant to the Insight claim.
- **Independent audiences:** Engineering and Investment are separate judgments
  over one shared evidence core, not two ingestion systems.
- **Derived delivery cache:** a PDF cache key binds the report renderer version,
  canonical read schema, selected day and audience, and imported result hash.
  Cache files are atomically replaceable and may be deleted without losing
  editorial truth; the normalized run remains the only report input.
- **Agent freedom behind a narrow write boundary:** the agent may search,
  compare, group, and research freely, but only a versioned Insight schema and
  complete candidate disposition may enter product state.
- **Versioned model contracts:** active prompts use stable semantic filenames;
  immutable runs store prompt version, schema version, and prompt/input hashes.
- **Shared model adapter:** every LLM call goes through the LiteLLM Responses
  boundary with stable metadata, measured cache telemetry, and captured cost.
- **No compatibility maze:** migrations use direct imports and canonical data
  paths. Old module aliases and dual reads are not retained by default.
- **Artifact targets remain document-shaped:** exact generic `/search`
  navigation endpoints are excluded both when first observed and when reached
  through redirects, so changing listing content cannot enter semantic packets.
- **External action remains explicit:** publishing, alerts, uploads, and case
  submission require current-session human approval.

## Agent Change Rule

Start at the owning package and its mirrored tests. Update this overview only
when the system shape or dependency direction changes. Update the relevant
reference when an exact contract, schema, cache rule, command, or store changes.
Routine work is tracker-free. Use a project tracker only when Adi explicitly
invokes `$project` for work that needs a durable multi-session plan.

Validation is one command:

```bash
bash scripts/check-fast.sh
```

It validates the docs/build log, compiles and tests Python, audits live artifact
lineage when local data exists, runs frontend contract tests and lint, and
builds the production SPA.

## Exact References

- [Code and data ownership](code-map.md)
- [Current system status](../STATUS.md)
- [Implemented contracts and historical proof](../references/implementation-contracts.md)
- [Local data lifecycle](../references/data-lifecycle.md)
- [Feed and Event contract](../references/signal-feed.md)
- [Evidence refresh workflow](../references/evidence-refresh.md)
- [Artifact library contract](../references/artifact-library.md)
- [Model routing and cache policy](../references/model-routing.md)
- [Insight refresh/client](../references/insight-refresh.md)
- [Daily agent/editorial contract](../references/daily-intelligence.md)
