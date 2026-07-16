# Insight Persona Calibration

Last verified: 2026-07-16

## Purpose

This calibration asks whether the final audience editors turn the same
first-party Evidence packet into genuinely different, useful last-mile output
for BIT Capital's Investment and AI Engineering readers. It is a bounded
quality check, not approval to generate the full routed backlog.

The assignment sets the governing bar: surface intelligence that BIT would
genuinely want to know, keep noise out, tailor one shared evidence core to two
audiences, keep every Insight traceable to primary evidence, and make the
output actionable enough that the reader knows what it means and what to do.
It also explicitly treats a star researcher leaving a lab to found a startup
as a possible Investment signal before a product or stock-price effect exists.

Public BIT material adds useful specificity without inventing private
knowledge:

- BIT describes a bottom-up, high-conviction technology-equity process that
  combines proprietary data and AI with final human judgment:
  <https://bitcap.com/en/investmentansatz>.
- Its public Investment role emphasizes original theses, concentrated
  portfolios, buy/sell responsibility, alternative data, and AI-supported
  research: <https://bitcap.jobs.personio.com/job/2591464>.
- Its AI Engineer role describes production LLM extraction pipelines,
  financial-intelligence agents, evals, data and tool integrations, and
  end-to-end ownership in a small team:
  <https://bitcap.jobs.personio.com/job/2685548?language=en>.

The prompt structure also follows OpenAI's reasoning-model guidance: give a
clear goal and constraints, delimit the evidence, avoid asking for hidden
reasoning, and start zero-shot before adding examples:
<https://developers.openai.com/api/docs/guides/reasoning-best-practices#how-to-prompt-reasoning-models-effectively>.

## Prompt hill climb

1. The initial production prompts proved the shared schema and strict final
   surface-or-suppress gate, but the Investment editor suppressed the Richard
   Sutton / Oak Lab formation signal because no product, funding, or benchmark
   was disclosed.
2. Investment v5 encoded the assignment-critical organizational-move rule. A
   tracked frontier researcher leaving, joining, or founding a specific AI
   organization can clear the gate as a competitive-map or talent-formation
   watchpoint without disclosed commercialization.
3. Investment v6 and AI Engineering v5 added distinct reader and voice
   contracts. Investment now writes a sharp internal bottom-up research note
   about thesis pressure, competitive structure, exposure, and observable
   validation. Engineering writes a precise internal production review about
   mechanism, evidence boundaries, architecture or evaluation consequences,
   and a reproducible next step. Neither prompt claims knowledge of BIT's
   holdings, valuation work, or exact internal stack.
4. AI Engineering v6 preserved the strict final gate while correcting two
   bounded editorial failures. A specialized source artifact may support a
   transferable engineering pattern without making reproduction of that
   specialized project the team's assignment; the next step now applies the
   pattern to a representative BIT workflow. A concrete attributed capability
   observation or architectural thesis may also clear the gate before a formal
   benchmark when it challenges a named build assumption and supports a
   bounded team-relevant investigation. Generic inspiration and unspecified
   comparisons remain suppressions.

No few-shot examples were added. The zero-shot instructions produced the
desired separation, so examples would currently add length and anchoring risk
without evidence of a remaining systematic failure.

## First bounded evaluation

The fixed review set contains six routed Events across 2026-07-12 and
2026-07-13. Terra/high produced ten audience decisions: five surfaced and five
suppressed. The calls used 29,216 input tokens and 4,622 output tokens, read
8,960 cached prefix tokens, and recorded $0.122210 in proxy-reported cost. All
five cache hits belonged to the Investment prefix; the four Engineering calls
were eligible but reported zero reads, so cache behavior is recorded rather
than inferred.

### Surfaced

| Audience | Feed item | Title | Qualitative judgment |
| --- | --- | --- | --- |
| Engineering | Jul 12 #3 | Treat agent exhaust as a portability boundary | Strong. Converts Nadella's customer-owned learning thesis into an inspectable model-swap and data-boundary exercise without pretending an implementation was disclosed. |
| Investment | Jul 12 #3 | Nadella frames enterprise AI around customer-owned learning | Strong and distinct from Engineering. Identifies procurement, data-rights, and model-portability consequences, then names terms and deployment evidence to compare. |
| Engineering | Jul 12 #6 | Treat time horizons as scaffold-specific capability signals | Strong. Preserves METR's measurement limits and turns the result into a versioned internal eval with a representative workload, reliability threshold, latency, cost, and failure modes. |
| Investment | Jul 12 #6 | METR trend challenges gradual AI product roadmaps | Defensible. Connects the reported curve to roadmap and workflow exposure while explicitly rejecting broad labor-substitution or production-readiness claims. |
| Investment | Jul 13 #2 | Sutton and Javed form Oak Lab around alternative RL | Corrected assignment-critical case. Treats the move as an early competitive-map signal, preserves unknown funding/product evidence, and defines concrete funding, hiring, publication, and benchmark watchpoints. |

### Rejected controls

- The same Oak Lab packet was correctly suppressed for Engineering because it
  contains a high-level technical thesis but no method, artifact, evaluation,
  or operational evidence to test.
- An informal browser-use model comparison was suppressed for both audiences
  because its task set, scoring, configuration, and reproducibility were
  missing.
- An unsupported Uber autonomy allegation and a temporary Claude promotion
  were suppressed for Investment because neither supported a defensible
  transmission path.

## Assessment and stop condition

The current prompts meet the bounded calibration goal. They produce different
decisions and different next actions from the same evidence when the audience
requires it, retain useful early Investment signals, and keep weak technical or
commercial claims out. The output is somewhat detailed, but the detail carries
source qualification, a real decision boundary, or an executable next step
rather than generic prose.

Adi reviewed this first five-Insight checkpoint on 2026-07-16 and approved a
second bounded expansion of exactly five additional surfaced Insights. No
prompt change was made between cohorts.

## Second bounded evaluation

The expansion consumed the five highest-ranked positive routes from July 11
and then the five highest-ranked positive routes from July 10. It stopped as
soon as exactly five additional audience decisions surfaced. Ten Events
produced fifteen decisions: five surfaced and ten suppressed. The expansion
used 47,581 input tokens and 6,763 output tokens, read 3,584 cached prefix
tokens, and recorded $0.212334 in proxy-reported cost.

### Additional surfaced Insights

| Audience | Feed item | Title | Qualitative judgment |
| --- | --- | --- | --- |
| Engineering | Jul 11 #9 | Test long-horizon computer use beyond short UI tasks | Strong. Treats a reported five-hour game run as an anecdotal capability signal, not a reliability result, and converts it into a repeated state/recovery/intervention evaluation on a representative workflow. |
| Investment | Jul 11 #9 | Reported five-hour game win raises computer-use agent bar | Defensible and distinct. Challenges a specific thesis assumption about UI-agent horizons while explicitly rejecting enterprise reliability inference from one game outcome. |
| Investment | Jul 10 #1 | Thinking Machines raises $2B around custom-model strategy | Strongest new Investment result. Preserves the disclosed financing, named participants, open-source/custom-model direction, and unknown commercial traction, then defines product-release comparisons that could turn investor participation into an operating signal. |
| Engineering | Jul 10 #4 | Lean artifact makes agent proof auditable | Strongest new Engineering result. Identifies the verifier-backed artifact as the development, preserves the provider-reported evidence boundary, and gives exact pinned build, source-audit, and specification-alignment checks. |
| Investment | Jul 10 #4 | Claimed Lean-checked proof raises the bar for agentic reasoning | Useful but the softest surfaced result. The public-equity transmission is indirect; however, it remains conditional, identifies formal verification as the differentiator, flags the prompt/runtime inconsistency, and requires reproduction before treating the claim as a capability milestone. |

### Additional rejected controls

- Unsupported Altman employment commentary and Buterin governance preferences
  were rejected because neither supplied a concrete development or defensible
  company-level diligence path.
- A Grok comparison was rejected for both audiences because the benchmark,
  methods, settings, and results were absent.
- Thinking Machines' separate manifesto was rejected for both audiences after
  the stronger financing/product announcement cleared Investment; the essay
  added direction but no released artifact, measured result, customer, or
  commercialization evidence.
- A vague laboratory data-capture anecdote was rejected for Engineering, while
  a small AI-news launch and free deployment URL were rejected for Investment.

## Cumulative assessment

The current contracts have now evaluated sixteen Events and twenty-five
audience decisions: ten surfaced and fifteen suppressed. They used 76,797 input
tokens and 11,385 output tokens, read 12,544 cached tokens, and recorded
$0.334543 in proxy-reported cost. Engineering has ten decisions with four
surfaced; Investment has fifteen decisions with six surfaced.

The second cohort reinforces the first conclusion: the prompts distinguish an
interesting topic from an actionable audience Insight, produce materially
different last-mile interpretations of the same packet, and preserve caveats
instead of converting every frontier claim into a result. No repeatable error
justifies another prompt hill climb yet. The next useful action is human ranking
of the ten surfaced Insights, with particular scrutiny of the softer formal-
proof Investment implication. The remaining catalog stays paused.

## Investment next-step correction

Adi's review of the computer-use Insight exposed one real persona leak in
Investment v6. Its proposed next step—obtain run logs and execute a controlled
multi-hour UI benchmark—was a strong AI Engineering action, but not the most
useful instruction to a BIT portfolio manager or equity analyst.

The correction stayed deliberately narrow. Investment v9 now states that BIT
is an active technology public-equity investor and requires consequential
private-lab evidence to be translated into a public-company competitive map,
business-model exposure, semiconductor or energy value-chain effects, and an
observable thesis implication. An Investment next step must name a thesis
assumption, company or business-model exposure, value-chain consequence, or
investment-relevant observable. It must not assign an engineering experiment
unless that experiment directly resolves a named investment question. The
prompt still does not claim knowledge of BIT's live holdings, position sizes,
valuations, or private internal theses.

Two early-signal rules from the assignment were made explicit after bounded
controls found that an evidence threshold designed for product launches could
incorrectly suppress them:

- a specific, attributed strategic thesis may surface before realized adoption
  when it challenges a concrete procurement, competitive-map, business-model,
  or value-chain assumption and defines observable validation; and
- a specific capability observation or reported result may surface before
  independent replication when its anecdotal or provider-reported status is
  preserved and it challenges a named capability, cost, reliability, moat, or
  workflow assumption.

Four fixed controls passed under v9: Sutton's Oak Lab formation, Nadella's
enterprise-control thesis, Thinking Machines' custom-model strategy, and the
reported five-hour computer-use run. The computer-use Investment next step now
tracks independent/provider evidence on long-horizon desktop completion,
intervention rates, and costly-error rates for multi-application enterprise
workflows. The Engineering result remains intentionally different: it asks the
AI team to build and run the repeated workflow evaluation.

### Full bounded replay

Investment v9 was then replayed over all fifteen previously evaluated
Investment candidates, while the ten AI Engineering v5 decisions remained
unchanged. Fourteen of fifteen Investment decisions matched v6. The one change
was a second Thinking Machines strategy envelope that moved from suppressed to
surfaced because it contains a specific customization thesis. That decision is
defensible in isolation but redundant beside the stronger financing/product
envelope; it is an editorial cross-Event deduplication finding, not a reason to
weaken the per-Event Investment standard or build a reconciliation subsystem
during this calibration.

At that v9/v5 checkpoint, the prompt-qualified store contained twenty-five decisions:
eleven surfaced and fourteen suppressed. Investment v9 accounts for seven
surfaced and eight suppressed decisions; AI Engineering v5 accounts for four
surfaced and six suppressed decisions. Together they used 81,612 input tokens
and 11,410 output tokens, read 12,544 cached Investment-prefix tokens, and
recorded $0.346956 in proxy-reported cost.

Qualitatively, the original ten surfaced Insights still form the useful review
set. The additional Thinking Machines note should be treated as redundant in
final selection. The strongest Investment improvements are the corrected
computer-use diligence action, Nadella's procurement/control watchpoint, and
Sutton's talent-formation signal. No further prompt change is justified before
human ranking; the next useful step remains selecting the strongest three to
five Insights for the submission.

## Engineering v6 and balanced 50-decision expansion

Adi's review of the Lean-checkable proof Insight found that its summary and
implication were useful but its proposed action was audience-remote: rebuilding
and auditing the Lean repository would assign the AI team a specialized formal-
methods project rather than test the transferable verifier-gate pattern in its
own work. Engineering v6 now chooses the smallest investigation that resolves
the named team decision and reproduces a source project only when the team
could plausibly adopt or compare it directly. The corrected Lean action applies
an immutable verifier gate to a representative financial extraction and
reconciliation workflow.

A six-control replay then separated concrete early signals from inspirational
noise:

- the Lean verifier workflow, a reported five-hour computer-use run, a
  first-hand multi-model browser-use evaluation, an intent-aware evidence-
  capture pattern, and Nadella's protected-learning-assets thesis surfaced;
- Thinking Machines' broad customization/interaction manifesto remained
  suppressed because it supplied no mechanism, measured behavior, or bounded
  build decision; and
- the browser-use evaluation was retained only after inspecting the complete
  packet. It contained relative performance, token, price, and speed
  observations across several models, not merely the isolated phrase “Grok is
  Opus-class for browser use.” The surfaced note labels the evidence anecdotal
  and asks for a controlled internal comparison.

After the control set passed, the exact current Investment v9 and Engineering
v6 contracts evaluated 50 new positive audience routes. The cohort was balanced
across the five highest-ranked positively routed Events per day and excluded
the 25 current decisions already present. It produced 30 surfaced and 20
suppressed decisions:

| Audience | Decisions | Surfaced | Suppressed | Cached input tokens | Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| AI Engineering | 26 | 14 | 12 | 28,672 | $0.507623 |
| Investment | 24 | 16 | 8 | 41,216 | $0.438862 |
| **Total** | **50** | **30** | **20** | **69,888** | **$0.946485** |

The qualitative result is precision-positive at the per-Event gate. Strong
notes include adversarially durable alignment training, Jacobian-lens agent
monitoring, SWE-Bench Pro task-validity failures, continuous-voice controller
architecture, programmatic tool calling, horizontal work agents, and
Transformers-native vLLM serving. Suppressions correctly rejected missing
papers, unsupported benchmark claims, generic sovereignty and recursive-
improvement theses, a departure without a consequential next move, product
privacy controls without implementation evidence, and technically credible but
team-remote modular robotics.

The expansion also exposed a separate product problem: 30 surfaced decisions
represent roughly 23 unique developments. Exact but independent Feed Events can
describe the same launch, producing duplicate audience notes for Meta Muse,
GPT-5.6, the Meta Model API, and Grok 4.5. Each result is defensible in isolation,
so weakening either audience prompt would remove useful signals. The next
quality boundary is cross-Event consolidation or final selection, not another
prompt hill climb. The run stops at 50 new decisions rather than scaling to the
remaining catalog.

The current prompt-qualified store contains 75 decisions: 43 surfaced and 32
suppressed. It has read 89,600 cached input tokens and records $1.305057 in
proxy-reported cumulative cost. These are audit decisions, not 43 recommended
submission items; semantic duplicates and weaker notes still require final
selection before the 3–5 item case-study proof.

## Fresh July 14–15 top-30 expansion

After the Evidence and audience-routing window extended through July 15, the
frozen Investment v9 and Engineering v6 contracts evaluated the top 30 routed
Events on each new day. The run made 98 audience decisions over 60 Events and
completed without a pending or failed row:

| Audience | Decisions | Surfaced | Suppressed | Cached input tokens | Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| AI Engineering | 44 | 25 | 19 | 50,176 | $1.093977 |
| Investment | 54 | 32 | 22 | 102,400 | $1.223590 |
| **Total** | **98** | **57** | **41** | **152,576** | **$2.317567** |

The decisions reinforce the audience split. WANDR's research-agent coverage
benchmark, frozen-probe reward signals, agent-trajectory safety evaluation,
claim-level factuality checks, SHARP deployment caveats, per-viewer MCP access,
and kernel-specific FP4 serving behavior produced concrete Engineering notes.
Classified-AI procurement, K–12 distribution, coding-agent bundling, insurance
constraints on agent deployment, open-model inference share, regional Gemini
distribution, and reported frontier-model task-cost changes produced distinct
Investment notes. Thin hiring posts, unsupported launch rumors, event
announcements without artifacts, broad custom-RL theses, anecdotes without
evaluation detail, and product milestones without a public-equity transmission
path were suppressed.

The review found no repeated persona or final-gate error that justifies another
prompt revision. It did find two downstream quality boundaries:

- Inkling appears through four independent Feed Events and the reported
  Google/DoD agreement through two. Each per-Event result is defensible, but the
  reader should receive one consolidated development rather than every valid
  angle as a separate note.
- One old 2022 ChatGPT launch Event resurfaced through current network activity.
  The first-party-only Insight packet omitted both source timestamps and the
  current reactions that caused the resurfacing, so the model treated the old
  launch as current. This is a temporal-provenance false positive in candidate
  packaging, not evidence that Investment v9 should become stricter in general.

The prompt-qualified store now contains 173 decisions: 100 surfaced and 73
suppressed. It has read 242,176 cached input tokens and records $3.622624 in
proxy-reported cumulative cost. Further broad generation is paused at this
checkpoint. The next quality work is to expose enough temporal provenance to
prevent stale-source Insights and to consolidate semantically overlapping
Events before final human selection.
