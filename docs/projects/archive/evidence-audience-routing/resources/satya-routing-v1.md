# Satya Audience Routing v1 — Exact Review

## Run

- Event: `56ec1710fbc2f39b18aad549d21b38581a115b5dcf09d9b79dd4522d56bef56d`
- Feed rank: #2
- Snapshot SHA-256: `3632a213e6b78b0d847b7867b7adbc3a9cf8b6c44d4d19b44447109c52a16c68`
- Evidence SHA-256: `47a7a55e8d2c6adfe05138a32cc56c9c0d18430676664b2fbbd811ab0d5c94fe`
- Variable-input SHA-256: `41149897a3ee3d7560b6cc9a5d25f48e26e45e44e817f9c5b43503c222124f75`
- Model: `gpt-5.6-luna`
- Reasoning: `medium`
- Prompt: [audience_routing_v1.txt](../../../../src/fli/prompts/audience_routing_v1.txt)

The Responses request uses the linked prompt as the stable `instructions` prefix and the exact text below as `input`. Rank, engagement, triage outcome, runner IDs, and source URLs are not included in the model input.

## Strict Output Schema

```json
{
  "ai_engineering": {
    "relevant": "boolean",
    "reason": "string"
  },
  "investment": {
    "relevant": "boolean",
    "reason": "string"
  }
}
```

The actual API schema is strict: both audience objects and both fields are required, booleans are JSON booleans, and additional properties are rejected.

## Source Blocks

1. `x_post` · @satyanadella · `root` · 23 chars
2. `x_post` · @tadityasrinivas · `quote` · 356 chars
3. `x_post` · @brendanfoody · `quote` · 131 chars
4. `x_post` · @rauchg · `quote` · 257 chars
5. `x_post` · @annbordetsky · `quote` · 178 chars
6. `x_post` · @_onionesque · `quote` · 32 chars
7. `x_post` · @ben_burtenshaw · `quote` · 187 chars
8. `x_post` · @sentdex · `quote` · 37 chars
9. `x_post` · @sternhenri · `quote` · 63 chars
10. `x_post` · @ypatil125 · `quote` · 470 chars
11. `x_post` · @cramforce · `quote` · 268 chars
12. `x_post` · @liamfedus · `quote` · 366 chars
13. `x_post` · @zymazza · `quote` · 23 chars
14. `x_post` · @aravsrinivas · `quote` · 497 chars
15. `x_post` · @alexatallah · `quote` · 275 chars
16. `artifact` · @satyanadella · `self_published_artifact` · The Reverse Information Paradox · 5076 chars

## Exact Variable Input

```text
Route this Feed-kept evidence packet by audience.
Judge each numbered source independently before judging the full packet.

<EVIDENCE_BLOCK index="1">
[type=x_post | author=@satyanadella | relation=root]
<VERBATIM_TEXT>
https://t.co/xv6csf1SbV
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="2">
[type=x_post | author=@tadityasrinivas | relation=quote]
<VERBATIM_TEXT>
“While the great innovation that comes from model providers having fair use rights to train models on public data is needed, I find it ironic that the status quo is to then turn around and impose restrictive terms on distillation, and to reserve the right to learn from customer usage and interaction data.” @satyanadella’s formalized version of this meme:
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="3">
[type=x_post | author=@brendanfoody | relation=quote]
<VERBATIM_TEXT>
Every enterprise must build its own evals and train its own models to survive. This is the largest trend in enterprise AI adoption.
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="4">
[type=x_post | author=@rauchg | relation=quote]
<VERBATIM_TEXT>
Make the model a cog in a machine you own. ◾ AI SDK → open model API ◾ https://t.co/O7y9dmUqk5 → open Agent API ◾ AI Gateway → open ZDR inference Startups and enterprises must own their data, evals, model choices, software layer. Don't outsource your brain.
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="5">
[type=x_post | author=@annbordetsky | relation=quote]
<VERBATIM_TEXT>
Proprietary AI Will be a big theme in H2 Expect companies to reevaluate their build / buy / partner assumptions, maybe even acquire startups to build more of an in-house platform
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="6">
[type=x_post | author=@_onionesque | relation=quote]
<VERBATIM_TEXT>
With a three year lag, but good.
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="7">
[type=x_post | author=@ben_burtenshaw | relation=quote]
<VERBATIM_TEXT>
"Build your own proprietary learning environments within the tenant boundary to train or tune models, where models learn against real workflows without exposing the company’s knowledge. "
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="8">
[type=x_post | author=@sentdex | relation=quote]
<VERBATIM_TEXT>
tldr: host open source models on-prem
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="9">
[type=x_post | author=@sternhenri | relation=quote]
<VERBATIM_TEXT>
Or to quote @alexatallah — we must build toward neurodiversity.
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="10">
[type=x_post | author=@ypatil125 | relation=quote]
<VERBATIM_TEXT>
General models won’t give you a real edge. Everyone can use them. Advantage is going to start coming from capturing the specific signals from how your business actually works. If you feed those signals into someone else’s model, you’re either leaking alpha or at the very least not using that learning to make your own system better. The companies that build the strongest closed loops around their own data and feedback will pull ahead. The Best AI is Built Not Bought.
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="11">
[type=x_post | author=@cramforce | relation=quote]
<VERBATIM_TEXT>
Model independence is important. But in 2026 you also need to achieve harness independence because models are trying to achieve model lock-in through the backdoor of proprietary, hosted harnesses. Antidote: @aisdk AgentHarness that lets you run an agent on any harness
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="12">
[type=x_post | author=@liamfedus | relation=quote]
<VERBATIM_TEXT>
Our failures are our moat. A scientific paper is a clean repackaging of a messy process of failed syntheses, dead ends, hints of success. That mess is the durable asset: what was tried, what worked, what failed, and why. Compound it into weights you own. Frontier labs live by this principle. If tokens-in-context were enough, pre-training would have died years ago.
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="13">
[type=x_post | author=@zymazza | relation=quote]
<VERBATIM_TEXT>
https://t.co/OJLSl6E0qd
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="14">
[type=x_post | author=@aravsrinivas | relation=quote]
<VERBATIM_TEXT>
"I find it ironic that the status quo is to then turn around and impose restrictive terms on distillation, and to reserve the right to learn from customer usage and interaction data. If learning flows in only one direction, economic value converges toward the owners of the learning infrastructure rather than the creators of the knowledge itself. Therefore, it's imperative that we distribute the learning infrastructure to every firm so that they can control their own learning loop." Well said.
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="15">
[type=x_post | author=@alexatallah | relation=quote]
<VERBATIM_TEXT>
Very important perspective that will grow over the course of the year: Enterprises preserving their IP, improving their AI neurodiversity, &amp; creating hill-climbing evals to build "veteran" agents that beat generalist models. Proprietary evals will finally become a thing!
</VERBATIM_TEXT>
</EVIDENCE_BLOCK>

<EVIDENCE_BLOCK index="16">
[type=artifact | author=@satyanadella | relation=self_published_artifact | title=The Reverse Information Paradox]
<VERBATIM_TEXT>
In the age of intelligence, how should firms protect their core IP?

Nobel Prize winning economist Kenneth Arrow famously described a paradox in the market for information. “Its value for the purchaser is not known until he has the information, but then he has in effect acquired it without cost.” In Arrow’s “Information Paradox,” the seller risks giving away knowledge in order to sell it.

AI creates the reverse problem. In the AI age, the buyer risks giving away knowledge, just in order to use what they bought.

You essentially pay for intelligence twice, once with money, and again with something even more valuable: the proprietary knowledge you must reveal to make that intelligence useful. The better you want the model to perform, the more of that knowledge you have to feed it!

Over time, the information asymmetry becomes increasingly skewed. The seller learns more and more about you as you use what you purchased, while you learn very little about what the seller is learning in return.

That is what I think of as the Reverse Information Paradox.

Patents solve one aspect of Arrow’s paradox. They let an inventor disclose an idea without simply giving it away. The Reverse Information Paradox needs its own equivalent.

This requires more than data protection. Models learn from "exhaust," the prompts people write, the tools agents use, and especially the corrections people make when the model is wrong. Every correction is distilled into institutional know-how. It's the kind of knowledge a competitor could never buy, and the kind that leaks almost imperceptibly: trace by trace, correction by correction, eval by eval.

In consuming intelligence, you are creating intelligence. And what you create should belong to you. This is your particular intelligence, in Hayek's sense: the knowledge of time, place, and circumstance that no one else can hold. It knows what you think, what you value, and how you measure success.

While the great innovation that comes from model providers having fair use rights to train models on public data is needed, I find it ironic that the status quo is to then turn around and impose restrictive terms on distillation, and to reserve the right to learn from customer usage and interaction data. If learning flows in only one direction, economic value converges toward the owners of the learning infrastructure rather than the creators of the knowledge itself. Therefore, it's imperative that we distribute the learning infrastructure to every firm so that they can control their own learning loop.

As Alex Karp put it: "What the technical customers want is control over their compute, their models, their data stack, and their alpha. They want to know they own the means of production, and it's not being transferred to someone else." The current regime does precisely the transfer Karp and companies fear.

That is why enterprises need a real trust boundary for their human capital and token capital to compound. It is where an organization’s data, traces, evals, adapted weights, and memory accumulate and improve together. And it is a hard boundary across which nothing crosses, not even the intelligence exhaust, without consent. Enterprises will demand the rights to use model outputs to fine tune and/or train their own models.  I think of this as every firm’s right to align models to their enterprise accountability obligations.

In the cloud era, enterprises accumulated data. In the AI era, they accumulate learning. The trust boundary must evolve accordingly, from protecting information to protecting the mechanisms through which organizations learn, adapt, and compound intelligence. There are a few things every enterprise must do to ensure this:

Control: Create your private evals, because evals define what “good” looks like inside the organization. Also, retain ownership of your organization’s memory, traces, feedbacks, decisions, and institutional context, and ability to use outputs of models from your own tasks and queries.

Capability: Build your own proprietary learning environments within the tenant boundary to train or tune models, where models learn against real workflows without exposing the company’s knowledge.

Choice: Ensure the orchestration layer is decoupled from any single model. Ask yourself: If any one model you are using is taken away, do you still have the ability to operate and optimize for your evals using other models?  Does your company “veteran” capability remain with you even if a given “generalist” model is taken away?

Cost: By decoupling the orchestration layer, you are also able to bring together context, models, and tasks in the most efficient and cost-effective way without sacrificing quality.

Compound: Bring these four together and you create your own continuous learning loop (i.e. hill climbing machine) that will allow your AI investments to compound the value of your firm.

In other words, a company should be able to use a model without giving up the knowledge that makes it unique. That is the reverse information paradox we need to confront.

</VERBATIM_TEXT>
</EVIDENCE_BLOCK>
```

## Exact Raw Output

```json
{
  "ai_engineering": {
    "relevant": true,
    "reason": "The artifact presents concrete engineering choices—private evals, tenant-boundary learning environments, retained traces and adapted weights, and model-independent orchestration—with explicit implications for reliability, portability, data control, and cost."
  },
  "investment": {
    "relevant": true,
    "reason": "The attributed thesis that firms will protect proprietary learning loops and shift toward build, buy, partner, or acquisition decisions provides a material watchpoint on enterprise AI adoption, vendor lock-in, competitive differentiation, and infrastructure strategy."
  }
}
```

## Telemetry

- Input tokens: 4698
- Cached tokens: 0
- Cache-write tokens: 0
- Output tokens: 210
- LiteLLM-reported cost: $0.005958
- Response ID: `resp_yObcR32LNkK43MzPQjCJjRkXLPbOEOAs79S3TgKxuKHfSkJ2TXQm39wphj5UfGXWidJYxy95PHoFEFU9tqlgU1XAOKba7wFI1H_tsmrfbfxfXd83xctAvG8GlH4f_jhR1thRtcwEeBe3Q1SZlG-Ol5GDPBDff_y7FHWrWTJx75Zl6NI06dC8u26mNeWFq3Wfl-F7RzBv2oFosCJ7TYjMpbe80BNKrjfsqpCwdLzSsVUCniY1AdrAh0Ep5gHmkblx3Q_Y5OK2te1G5G1Uw_nj3Yr_-MJOCcNvlOkNmMNjfqrX76NpVRd4btt6_vh9VZ8BzuNbLLyzbrRQ4QtXNKbqZM8svgZDpa8g_106KdJfCW5APsEcr0SLnlhzebwjIkChm5xPF5tk_vKEmHMEYNzvmg9cSJFT7mhKwjITmdPLwb5R4Z8Vdp1K0unN_OTqm46zCWob37iNAwh9W3bQZ_xi9Pso`

A single call cannot produce a cache read because no earlier request populated either routing cache lane. Cache behavior should be judged only after a later multi-envelope cohort.

