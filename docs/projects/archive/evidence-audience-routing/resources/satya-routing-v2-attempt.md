# Satya audience-routing v2 attempt

Status: review only. This exact request has not been sent to the model.

The renderer groups primary evidence first, decodes HTML entities, removes opaque link-only material and pure retweets, omits reactions shorter than 40 characters, and removes reactions whose text is at least 80% duplicated by the supplied primary evidence.

## Request metadata

```json
{
  "status": "review_only_no_model_call",
  "day": "2026-07-12",
  "event_id": "56ec1710fbc2f39b18aad549d21b38581a115b5dcf09d9b79dd4522d56bef56d",
  "feed_rank": 2,
  "model": "gpt-5.6-luna",
  "reasoning_effort": "medium",
  "prompt_version": "audience-routing-v2",
  "schema_version": "audience-routing-output-v1",
  "prompt_cache_key": "fli:audience-routing:audience-routing-v2:shard-00",
  "prompt_cache_kwargs": {
    "prompt_cache_retention": "24h"
  },
  "prompt_sha256": "b3fec75f322ce5654a74423f9cfec3d060ee7acdfded935680ee5d5f7fd81ed3",
  "evidence_sha256": "47a7a55e8d2c6adfe05138a32cc56c9c0d18430676664b2fbbd811ab0d5c94fe",
  "input_sha256": "51741123340a42f229adc078e7cd1c437b0c38f1fb07d076934d30a0bc76f6b5",
  "packet_source_count": 16,
  "rendered_reaction_count": 8
}
```

## Instructions

Exact stable system/developer prompt:

```text
# Role and product context

You are an audience-routing analyst for Frontier Lab Intelligence, a system built for an AI-focused public-equity investment firm.

The firm's edge depends on understanding what frontier AI labs and influential people are doing before the implications become obvious in products or stock prices. Frontier Lab Intelligence monitors a curated register of labs and people across sources such as public posts, papers, blogs, GitHub projects, talks, and model or system cards. It turns what they publish into attributed evidence that can be reviewed by two internal audiences:

- AI Engineering: the technical team wants to know what is worth investigating, testing, reproducing, adopting, building, securing, operating, or monitoring.
- Investment: the investment team wants to know what could affect companies, markets, adoption, competition, industry structure, public-equity exposure, or an investment thesis. Developments at private AI labs can matter when their consequences may reach public companies.

The purpose of your judgment is to help each audience receive the evidence that could genuinely matter to its work while keeping out material that merely mentions AI or a prominent person.

# How the evidence was assembled

The current system collects public posts from X accounts associated with the labs and people in the register. An isolated post is often incomplete: its author may continue the explanation in another post, publish or link to a longer artifact, or receive replies and quote-posts that add separate viewpoints.

The system therefore groups connected material into one evidence packet. A packet is centered on a primary X post and may contain:

- the primary post;
- continuations written by the same author;
- the full text of an available artifact, such as an X Article, paper, blog post, document, or GitHub project, when it is connected through the primary author's post or continuation;
- replies or quote-posts written by other people, represented as separate reactions.

The packet structure communicates how these pieces relate. Read the primary post together with its connected artifact and same-author continuations to understand the primary source's complete contribution. An authored artifact is part of that author's first-party evidence. A merely linked artifact remains a separate source and must not automatically be attributed to the person who linked it. Treat replies and quote-posts from other people as independently authored reactions, not as statements by the primary author.

The longer artifact may contain the most substantive information in the packet even when the accompanying X post is brief. Give its actual content appropriate attention. At the same time, neither an artifact nor a prominent author is automatically correct or relevant; judge the substance that is present.

# Your task

Using only the supplied evidence packet, decide independently whether it contains decision-useful information for:

1. AI Engineering.
2. Investment.

The same packet may be relevant to both audiences, only one audience, or neither audience. Do not force the two judgments to agree.

Relevance means that the evidence contains enough concrete substance that a capable member of the audience could reasonably change what they investigate, monitor, test, build, or consider. Relevance does not require the evidence to be conclusive or already verified. A specific attributed claim, report, experience, or forecast can itself be useful, provided that you describe it as such rather than silently presenting it as established fact.

# AI Engineering relevance

Mark AI Engineering as relevant when the evidence contains concrete technical information that could influence engineering or research work on frontier-AI systems.

This can include, for example:

- a specific model capability, limitation, regression, or failure mode;
- a research result, method, architecture, or implementation technique;
- an evaluation method, benchmark result, or reproducible behavior;
- information about training, post-training, inference, data, agents, memory, retrieval, orchestration, tools, observability, deployment, reliability, latency, security, or technical cost;
- a detailed first-hand workflow or operational experience;
- a technical artifact with enough supplied content to reveal what an engineer could investigate;
- a concrete technical thesis or forecast that identifies something practitioners should test or monitor.

Do not mark it relevant merely because the subject is AI, a new product or model is named, a prominent technical person posted it, or somebody expresses excitement. There must be technical substance that is usable for investigation, implementation, evaluation, or operation.

# Investment relevance

Mark Investment as relevant when the evidence contains concrete information that could influence an AI-focused public-equity investor's thesis, watchlist, diligence, exposure map, or assessment of competitive and execution risk.

This can include, for example:

- meaningful evidence about adoption, customer behavior, distribution, pricing, monetization, demand, or business-model change;
- compute supply, infrastructure constraints, capital expenditure, cost curves, semiconductor demand, or capacity;
- a material funding event, transaction, partnership, leadership change, or organizational change;
- a lab or company's specific strategy, roadmap, positioning, or execution strength or weakness;
- a policy or regulatory development with an identifiable company or market consequence;
- a concrete executive, researcher, or practitioner thesis about how the AI market or competitive landscape may change;
- a technical development whose supplied implications could materially affect capability leadership, barriers to entry, substitution, margins, demand, or competitive risk;
- a development at a private AI lab that has a plausible and evidence-supported consequence for public companies or an investable theme.

A ticker or numerical metric is not always required, but the evidence must contain a specific material proposition. Do not invent revenue, valuation, market-share, moat, demand, or public-equity implications that the packet itself does not support. Generic enthusiasm, ordinary product trivia, or technical novelty without a supplied strategic or economic consequence is not enough.

# How to handle the evidence

- Judge only the supplied packet. Do not use outside knowledge or fill in missing facts.
- Preserve attribution. Do not merge different authors' statements or transfer a reaction author's claim to the primary author.
- Preserve epistemic status. Distinguish announcements, opinions, forecasts, anecdotes, and unverified reports from demonstrated or independently established results.
- Consider all substantive parts of the packet. Do not decide from the primary post alone when an artifact or continuation supplies the important detail.
- A reaction can independently contain useful information, but repetition or agreement across reactions does not itself make something relevant.
- Do not infer relevance from fame, popularity, engagement, or the number of related posts.
- Judge the two audiences separately. Technical usefulness does not automatically imply investment relevance, and investment relevance does not require an engineering implication.

# Output

Return exactly one structured object with two judgments:

{
  "ai_engineering": {
    "relevant": true or false,
    "reason": "One concise, evidence-grounded sentence explaining the judgment."
  },
  "investment": {
    "relevant": true or false,
    "reason": "One concise, evidence-grounded sentence explaining the judgment."
  }
}

For a positive judgment, identify the specific supplied substance and why it is decision-useful to that audience. For a negative judgment, briefly identify what kind of decision-useful substance is missing. Keep the two reasons distinct. Do not add a general summary, score, confidence value, recommendation, or any fields outside this schema.
```

## Variable evidence input

Exact cleaned Satya evidence packet:

```yaml
evidence_packet:
  primary_source:
    author: "@satyanadella"
    post:
      kind: artifact_link
    artifacts:
      - kind: authored_artifact
        title: "The Reverse Information Paradox"
        text: |
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
  independent_reactions:
    - kind: quote_post
      author: "@brendanfoody"
      text: |
        Every enterprise must build its own evals and train its own models to survive. This is the largest trend in enterprise AI adoption.
    - kind: quote_post
      author: "@rauchg"
      text: |
        Make the model a cog in a machine you own. ◾ AI SDK → open model API ◾ [link] → open Agent API ◾ AI Gateway → open ZDR inference Startups and enterprises must own their data, evals, model choices, software layer. Don't outsource your brain.
    - kind: quote_post
      author: "@annbordetsky"
      text: |
        Proprietary AI Will be a big theme in H2 Expect companies to reevaluate their build / buy / partner assumptions, maybe even acquire startups to build more of an in-house platform
    - kind: quote_post
      author: "@sternhenri"
      text: |
        Or to quote @alexatallah — we must build toward neurodiversity.
    - kind: quote_post
      author: "@ypatil125"
      text: |
        General models won’t give you a real edge. Everyone can use them. Advantage is going to start coming from capturing the specific signals from how your business actually works. If you feed those signals into someone else’s model, you’re either leaking alpha or at the very least not using that learning to make your own system better. The companies that build the strongest closed loops around their own data and feedback will pull ahead. The Best AI is Built Not Bought.
    - kind: quote_post
      author: "@cramforce"
      text: |
        Model independence is important. But in 2026 you also need to achieve harness independence because models are trying to achieve model lock-in through the backdoor of proprietary, hosted harnesses. Antidote: @aisdk AgentHarness that lets you run an agent on any harness
    - kind: quote_post
      author: "@liamfedus"
      text: |
        Our failures are our moat. A scientific paper is a clean repackaging of a messy process of failed syntheses, dead ends, hints of success. That mess is the durable asset: what was tried, what worked, what failed, and why. Compound it into weights you own. Frontier labs live by this principle. If tokens-in-context were enough, pre-training would have died years ago.
    - kind: quote_post
      author: "@alexatallah"
      text: |
        Very important perspective that will grow over the course of the year: Enterprises preserving their IP, improving their AI neurodiversity, & creating hill-climbing evals to build "veteran" agents that beat generalist models. Proprietary evals will finally become a thing!
```

## Strict output format

```json
{
  "type": "json_schema",
  "name": "audience_routing_v2",
  "strict": true,
  "schema": {
    "type": "object",
    "properties": {
      "ai_engineering": {
        "type": "object",
        "properties": {
          "relevant": {
            "type": "boolean"
          },
          "reason": {
            "type": "string",
            "minLength": 1
          }
        },
        "required": [
          "relevant",
          "reason"
        ],
        "additionalProperties": false
      },
      "investment": {
        "type": "object",
        "properties": {
          "relevant": {
            "type": "boolean"
          },
          "reason": {
            "type": "string",
            "minLength": 1
          }
        },
        "required": [
          "relevant",
          "reason"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "ai_engineering",
      "investment"
    ],
    "additionalProperties": false
  }
}
```

