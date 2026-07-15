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

No few-shot examples were added. The zero-shot instructions produced the
desired separation, so examples would currently add length and anchoring risk
without evidence of a remaining systematic failure.

## Bounded evaluation

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

Do not rewrite or expand the prompts again before human review. The next useful
step is for Adi to inspect these five surfaced Insights in the UI and select
the strongest 3–5 submission examples. Do not run the remaining 751-request
catalog until that review either approves the contract or identifies a
repeatable failure.
