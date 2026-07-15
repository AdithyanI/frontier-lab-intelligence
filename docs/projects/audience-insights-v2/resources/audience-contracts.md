# Audience Insights v2 — Extraction, Editorial, and Evaluation Contracts

Status: implementation contract for M2–M4. This document turns the v2 product
decisions into exact model and application boundaries. It is intentionally
separate from the tracker: `../tasks.md` owns execution state; this resource
owns the contract that code, prompts, fixtures, and run stores must implement.

## Product decision

Investment and AI Engineering are two products over one frozen evidence core.
They do not share an extracted claim or a compromise output row. The same
evidence packet may produce:

- an Investment insight only;
- an AI Engineering insight only;
- two different insights, one for each audience;
- the same attributed claim with different audience analysis when that is
  genuinely the best decision-relevant claim for both; or
- no insight for either audience.

The audience extractors decide whether one packet contains one useful claim for
their reader. A later audience-specific editor chooses the best daily set. No
stage writes a numeric importance score.

The intended readers are:

- **Investment:** a public-equity PM or analyst deciding whether to change a
  thesis, watchpoint, diligence question, exposure map, or execution-risk view.
- **AI Engineering:** a senior hands-on AI engineer or technical lead deciding
  what to reproduce, benchmark, prototype, regression-test, investigate, or
  monitor.

## Shared frozen input

Both extractors consume the same immutable `EvidencePacket`. The packet is
rendered after the stable prompt prefix and contains no Feed score, engagement,
follower count, Registry prominence, or editorial rank.

```text
EvidencePacket
  event_id             runner-owned; never shown as a requested model field
  day                  UTC source day
  feed_rank            stored for provenance; omitted from model input
  evidence_sha256      hash of the complete rendered packet
  blocks[]
    block_index        one-based integer, unique inside the packet
    source_type        x_post | artifact
    source_id          runner-owned; not requested from the model
    source_url         runner-owned; not requested from the model
    source_author      optional
    source_title       optional
    relation           root | reply | quote | optional_strengthening | article_section
    source_sha256      immutable source-text hash
    section_ordinal    optional, for deterministically sectioned long artifacts
    source_char_start  optional, zero-based position in normalized source text
    source_char_end    optional, exclusive position in normalized source text
    verbatim_text      NFC-normalized frozen text
```

Every rendered block is explicitly delimited and numbered:

```text
<EVIDENCE_BLOCK index="3" type="ARTIFACT">
[author=... | title=... | role=article_section]
<VERBATIM_TEXT>
...
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>
```

When a long artifact must be sectioned, each section is a separate evidence
block with a runner-owned mapping back to the same artifact, content hash, and
character range. Sectioning is deterministic and source-hashed. An LLM summary
is never a citable evidence block.

## Shared epistemic contract

### Claim posture enum

Both extractor schemas use exactly one `claim_posture` value for an insight:

| Value | Meaning | Required claim behavior |
| --- | --- | --- |
| `directly_documented` | An official artifact directly documents a release, interface, policy, price, or event. | Limit the claim to what the document explicitly establishes. Documentation of a benchmark still does not independently prove broad performance. |
| `first_party_report` | A person or organization reports its own action, result, incident, evaluation, or observation. | Name the actor and use an attributed verb such as “announced,” “reported,” “observed,” or “acknowledged.” |
| `third_party_observation` | An outside researcher, practitioner, or observer reports a comparison or observation. | Name the observer and preserve the scope of their harness, sample, or experience. |
| `opinion_or_forecast` | The source argues, predicts, believes, or offers a thesis. | Name the speaker and preserve every hedge, modal, and temporal boundary. Never render the view as an established fact. |

`claim_posture` is an epistemic description, not a confidence score. It is
stored for auditing and need not become decorative UI metadata.

### Claim rules

Every insight claim must:

1. be one concrete, falsifiable or auditable sentence;
2. name the relevant actor, product, model, technique, evaluation, or event;
3. be directly supported by the one bound quotation;
4. preserve source authorship and uncertainty;
5. distinguish a source's report from independent verification; and
6. avoid inferred causality, revenue, market share, safety, benchmark
   superiority, production readiness, or general adoption unless the frozen
   evidence explicitly states it.

Replies and quoted posts keep their own authorship. A reply cannot become a
claim by the root author. Conflicting blocks remain separate attributed claims;
the extractor does not reconcile them into a stronger collective assertion.

### Analysis rules

Audience fields are analysis, not a second citation claim. They must remain
close to the supported claim and may not introduce a new factual premise.

For `first_party_report`, `third_party_observation`, and
`opinion_or_forecast`, the implication must be explicitly conditional with
language such as “if validated,” “if borne out,” “could,” or “would.” A direct
document can support less hedged description of the documented change, but its
market or production consequence remains analysis rather than fact.

## Exact citation binding

The model returns only `citation_block_index` and `supporting_quote`. It never
returns a source ID, URL, author identity, artifact ID, post ID, hash, or
citation object. A block index is a positional selector, not trusted
provenance; the runner owns the block-to-source mapping.

Application binding must execute in this order:

1. Assert that `citation_block_index` is an integer in the packet's one-based
   block range.
2. Preserve `supporting_quote` exactly as decoded from JSON. Do not trim,
   collapse whitespace, repair punctuation, decode entities, change case, add
   ellipses, or pass it through the generic prose cleaner.
3. Compare the quote with the selected block after NFC normalization of both.
   It must be one non-empty contiguous substring.
4. Require exactly one occurrence inside the selected block. If it occurs
   twice in that block, reject the result and require a longer disambiguating
   quote on a separately recorded attempt.
5. It is acceptable for the same phrase to occur in another block only because
   the explicit block selector disambiguates the source. Record the global
   matching-block count for audit.
6. Bind runner-owned source identity, URL, author, title, source hash, section
   ordinal, and exact character offsets from the selected block map.
7. Publish only a completed insight whose selected source URL and immutable
   source hash are present.

An absent selector, wrong selector, altered quotation, unmatched quotation,
or repeated quotation inside the selected block is a citation verification
failure, not `no_extractable_insight`. Preserve the model output and failure in
the run store; never render it.

## Investment extractor

### Versions and output fields

- Current prompt version: `investment-insight-v2.2` (v2.0 and v2.1 are
  preserved in the first Jul 11 calibration runs). V2.1 adds a final
  exact-block/Unicode citation
  audit plus attribution, literal-ticker, unsupported-association, and
  superseded-state checks after v2.0 repeated two deterministic quote failures
  and exposed permissive candidate analysis. V2.2 converts private-company
  announcements and generic public-equity watchpoints into honest no-insight
  outcomes unless the frozen evidence supports a concrete named exposure.
- Schema version: `investment-insight-output-v2`
- JSON schema name: `investment_cited_insight_v2`
- `strict: true`, every property required, `additionalProperties: false`

| Field | Exact type / enum | `insight` | `no_extractable_insight` |
| --- | --- | --- | --- |
| `outcome` | `insight \| no_extractable_insight` | `insight` | `no_extractable_insight` |
| `no_insight_reason` | `null \| no_audience_decision_value \| insufficiently_concrete \| missing_required_evidence \| ambiguous_attribution \| unsupported_inference_required` | `null` | one enum value |
| `claim` | `string \| null` | concise non-empty one-sentence claim | `null` |
| `claim_posture` | `null \| directly_documented \| first_party_report \| third_party_observation \| opinion_or_forecast` | one enum value | `null` |
| `why_it_matters` | `string \| null` | one or two concise sentences describing the competitive, product, economic, adoption, or execution change | `null` |
| `investment_implication` | `string \| null` | one or two concise conditional sentences tied to a public-equity decision | `null` |
| `what_to_watch` | `string \| null` | one concrete confirming or disconfirming watchpoint or diligence question | `null` |
| `supporting_quote` | `string \| null` | one exact contiguous quotation | `null` |
| `citation_block_index` | `integer \| null` | selected one-based evidence block | `null` |

The application validator enforces the column's nullability by outcome; JSON
Schema alone is not treated as sufficient conditional validation.

### Investment selection bar

Return `insight` only when the claim can plausibly change or sharpen at least
one of:

- provider differentiation or competitive position;
- adoption friction or evidence of adoption;
- inference, training, or infrastructure economics;
- product or distribution strategy;
- execution, compatibility, regulatory, or concentration risk;
- a concrete thesis or diligence question.

“Interesting AI news” is insufficient. `investment_implication` must connect
the supported development to a named investment question without presenting a
trade recommendation. `what_to_watch` must name observable evidence rather
than say only “monitor developments.”

### Company and ticker policy

V2 has no ticker-array field. This is deliberate: the current evidence packet
does not contain an authoritative public-company-to-ticker mapping, and model
generated tickers create false precision.

- Company names may appear when named in the frozen evidence or when the
  implication clearly concerns the named source organization.
- A ticker may appear in prose only if the exact ticker is present in frozen
  evidence or in an explicit runner-owned allowlist supplied with the packet.
- Never force a public-equity mapping for a private company, open-source
  project, technique, or broad theme.
- No buy/sell language, price target, portfolio sizing, certainty, or implied
  fiduciary recommendation.
- A future ticker feature must be deterministic enrichment from an audited
  company map; it is not added to this extractor opportunistically.

The evaluator marks a forced or unsupported ticker and any trade instruction as
an epistemic failure.

## AI Engineering extractor

### Versions and output fields

- Current prompt version: `ai-engineering-insight-v2.2` (v2.0 and v2.1 are
  preserved in calibration runs). V2.1 adds the same exact-block/Unicode
  citation audit, explicit strict-key preflight, attribution and unsupported
  association checks, bounded-action discipline, and superseded-state handling
  after v2.0 produced repeated strict-schema failures. V2.2 closes the final
  pre-holdout publication-audit gap: model names, generic metrics,
  "representative workloads," and a generic results-may-vary disclaimer do not
  create an actionable benchmark. A performance comparison or anecdotal
  failure must expose a concrete workload, task, prompt, artifact, interface,
  method, or repeatable failure condition that an external team can exercise.
- Schema version: `ai-engineering-insight-output-v2`
- JSON schema name: `ai_engineering_cited_insight_v2`
- `strict: true`, every property required, `additionalProperties: false`

| Field | Exact type / enum | `insight` | `no_extractable_insight` |
| --- | --- | --- | --- |
| `outcome` | `insight \| no_extractable_insight` | `insight` | `no_extractable_insight` |
| `no_insight_reason` | `null \| no_audience_decision_value \| insufficiently_concrete \| missing_required_evidence \| ambiguous_attribution \| unsupported_inference_required` | `null` | one enum value |
| `claim` | `string \| null` | concise non-empty one-sentence claim | `null` |
| `claim_posture` | `null \| directly_documented \| first_party_report \| third_party_observation \| opinion_or_forecast` | one enum value | `null` |
| `why_it_matters` | `string \| null` | one or two concise sentences describing the technical or operational change | `null` |
| `action_type` | `null \| investigate \| reproduce \| benchmark \| prototype \| regression_test \| monitor` | one enum value | `null` |
| `engineering_action` | `string \| null` | one concrete action naming the object, workload, comparison, or trigger | `null` |
| `validation_boundary` | `string \| null` | one concrete methodology caveat or condition that prevents over-generalization | `null` |
| `supporting_quote` | `string \| null` | one exact contiguous quotation | `null` |
| `citation_block_index` | `integer \| null` | selected one-based evidence block | `null` |

### Action enum

| Value | Use when |
| --- | --- |
| `investigate` | The next step is to inspect a paper, repository, design, failure mode, or disclosed method before testing. |
| `reproduce` | A reported result or behavior should be independently recreated under its stated conditions. |
| `benchmark` | A model, system, cost claim, or technique should be compared on a concrete evidence-exposed workload, task, method, interface, or baseline; “representative workloads” alone is not a test object. |
| `prototype` | A bounded implementation trial can test whether the capability or method fits a system. |
| `regression_test` | A release, incident, or compatibility change warrants a durable test around a named behavior. |
| `monitor` | No immediate experiment is justified, but a named release, metric, issue, or threshold would change an engineering decision. |

`adopt` and `integrate` are intentionally not enum values. One evidence packet
rarely establishes production readiness; a bounded `prototype` is the strongest
default action. `monitor` is valid only when `engineering_action` names exactly
what evidence or trigger to watch.

### Engineering selection bar

Return `insight` only when the claim can plausibly change or sharpen at least
one experiment, benchmark, implementation choice, compatibility test,
reliability check, tooling investigation, or named monitoring decision. Generic
advice such as “teams should evaluate this,” “engineers should monitor it,” or
“consider using the model” fails unless the action identifies the object,
method, comparison, and relevant boundary.

Model names plus “representative workloads” and generic latency, throughput,
quality, or cost measurements are still boilerplate. A one-off anecdotal
failure also fails unless the evidence supplies the prompt, artifact, named
failure mode, or repeatable conditions needed to turn it into a real test.

`validation_boundary` is required for every insight. For direct documentation
it can identify the workload, version, deployment context, or missing production
evidence that still needs checking; it must not invent a caveat absent from all
reasonable interpretation of the packet.

## `no_extractable_insight` behavior

An audience extractor can return no insight even though upstream triage kept
the envelope. This is not a second substance gate: it asks whether the supplied
evidence supports a decision-relevant claim for this specific audience.

The exact reason enum means:

| Value | Use only when |
| --- | --- |
| `no_audience_decision_value` | A concrete citable claim exists, but it cannot change or sharpen a decision for this audience without padding. |
| `insufficiently_concrete` | The supplied text is praise, banter, a vague teaser, or a non-falsifiable statement. |
| `missing_required_evidence` | The useful proposition depends on an unavailable article body, absent image/video, undisclosed table, or other missing source. |
| `ambiguous_attribution` | The packet does not permit the useful claim to be assigned safely to one source actor. |
| `unsupported_inference_required` | The only audience value would require an unstated market, causal, performance, safety, adoption, or implementation premise. |

Lack of independent confirmation, an external artifact, a numerical result, or
a URL is not by itself a reason to return no insight. Authored first-party X
text can support a carefully attributed claim about the author's own work,
release, result, incident, or view.

Deduplication is never a no-insight reason. Extract candidates independently;
the daily editor owns redundancy.

## Daily audience editor

### Boundary

There is one editor run per audience and UTC day. Every completed, schema-valid,
uniquely citation-bound `insight` candidate is first reviewed independently.
The editor receives only candidates passing all five item-review dimensions:
citation fidelity, attribution, audience usefulness, actionability, and
specificity. It receives no reviewer scores or rationales, so review cannot
coach or leak into selection. It can select, order, and identify duplicates.
It cannot rewrite any claim, analysis field, action, quote, citation, source
metadata, or factual content.

The runner materializes display rows by joining returned IDs back to frozen
candidate rows. The editor's array order becomes audience editorial rank `#1`
through `#5`. Feed rank is joined later as secondary provenance and is absent
from editor input.

### Input contract

```text
AudienceEditorInput
  audience              investment | ai_engineering
  day                   UTC day
  target_min            3
  target_max            5
  candidates[]          canonical order by candidate_id, never Feed rank
    candidate_id        opaque runner-owned current-day ID
    claim
    claim_posture
    why_it_matters
    audience_fields     investment_implication + what_to_watch
                        OR action_type + engineering_action + validation_boundary
    source_type
    source_author
    source_title
  prior_selected[]      all earlier selected items in the same frozen nine-day run
    selected_item_id    opaque runner-owned prior ID
    day
    claim
    audience_fields
    source_author
    source_title
  candidate_set_sha256
  history_sha256
```

Editor inputs omit exact quotes because citation validity is already mechanical,
omit item-review scores and rationales because the review is a publication
filter rather than editorial coaching, and omit Feed rank, score, engagement,
followers, and Registry support so those signals cannot substitute for audience
judgment.

### Versions and output schema

- Investment prompt: `investment-daily-editor-v2.1`
- AI Engineering prompt: `ai-engineering-daily-editor-v2.4`
- Shared structural schema: `audience-daily-editor-output-v2`
- `strict: true`, every property required, `additionalProperties: false`

```text
selected: array[0..5] of
  candidate_id: string
  decision_value: audience enum
  audit_reason: non-empty string
  updates_prior_id: string | null

suppressed_duplicates: array of
  candidate_id: string
  duplicate_of_id: string
  duplicate_scope: same_day | cross_day
  audit_reason: non-empty string

thin_day_reason: string | null
```

Investment `decision_value` enum:

- `thesis_or_model`
- `watchlist_or_exposure`
- `diligence_question`
- `execution_or_competitive_risk`

AI Engineering `decision_value` enum:

- `experiment_or_benchmark`
- `implementation_choice`
- `regression_or_reliability`
- `research_or_tooling_watch`

Application validation requires:

1. every selected ID exists in current-day `candidates` and appears once;
2. array order is the complete editorial order;
3. zero to five items are permitted; never pad to reach three;
4. `thin_day_reason` is non-empty when fewer than three are selected and is
   `null` otherwise;
5. `updates_prior_id` is either `null` or a valid ID in `prior_selected`;
6. every suppressed ID is a current candidate not selected elsewhere;
7. a `same_day` duplicate points to another current candidate, while a
   `cross_day` duplicate points to `prior_selected`;
8. an ID cannot occur in both `selected` and `suppressed_duplicates`; and
9. audit reasons describe editorial value or redundancy only and are stored as
   audit metadata, not rendered as new source facts.

Candidates that are neither selected nor explicitly marked as duplicates are
ordinary lower-priority candidates; the editor does not need to manufacture a
reason for every non-selection.

## Same-day and cross-day deduplication

Two items are the same story when they assert the same underlying development,
release, result, incident, strategy change, or expert thesis, even if different
people link to it or phrase it differently.

### Same day

Select at most one item per underlying story. Prefer the candidate whose claim
is most precise, whose audience action is most concrete, and whose source is
closest to the event. Put other current candidates in
`suppressed_duplicates`, pointing at the preferred candidate ID. Do not merge
their claims or citations.

### Across days

Days are edited chronologically. A repeated story is suppressed unless the new
candidate adds a material development that could change the audience decision.
A material update is one of:

- a new version, release, capability, policy, or price;
- a new measured result or disclosed methodology;
- a correction, regression, outage, or changed limitation;
- new adoption, commercial, regulatory, or execution evidence; or
- a changed forecast or thesis from the responsible actor.

A different commentator repeating the same fact, a new paraphrase, more
engagement, a recap, or an unchanged opinion is not a material update.

When selected as a material update, set `updates_prior_id` to the relevant prior
selected ID and explain the new decision value in `audit_reason`. When it adds
no material information, suppress it with `duplicate_scope=cross_day`.
Cross-audience overlap is allowed and is never deduplicated: the two products
have independent readers and histories.

The editor run identity includes `candidate_set_sha256` and `history_sha256`, so
changing an earlier selected set creates a new immutable downstream run rather
than silently rewriting later days.

## Automated quality evaluation

### Deterministic checks

Application code, not a review model, checks:

- exact schema and outcome-dependent null behavior;
- model/prompt/schema/run identity;
- candidate and history hashes;
- quote preservation and unique selected-block binding;
- citation URL, source hash, and character offsets;
- editor ID membership, uniqueness, count, and reference integrity;
- complete/pending/failed/selected reconciliation; and
- token, cache, response, error, retry, and proxy-cost telemetry.

Any deterministic failure makes the item or day ineligible for publication.

### Independent item reviewer

An isolated Luna-high reviewer receives the frozen evidence, extracted item,
audience, and rubric, but not the extractor's hidden reasoning, Feed rank,
editor order, or editor audit reason. The active contract is
`audience-insight-item-review-v2.4`; v2.0, v2.1, v2.2, and v2.3 are preserved in immutable calibration
runs. V2.1 adds a mechanical attribution sentence check and an analysis
proper-noun/relationship scan after v2.0 failed to catch first-party benchmark
upgrades and a funding-participation-to-integration inference that the blinded
publication audit correctly rejected. Its strict output is:

```text
candidate_id: string
claim_fidelity: pass | fail
epistemic_discipline: pass | fail
audience_usefulness: pass | fail
actionability: pass | fail
specificity: pass | fail
failure_codes: array of
  unsupported_claim |
  wrong_attribution |
  attribution_upgrade |
  modal_or_scope_loss |
  unsupported_analysis_fact |
  forced_ticker_or_trade |
  generic_investment_implication |
  generic_engineering_action |
  missing_validation_boundary |
  audience_mismatch |
  not_decision_relevant |
  vague_or_promotional |
  other
rationale: non-empty string
```

The definitions are binary:

- **Claim fidelity:** the claim follows from the selected quote and its source
  block without adding a material fact.
- **Epistemic discipline:** authorship, uncertainty, comparison scope, and
  first-party status are preserved; analysis does not masquerade as evidence.
- **Audience usefulness:** the item could plausibly change or sharpen one of
  the intended reader decisions defined above, rather than merely inform.
- **Actionability:** Investment names a concrete implication and watchpoint;
  Engineering names an executable action and validation boundary.
- **Specificity:** actor, object, and change are concrete; fields are not
  interchangeable boilerplate.

The posture enum and `source_author` metadata never substitute for attribution
inside the claim sentence. Funding participation proves participation only;
without additional evidence it does not prove strategic alignment,
partnership, integration, demand, adoption, revenue, or infrastructure usage.

### Independent day-set reviewer

The reviewer also receives the complete selected set plus unselected candidate
claims and prior selected history. Its strict output is:

```text
duplicate_pairs: array of
  left_id: string
  right_id: string
  scope: same_day | cross_day
  rationale: string
padding_detected: boolean
thin_day_honest: boolean
set_rationale: non-empty string
```

`padding_detected` means an item was selected mainly to reach a count rather
than because it meets the audience bar. `thin_day_honest` is true when fewer
than three were selected only because no additional candidate met that bar.

### Calibration and holdout expansion gate

Each audience declares its own frozen evaluation days, holdout day, and gate
policy. This is intentional: the two products may need different evidence
windows, but neither may relabel a holdout after inspecting it. Every audience
day passes only when:

1. all selected items pass deterministic schema and citation checks;
2. all selected items pass `claim_fidelity` and `epistemic_discipline`;
3. at least `ceil(0.80 * selected_count)` items pass all three of
   `audience_usefulness`, `actionability`, and `specificity`;
4. if fewer than three items are selected, every selected item passes those
   three fields and the day-set reviewer says `thin_day_honest=true`;
5. `duplicate_pairs` is empty and `padding_detected=false`;
6. all editor outputs pass ID/reference validation; and
7. no unhandled run item remains pending or failed.

The `standard` policy additionally requires at least three selected items,
selections on at least two days, and at least one holdout selection. This
prevents mechanically valid empty days from becoming a vacuous quality proof
while still allowing honestly thin individual days.

The separately named `audited_sparse` policy is available only when the
standard gate fails on yield while every quality, audit, binding, and contract
check passes. It requires at least five frozen days, at least one selected item,
at least one selected day, an explicitly honest zero-item holdout with a full
five-reject adjacent audit, uniform contracts, and zero unresolved or
`would_enter` false negatives. Every zero day must pass the explicit
thin-day/no-padding check. An all-zero window, shorter window, contract drift,
stale audit, failed selected item, or incomplete reject audit still fails.
Reports expose `audited_sparse` rather than calling this a standard pass.

The oracle does not require exact agreement with the handwritten preferred
claim: the v1 run already showed defensible alternate selections. It requires
safe, cited, audience-useful alternatives. Failure triggers diagnosis and a
new immutable prompt version, not broad expansion. Compare at most three prompt
versions and freeze the first one that passes; if several pass, prefer the one
with the highest count of selected items passing all reviewer fields, then the
lower no-insight false-miss count, then lower unsupported-inference count.

### Candidate-width escalation

Top 50 is an execution start, not a quality assumption. For each gate day and
audience, evaluate a fixed stratified sample from kept ranks 51–75 and 76–100
without revealing rank to the extractor or reviewer. Widen that day to 75, then
100, when either:

- a lower-band candidate passes every item rubric field and the daily set has
  fewer than five items; or
- the editor selects a lower-band candidate ahead of the current fifth item in
  a comparison run.

Retain both cohort hashes and comparison results. Do not widen because a lower
item is famous, highly followed, or highly engaged.

## Adversarial fixture suite

These cases must be represented in tests or a frozen calibration resource:

| Case | Required result |
| --- | --- |
| First-party benchmark says “we found”; output says the model definitively wins. | Reviewer fails claim fidelity/epistemics for attribution upgrade. |
| Observer says a model “seems” Pareto-efficient; output says it “is.” | Fail `modal_or_scope_loss`. |
| Exact phrase occurs in two blocks and model selects the correct block. | Bind selected block, record global match count, accept if unique inside that block. |
| Exact phrase occurs twice inside the selected block. | Mechanical citation failure; require a longer quote. |
| Model fixes capitalization, punctuation, spelling, whitespace, or adds ellipses. | Mechanical citation failure. |
| Useful claim exists only in an unfetched X Article body or absent image. | `no_extractable_insight` with `missing_required_evidence`; preview metadata cannot support it. |
| First-party X post contains a concrete release but no external artifact. | Eligible attributed claim; absence of external validation is not a miss. |
| Reply evidence is attributed to the root author. | Fail `wrong_attribution`. |
| Two blocks conflict and output silently resolves them as consensus. | Fail `unsupported_claim`; select one attributed proposition or no insight. |
| Investment output forces a ticker, trade, or price target. | Fail `forced_ticker_or_trade`. |
| Investment output says only “this could be important; monitor adoption.” | Fail actionability and specificity. |
| Engineering output says only “teams should test/monitor this.” | Fail `generic_engineering_action`. |
| Engineering recommends adoption from one provider-authored result. | Fail epistemics/actionability; a bounded prototype or benchmark is the maximum. |
| Method-specific result omits its workload/sample boundary. | Fail `missing_validation_boundary` or `modal_or_scope_loss`. |
| Two current-day sources report the same release. | Select one, suppress the other as `same_day`. |
| Next day repeats the same release with no new fact. | Suppress as `cross_day`. |
| Next day reports a concrete regression or new measured result for that release. | May select with `updates_prior_id` referencing the earlier item. |
| Vague praise, meme, or unexplained link survives permissive triage. | Audience no-insight with `insufficiently_concrete`. |
| Concrete technical claim has no investment decision value. | Investment may return `no_audience_decision_value` while Engineering emits an insight. |
| Concrete strategy claim has no engineering decision value. | Engineering may return `no_audience_decision_value` while Investment emits an insight. |
| Same claim is independently useful to both audiences. | Both may emit it with separate audience fields; no cross-audience suppression. |

## Model routing, caching, and run identity

### Routing

| Job | Model | Reasoning | Rule |
| --- | --- | --- | --- |
| Investment extraction | `gpt-5.6-luna` | `medium` | Proven bounded extraction baseline. |
| AI Engineering extraction | `gpt-5.6-luna` | `medium` | Same evidence complexity, independent prompt. |
| Investment daily editor | `gpt-5.6-luna` | `high` | Low-volume comparative selection and deduplication. |
| AI Engineering daily editor | `gpt-5.6-luna` | `high` | Low-volume comparative selection and deduplication. |
| Independent item/day evaluator | `gpt-5.6-luna` | `high` | Separate rubric pass; no web search required. |

Transient provider failures may retry without changing run identity. A schema,
citation, or quality failure is preserved and analyzed; it is not silently
replaced by a higher-effort result. Luna-high extraction is allowed only as a
separately identified calibration experiment when medium shows a recorded
systematic miss. Terra remains reserved for the separate web-grounded relevance
boundary and is not needed for these frozen evidence contracts.

### Prompt-cache namespaces

Use `fli.llm_responses.sharded_prompt_cache_key` with these exact `namespace`
values and the prompt versions above:

| Job | Namespace | Shards | Concurrency |
| --- | --- | ---: | --- |
| Investment extraction | `audience-insights-v2-investment-extraction` | 32 | at most one in-flight request per lane |
| Engineering extraction | `audience-insights-v2-engineering-extraction` | 32 | at most one in-flight request per lane |
| Investment editor | `audience-insights-v2-investment-editor` | 1 | chronological, one request at a time |
| Engineering editor | `audience-insights-v2-engineering-editor` | 1 | chronological, one request at a time |
| Investment evaluation | `audience-insights-v2-investment-evaluation` | 4 | at most one in-flight request per lane |
| Engineering evaluation | `audience-insights-v2-engineering-evaluation` | 4 | at most one in-flight request per lane |

Stable instructions, rubric, schema guidance, and examples precede variable
evidence. Provider cache kwargs come only from
`fli.llm_responses.litellm_prompt_cache_kwargs(model)`. Cache eligibility is not
a cache hit; record input, cached, cache-write, and output tokens per request.

### Tags and identity

Every request includes stable LiteLLM metadata tags:

```text
app:frontier-lab-intelligence
pipeline:audience-insights
audience:investment | audience:ai-engineering
job:insight-extraction | job:daily-editor | job:quality-evaluation
scope:day-YYYY-MM-DD
prompt:<version>
run:<run_id>
```

Each immutable run identity includes audience, job, day/range, model, reasoning
effort, prompt version and SHA, schema version, source triage DB, artifact
snapshot/hash, cohort/candidate/history hashes, and creation time. Changing any
of these creates a new run; historical rows are never relabeled or overwritten.

## Minimum implementation acceptance

Before broad model calls, code and fixtures must prove:

1. the two schemas reject cross-audience fields and enforce exact null behavior;
2. the quote bypasses generic whitespace cleaning and binds to the selected
   block plus exact runner-owned provenance;
3. a model block index cannot spoof source IDs or URLs;
4. editor output can only select existing verified IDs and cannot mutate rows;
5. chronological history changes the editor run hash;
6. the adversarial citation, attribution, ticker, action, and dedup cases fail
   or pass as specified;
7. both audience prompts run against the five-record oracle and blind sample;
8. the Luna-high reviewer and deterministic gate produce reproducible reports;
9. prompt-cache lanes and telemetry are visible in run summaries; and
10. the API/UI read only complete selected rows with verified citations.
