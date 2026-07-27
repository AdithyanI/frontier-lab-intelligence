# Findings

Every finding here was measured against the live service at
`http://127.0.0.1:8797` or the repository databases on 2026-07-27, not read
from documentation. The command that produced each number is recorded so the
finding can be re-checked or shown live.

Severity is judged by one question: **does this cost Adi the job?**

## Index

| # | Finding | Severity | Status |
| --- | --- | --- | --- |
| 1 | Investment read-through concentrated on four mega-caps | medium | **diagnosed** — cause is registry coverage, not selection |
| 2 | Cross-platform entity resolution ~1% populated | medium | open |
| 3 | Insights are ranked but never scored | medium | addressable by B1 |
| 4 | Ranks 101–200 recall probe designed and never run | high | **B2** |
| 5 | Insights page subtitle over-promises | low | open |
| 6 | "Aion" leaks into Investment rejection reasons | low | needs a decision |
| 7 | The AI Engineering lane is the stronger of the two | — | **asset** — lead the demo here |
| 8 | Both lanes concentrate harder than the input does | medium | open |
| 9 | Editorial layer measurably overrides the deterministic rank | — | **asset** — best answer in the audit |
| 10 | Every day is written as if it is day one | high | **B3** — designed, deferred |
| 11 | No stability measurement | medium | **B4** |
| 12 | Quote validation is not claim validation | medium | 5 audited defects; fix deferred |
| 13 | Only 45% of citations are actually verified | high | **B5** — 16% unverified `web` tier |
| 14 | The "3–5 most interesting insights" deliverable does not exist | high | **B0** — cheapest, highest-weighted |
| 15 | 17 days vs suggested ~3-month window, 68% of budget unspent | medium | needs a one-sentence answer |
| 16 | Coverage does not track the portfolio (rho 0.205) | high | **B6** — the case for the cascade |
| 17 | Three current top-ten positions absent from the system | high | **fixed this session** — roster merged |
| 18 | Company linkage is high quality wherever it happens | — | **asset** — 614/614 labels correct |
| 19 | The blind spot is disruption-side, not small-cap | high | **B7** — needs a coverage universe |

Findings 7, 9 and 18 are strengths, recorded here because they were discovered by
measurement rather than assumed. Findings 10 and 12 were independently found by
the pipeline agents during the 5–17 July batch audit; their write-ups are better
than this one's and are quoted in place.

**If only one thing gets done: finding 14.** It is an explicit required
deliverable, it answers the prompt's self-declared most important question, the
material already exists, and it carries zero risk.

Recommended build order and design constraints live in `../tasks.md` under
**Recommended Work Order**.

---

## 1. Investment read-through is concentrated on four mega-caps

**Severity: high.** This is the sharpest question in the room, and it lands on
BIT's own identity rather than on a rubric line.

Across all 17 days, 75 kept Investment Insights:

| Portfolio company | Mentions |
| --- | ---: |
| Alphabet | 20 |
| NVIDIA | 18 |
| Microsoft | 14 |
| Meta | 13 |
| Amazon | 4 |
| AMD | 2 |
| Intel · Micron · Reddit · TSMC | 1 each |

Four names take roughly 83% of all portfolio read-through.

Outside-portfolio coverage is thin and scattered: Cloudflare 3, Apple 2,
Oracle 2, Z.ai 2, then single mentions of TeraWulf, Tencent, Alibaba,
Snowflake, SenseTime and others.

Why it matters, in BIT's own words:

- The flagship strategy emphasis "points to companies **below the most
  universally covered mega-caps**" (`bit-capital-editorial-context.md`).
- The case prompt on the registry: "the real signal is often **one layer
  down**."
- The case prompt's own example of what they want: "implications for the
  **semiconductor and energy supply chains**." Energy appears once, as
  TeraWulf. Semis beyond NVIDIA appear five times total.

A PM can reasonably say: *this is well-built, and it is telling me about the
four companies I already have twelve sources on.*

**The honest counter-argument, which is real:** most frontier labs are private,
and the prompt concedes "part of the judgment is connecting lab developments to
where they actually land for a public-equity investor." The mega-caps genuinely
are where frontier-AI news lands in public equity. The concentration may be a
correct reflection of the world rather than a defect of the system.

**What is not defensible is not having noticed.** Adi should walk in with this
number already measured.

### DIAGNOSED — 27 July. The cause is network coverage, not selection.

The obvious follow-up question is: *are you dropping the smaller companies, or
were they never there?* That is answerable for free, from data already stored,
with no model calls. Compare the company mix of the 75 **kept** Insights to the
690 **declined** candidates across the same 17 days.

| Bucket | n | Mentions a non-mega-cap and **no** mega-cap |
| --- | ---: | ---: |
| Kept Insights | 75 | **12 (16%)** |
| Declined candidates | 690 | **12 (1%)** |

Declined-pool company mix: Meta 30, Alphabet 27, NVIDIA 25, Microsoft 19 —
against Palantir 3, AMD 3, Alibaba 2, Intel 2, Cloudflare 2, Salesforce 2, and
single mentions of Dell, Qualcomm, TSMC, IREN.

**The selection stage is not the cause. It is the corrective.** A published
Insight is roughly sixteen times more likely to reach outside the mega-caps than
a declined candidate is. The concentration is inherited from the evidence pool,
and editorial selection measurably widens it.

The twelve declined non-mega-cap candidates were also declined for good reasons,
not lazy ones:

- Qualcomm ModCon — "an event advertisement, not a shipped product,
  partnership result, adoption signal, or financial development."
- TSMC — "the Taiwan import claim lacks a durable company-specific TSMC bridge;
  aggregate value is confounded by packaging, memory, tariff timing, and product
  mix."
- IREN — "New York's one-year permitting pause is real, but the evidence does
  not tie it to a current IREN or Hut 8 hyperscale project."

The TSMC rejection in particular identifies a genuine confound. None of the
twelve reads as an error.

**So the real constraint is upstream: who the registry listens to.** The ~2,400
tracked accounts are frontier-AI researchers and lab staff. They discuss
frontier labs. They do not discuss Vertiv, Credo, Astera Labs, Coherent or
Constellation Energy. To reach the semiconductor and energy supply chains the
prompt names, the registry needs a *different class* of source — sell-side semis
analysts, datacenter and power trade press, supply-chain trackers — not more
frontier-AI researchers one hop further out in the same follow graph.

This reframes the Thursday answer from an apology into a diagnosis:

> "I measured it. Selection isn't the cause — my published insights are sixteen
> times more likely to reach outside the mega-caps than the candidates I
> declined. The constraint is my source network: frontier-AI researchers talk
> about frontier labs. Covering semis and energy needs a different tier of
> source, and that's the top of my roadmap."

**Severity revised: high → medium.** It remains the top roadmap item, but it is
a known, measured, correctly-diagnosed coverage limit rather than a hidden bias.

Command:

```bash
# tmp/inv_kept.jsonl = all 17 days of investment kept payloads
# then regex company names across items[] vs declined[]
```

---

## 2. Cross-platform entity resolution is ~1% populated

**Severity: medium-high.** Named explicitly inside the joint-highest-weighted
section (Registry, 20%).

The prompt asks for entity resolution "to know that an X handle, an **arXiv
author name**, and a **GitHub account** are the same person."

Measured across 2,400 registry entities:

| Channel kind | Count |
| --- | ---: |
| x | 2,437 |
| website | 37 |
| github | **9** |
| blog | 5 |
| arxiv | **0** |

Multi-platform entities: **32 of 2,400** (~1.3%).

The schema is correct — one entity owns many channels, which is exactly BIT's
model, and the 32 multi-channel entities prove it works. The data is simply not
there. `docs/STATUS.md` defers this deliberately.

**Defense:** the prompt sanctions this — "a thoughtfully-scoped set of sources
done well beats a broad set done badly." Say it before they find it.

---

## 3. Insights are ranked but never scored

**Severity: high for the Quant session.** Named in the section the prompt says
they "look hardest" at.

The prompt: "Score and rate both the **contributors** and the **insights**."

Current state:

| Object | Scored? | Validated? |
| --- | --- | --- |
| Contributors | Yes — `network_rank`, tie-aware entity-support percentile | Yes, twice: downstream hit-rate gradient, and Spearman **0.877** against the frozen Digg baseline (72/100 top-100 overlap) |
| Events | Yes — `daily-rank-v2`, lexicographic, zero tunable constants | Yes — monotone gradient 34.3% → 53.9% → 64.2% → **72.1%** by trusted-voter count |
| **Insights** | **No score at all** | **Not validated** |

The `/api/insights` item carries `rank` and `rank_rationale` and no numeric
field of any kind. The brief ordering is agent judgment with a written reason.

**The real framing, which is stronger than the checkbox:** rigor decays
downstream. Stage 1 (who to watch) and stage 2 (what to look at) are scored,
deterministic, replayable, and externally validated. Stages 3–5 (relevant?
surface? rank first?) are model judgment with recorded reasons and no
measurement. The stages with the most rigor are the ones the reader never sees;
the stage the reader actually consumes has the least.

That is a genuinely good thing to say out loud before they say it.

---

## 4. The one named measurement that was designed and never run

**Severity: high for the Quant session. Also the best available opportunity.**

`docs/references/scoring-validation.md`, "Honest limits," states it directly:

> The top-100 gate makes "all routed and authored Insights come from the top
> 100" true by construction. The unmeasured quantity is **recall lost below the
> gate**. A bounded probe exists but has not been run: route ranks 101 to 200
> for one day with the same prompts and count how many would have been judged
> relevant.

A quant will ask what was filtered out. Right now the answer is "unknown, and I
designed the experiment but did not run it." Running it turns the weakest point
in the validation story into a measured one. Bounded to one day, roughly $1–2.

Related and already measured this session: at the rank-100 boundary on thin
days every Event has exactly one vote, so layer 2 becomes a sample of size one.
Because it is a six-decimal value it essentially never ties, so layer 3 (author
standing) fires on only **1.3%** of adjacent comparisons. On 5 July this cut
Anthropic's emergent-misalignment research at rank 111 (author position 0.9960)
below a football transfer rumour at 109 (author position 0.0000).

---

## 5. The Insights page subtitle over-promises relative to BIT's own wording

**Severity: low. Trivial to fix, and it changes how the whole declined log
reads.**

Page subtitle today:

> "Position-relevant frontier AI changes for theses, diligence, exposures, and
> **competitive risk**."

BIT's wording:

> "Framing: implications, **tickers**, theses. (Note: most labs are private, so
> part of the judgment is connecting lab developments to where they actually
> land for a **public-equity** investor.)"

The system's operative bar matches BIT, not the subtitle. Of the 58 declined
candidates on 21 July, roughly 24 reject on some form of "no named
public-company financial transmission."

Example — Fei-Fei Li's World Labs / SceniX post at Feed rank 18:

> "World Labs' private-company acquisition has no disclosed price, revenue
> effect, or direct portfolio path, and no Aion workflow decision."

Under the subtitle's promise of "competitive risk," that rejection looks too
strict. Under BIT's actual wording it is exactly right. Fix the subtitle, not
the prompt.

---

## 6. "Aion" leaks into Investment rejection reasons

**Severity: low, but it is a live thread an interviewer can pull.**

Aion is the AI-engineering-side workload. It appears inside Investment-lane
rejections:

- rank 18: "...no direct portfolio path, **and no Aion workflow decision**."
- rank 3: "...do not establish portfolio impact **or transfer to Aion's
  research workload**."

Reasonable question from the other side of the table: why does the investment
filter care about your research stack? Worth checking whether this is intended
cross-audience reasoning by the editorial layer or prompt bleed.

---

## 7. The AI Engineering lane is the stronger of the two

**Severity: none — this is an opportunity, and it changes the demo order.**

124 kept Engineering Insights across 17 days, versus 75 Investment.

**Every single one carries a `decision_rule`.** Zero missing. These are
falsifiable acceptance thresholds, not advice. 21 July, Insight #1:

> "Proceed only if containment blocks every seeded privilege or egress
> violation and the trajectory monitor detects every remaining seeded policy
> breach while preserving at least 95 percent of baseline accepted-task
> completion; otherwise pause broader tool or data access."

The titles are conclusion-led and consistently opinionated. Two patterns repeat
often enough to read as a house style, which is exactly the "taste" the prompt
asks for:

**Refuses to adopt on benchmarks alone** (8+ instances):

- "LongCat's open release earns a bounded model-routing test, **not adoption**"
- "Hy3 earns an Aion canary, **not a benchmark-based switch**"
- "Gemma 4 belongs in a frozen extraction test, **not the routing table yet**"
- "Grok 4.5 earns a research bakeoff, **not a default route**"
- "Kimi K3 merits a task-specific trial, **not a benchmark-led model switch**"
- "Perplexity's managed skills merit a bounded report test, **not an
  orchestration rewrite**"

**Prices work by outcome, not by token** (5+ instances):

- "Internal tasks, **not token prices**, should choose the research-agent stack"
- "Route Sol on **accepted-task cost**, not advertised token savings"
- "Agent routing should optimize **accepted work**, not frontier-token share"
- "Evaluate research agents on **progress per dollar**"

The lane is written for **Aion**, BIT's real publicly-described agentic research
platform, sourced from their own job postings — and
`ai-engineering-editorial-context.md` explicitly forbids inventing private
architecture details or claiming FLI's implementation is BIT's. That is
well-researched restraint, not roleplay.

Tail quality holds. On 21 July the #9 insight states its own weakness in its
rank rationale: "the evidence is one gateway's launch behavior rather than a
proven Aion bottleneck."

**Implication for Thursday:** Carlos, Vlad and the AI team are this lane's
audience — "the people you'd be joining." Lead the walkthrough here, not with
Investment. Leading with Investment puts mega-cap concentration (finding 1) on
screen in the first two minutes.

---

## 8. Both lanes concentrate harder than the input does

**Severity: medium.** Same defect, two different dimensions.

Engineering theme distribution across the 124 titles:

| Theme | Count | Share |
| --- | ---: | ---: |
| evaluation / traces / benchmarks | 52 | 41% |
| containment / authorization / isolation | 24 | 19% |
| model routing / adoption | 21 | 16% |
| retrieval / data / provenance | 13 | 10% |

Volume per day: average 7.3, peak 11 (8 and 10 July), versus Investment's 4.4
average and 6 peak.

Two consequences:

1. **Cross-day repetition.** "Agents need enforced containment boundaries"
   arrives in some form on 5, 7, 8, 9, 10, 13, 15, 16, 19, 20 and 21 July. Each
   day is internally deduplicated; across days it is not.
   `docs/STATUS.md` already discloses this as a known limitation.
2. **Actionability breaks down at volume.** A brief proposing 7–11 bounded
   experiments per day is proposing roughly 50 a week to a team that can
   realistically run one or two. The prompt's bar is "a reader knows what it
   means and what to do." Ranking plus honest rank rationales mitigate this —
   the reader can stop after #3 — but the raw count still overshoots.

Stated as one finding across both lanes: **19,657 Events become 199 Insights,
and those Insights cluster far harder than the evidence did.** Investment
concentrates on four companies; Engineering concentrates on two themes.

Some of this is the world, not the system — frontier AI in July 2026 genuinely
was mostly about agent safety and evaluation. But it is the second-sharpest
question available, and it should not be a surprise.

---

## 9. The editorial layer measurably overrides the deterministic rank — in a legible direction

**Severity: none. This is the strongest single measurement in the audit.**

The obvious challenge to the insight layer is: *"the model just decides, and you
trust it."* The answer is not to replace judgment with a formula — the prompt
calls an arbitrary weighted sum a red flag. The answer is to **anchor the
judgment against the deterministic rank and measure the disagreement.**

Every Insight carries the `feed_rank` of its source Events. That rank is
`daily-rank-v2`: lexicographic, replayable, hash-pinned, already validated.
So for each day, correlate published Insight rank against the best evidence rank
behind it.

Spearman across 16 days, 75 Investment Insights:

- **mean rho = 0.179**, median 0.350
- editor agreed with evidence order (rho > 0.5) on **3 of 16** days
- editor substantially overrode it (rho < 0.2) on **5 of 16** days

Near-zero correlation. The editor is not echoing the rank. **The direction of
the override is the finding:**

**Demoted — strong evidence rank, low Insight rank:**

| Evidence rank | Insight | Title |
| ---: | ---: | --- |
| 1 / 1360 | #4 | "Inkling creates a new NVIDIA workload, **not yet a material demand**" |
| 1 / 1360 | #3 | "Claude demand supports AWS usage, **not yet AWS returns**" |
| 2 / 1360 | #3 | "Enterprise-owned learning can strengthen Microsoft's control point" |
| 3 / 1360 | #3 | "Sol demand is strong, **but Microsoft economics remain unclear**" |
| 4 / 1360 | #5 | "Meta's physics result strengthens capability perception, **not economics**" |
| 5 / 1360 | #3 | "GPT's verified Erdős proof strengthens Microsoft's OpenAI exposure" |

**Promoted — weak evidence rank, high Insight rank:**

| Evidence rank | Insight | Title |
| ---: | ---: | --- |
| 86 / 1360 | #2 | "Oracle's OpenAI backlog now carries an **investment-grade warning**" |
| 84 / 1360 | #2 | "Managed Agents can deepen Gemini API usage" |
| 73 / 1360 | #1 | "NVIDIA's Diffusers integration strengthens its software moat" |
| 58 / 1360 | #2 | "Chrome **distribution** gives Gemini a stronger adoption path" |
| 54 / 1360 | #1 | "Gemini's Southeast Asia growth strengthens Alphabet's **distribution**" |
| 53 / 1360 | #1 | "CXMT's HBM lag keeps **Micron's** AI-memory advantage intact" |

Every demotion is a loud story with no financial transmission — and the title
says so unprompted ("not economics", "not yet returns", "economics remain
unclear"). Every promotion is a quieter story with a concrete mechanism: credit
risk, memory supply, distribution channel.

**The two layers are measuring different things, and they are supposed to
disagree.** The deterministic rank measures *attention* — how much of the
trusted network engaged. The editorial layer measures *consequence* — whether
anything lands for a public-equity reader. A correlation near 1.0 would mean the
model adds nothing. A correlation near 0 with random swaps would mean noise.
rho ≈ 0.18 with a consistent, readable direction means the editor is doing real
work in the intended direction.

Note also: two of the six promotions are **Oracle and Micron** — non-mega-caps.
Independent corroboration of the finding-1 diagnosis that selection reaches
*down* the cap curve, not up it.

**Use this as the answer to "how do you know the model isn't just deciding?"**

> "It is deciding — that's the point of the layer. But I can measure how far it
> departs from the deterministic rank, and in which direction. It demotes loud
> stories with no financial transmission and promotes quiet ones with a real
> mechanism. If it agreed with my deterministic rank I'd delete it."

**Follow-up worth doing:** surface the evidence rank per Insight in the UI so a
reader can see the override without running a script (B1).

### Both lanes measured — and the difference is interpretable

| Lane | mean rho | median | days |
| --- | ---: | ---: | ---: |
| Investment | **0.179** | 0.350 | 16 |
| AI Engineering | **0.421** | 0.536 | 17 |

The Engineering editor follows the deterministic rank roughly twice as closely
as the Investment editor. That is the right direction: for the Engineering
reader the trusted network *is* the audience — AI engineers ranking what AI
engineers published — so attention is a decent proxy for "what should we look
at." For the Investment reader attention is a poor proxy for financial
consequence, so the editor must override far more.

The divergence is not noise. It is audience-appropriate, and it is measured.

### Free invariant found alongside: zero double-counting

Across all 17 days and both lanes, **no Event is used by more than one published
Insight on the same day.** Zero reuses over 199 Insights. Within-day evidence
partitioning is clean, so no story is silently counted twice.

Command: `tmp/audit/{investment,ai_engineering}.jsonl` → per-day Spearman of
`item.rank` against `min(events[].feed_rank)`; event-id counter per day.

---

## 10. Every day is written as if it is day one

**Severity: high. This is the most visible defect in the output, and the fix is
already designed.**

`_prior_insights` in `src/fli/insights/editorial_runs.py:653` queries
`WHERE item.day = ?`. Same day only. It is a resume-and-reuse mechanism for
re-running a single day, **not** cross-day memory. Nothing in the editorial
packet tells the editor what was published yesterday.

The consequence is visible in the output. In the AI Engineering lane, some
version of "agents need enforced containment boundaries" is published on 5, 7,
8, 9, 10, 13, 15, 16, 19, 20 and 21 July. Each day is internally deduplicated;
across days it is not.

The pipeline agents found this independently during the 5–17 July batch audit,
with a sharper diagnosis than the theme count:

> The same NVIDIA announcement supported near-identical Investment conclusions
> on 5 and 6 July. The Apple complaint reappeared on 10 and 11 July without a
> new ruling, remedy, or other decision-relevant development. **Event IDs
> differed, so within-day identity validation could not detect the repetition.**

That last clause is the mechanism: dedup keys on Event identity, and a
continuing story generates new Events each day.

**The fix is designed and deferred** — follow-up item 2 in
`docs/references/daily-intelligence-batch-audit-2026-07-05-17.md`:

> expose compact recent-development fingerprints — canonical source URLs,
> accepted Insight IDs, company/mechanism keys, and the prior core claim — and
> require the editor to state what is new. It should **not** inject prior
> Insight prose wholesale because that would anchor the next editor.

The prose-versus-fingerprint constraint is the non-obvious part and it is
correct. Feeding yesterday's prose forward would make each day's editor write in
the shadow of the last one.

**Why this matters beyond repetition:** a daily briefing that cannot say "this
extends what I told you Thursday" is not really a briefing. It is seventeen
unrelated documents. The prompt asks for what matters *today*, and part of what
matters today is what is new relative to what the reader already knows.

**This is the recommended build (B3).**

---

## 11. There is no stability measurement

**Severity: medium. Cheap to close.**

Nobody has re-run the same day twice and compared the output. So the question
"if you re-ran 21 July right now, would you get the same six Insights?" has no
answer.

This matters because it is the honest form of the objection Adi raised himself:
*"we're just relying on the model to behave."* The defense is not that the
system is deterministic — the editorial layer is deliberately not, and finding 9
shows that is the point. The defense is that it is **stable**: the same input
produces substantially the same output.

Everything upstream of the editorial layer is already replayable and
hash-pinned (`input_sha256`, `source_rank_input_sha256`, frozen artifact
manifests). Only the final 100 → 6 step is unmeasured for stability.

Bounded: one day, three runs, count recurrence. ~$10. **B4.**

---

## 12. Quote validation is not claim validation

**Severity: medium — and this one has named, audited defects.**

`src/fli/insights/editorial_runs.py:1613` enforces
`if excerpt.casefold() not in artifact_text.casefold(): raise`. That is a real
control at the write boundary — the system cannot persist a fabricated quote.

But it is a containment check, not an entailment check. A genuine quote can sit
underneath a claim it does not support. The pipeline agents found the same gap
and, unlike this audit, produced a defect list:

> Validation proves that an artifact excerpt exists in the frozen text. It does
> not prove that the excerpt supports every material clause written around it.
> The audit found gaps in NVIDIA credit-risk detail, Muse distribution claims,
> trace-mining metrics, Inkling reasoning-effort claims, and SPACE scale claims.
> **These were citation-selection failures, not necessarily missing underlying
> evidence.**

Five named cases, with a diagnosis: the evidence existed, the wrong slice of it
was cited.

**The better fix is follow-up item 4, not a prompt change.** The agents asked
for exact source-text windows and historical-availability metadata so a reviewer
can see a citation's surroundings and judge support directly. That is
infrastructure for human review rather than another model-graded check. It is
deferred.

**Disclose this before being asked.** "My quote check is enforced and my quotes
are real. It does not prove the sentence around the quote is right, I have five
audited examples of exactly that failure, and I know which fix I want."

---

## 13. Only 45% of citations are actually verified

**Severity: high. This is the most precise version of the integrity claim, and
it is currently overstated.**

The enforced check at `editorial_runs.py:1613` is real. But two lines above it:

```python
for citation in normalized["citations"]:
    if citation["kind"] != "artifact":
        continue
```

**The substring check runs on artifact citations only.** Measured across all 199
published Insights, 398 citations:

| Kind | n | Share | What is actually enforced |
| --- | ---: | ---: | --- |
| `artifact` | 179 | **45%** | URL must be frozen evidence for the Event; `artifact_id` required; excerpt required; **excerpt must occur in the frozen artifact text** |
| `event` | 157 | **39%** | URL must be in that Event's frozen `source_urls`; `published_at` must match the frozen source date. Excerpt present on only 36 of 157, and never checked |
| `web` | 62 | **16%** | `retrieved_at` and `excerpt` required to be *present*. Nothing else. **The URL is not required to be frozen evidence of any Event, and the excerpt is never compared to anything** |

Tiers: 45% excerpt-verified, 39% provenance-verified, **16% model-asserted and
unchecked.**

The `web` class is the exposure. `editorial.py:341` requires only that the
fields exist:

```python
if kind == "web" and (retrieved_at is None or excerpt is None):
    raise ValueError(...)
```

No stored fetched page text exists to check against, so the excerpt, the URL and
the retrieval timestamp are all model output.

**In fairness, the web sources are good ones.** Domains include `sec.gov`,
`blogs.microsoft.com`, `anthropic.com`, `arxiv.org`, `hkexnews.hk`,
`aisi.gov.uk`, and the Illinois legislature's own bill text. This is not the
model inventing blogspam. It is the model quoting real, well-chosen primary
sources with no mechanism to confirm the quote.

**A hypothesis worth recording as refuted:** quantitative claims are *not*
concentrated in the unverified tier. Numbers appear in 22% of artifact excerpts,
24% of web, 22% of event — flat. The exposure is uniform, not targeted at the
hard numbers.

**Related, and smaller:** 63 of 199 Insights (32%) rest on **no artifact-backed
citation at all** — 28/75 Investment, 35/124 Engineering. Those are built from
post text plus web references. Not necessarily wrong for a story with no
document behind it, but "we read the documents, not the tweets" holds for two
thirds of the output, not all of it.

**Also:** 164 of 398 citations carry no `published_at`, including 146 of the 179
artifact citations. The batch audit already flagged exactly this.

**How to say it Thursday, before being asked:**

> "45% of my citations are excerpt-verified against frozen text and cannot be
> fabricated. 39% are provenance-verified — the URL must be frozen evidence of
> that Event. 16% are web references where I require an excerpt and a retrieval
> time but never verify them, because I don't store the fetched page. That tier
> is where I'd spend next."

**The fix is already designed** — batch-audit follow-up 4, exact source-text
windows and historical-availability capture. Promoting `web` citations into the
artifact store extends the enforced check to 61% of citations.

---

## 14. The "3–5 most interesting insights" deliverable does not exist

**Severity: high, and it is the cheapest thing on this list to fix.**

The prompt's final-report deliverable, verbatim:

> the 3–5 most interesting *real* insights the system surfaced — **"proof that
> it works"**

Searching the entire repository, `"most interesting"` appears in exactly two
files: `case-prompt.md` and the source-material transcript of the prompt itself.
**It appears in no deliverable, no doc, and no page of the app.**

`docs/references/reviewer-guide.md` is genuinely good — organized by rubric
weight, which is the right instinct, walking a reviewer through Registry →
Signal-vs-noise → Scoring → Delivery → Ingestion → UI. But it is a **navigation
guide, not a result showcase.** It says where to look. It never says "here are
the five best things this system found, and why each is non-obvious."

Frontend features are `architecture`, `bit-lens`, `evidence`, `insights`,
`network`, `system`. No highlights or best-of surface exists.

**Why this is the sharpest gap in the audit:**

The prompt names one question as the most important of all — *"did this surface
something we'd genuinely want to know, and did it keep the noise out?"* — and
weights signal-vs-noise at 20%. The 3–5 showcase is the direct answer to the
first half. Without it a reviewer must browse 199 Insights across 17 days and
two audiences and hope to be impressed on their own time.

**The material exists.** 199 Insights, all cited, all ranked, with written
rationales. This is curation and a short write-up, not engineering. An hour or
two, zero risk to the demo, touching the highest-weighted criterion.

The submission is frozen so it cannot be added retroactively — but Adi drives
the demo himself on Thursday. Arriving with five chosen, rehearsed, non-obvious
examples *is* the deliverable, moved to the room where it now matters more.

**Nominate from measured strength, not taste.** Finding 9 gives the selection
rule for free: the biggest evidence-rank-to-Insight-rank promotions are exactly
the cases where the system saw something the crowd did not. "Oracle's OpenAI
backlog now carries an investment-grade warning" came from evidence rank 86 of
1,360. "CXMT's HBM lag keeps Micron's AI-memory advantage intact" from rank 53.
Those are demonstrably non-obvious *by the system's own deterministic measure* —
a far better story than "I liked this one."

---

## 15. 17 days delivered against a suggested ~3-month window, with 68% of the budget unspent

**Severity: medium. Likely defensible, but the answer must be ready.**

The prompt, on extraction: structured, attributed, cited insights **"over a
recent window (~3 months suggested)."**

Delivered: **17 days**, 5–21 July 2026. Roughly 19% of the suggested window.

Separately, from `tokenomics.md`: total recorded spend is **$31.797248** against
a stated **€100 reimbursable budget** — about a third. The prompt explicitly
says they are interested in *how* it is spent.

Together those invite one question: *you had two thirds of the budget left, why
not more coverage?*

**The likely honest answer is a data constraint, not a budget one.** X's
first-party search does not allow cheap backfill of three months of timeline
data across ~2,400 accounts, and the repository already operates a "seven-day
first-party X evidence projection." Collection ran forward from the start of the
case rather than backwards from it. If that is right the answer is strong: the
window is bounded by what can be *honestly retrieved*, not by effort or money,
and 17 consecutive fully-replayable days with frozen evidence beats 90 shallow
ones. The prompt itself says "scoped-well beats broad-badly."

**Open question — verify before Thursday.** This audit did not confirm the
retrieval constraint from provider docs or the ingestion code. It is inferred
from the seven-day projection language. Adi should be able to state the real
reason in one sentence. If the true reason is "I ran out of time," say that —
still defensible, but a different sentence.

---

## 16. Coverage does not track the portfolio

The strongest measurement in the second half of this audit, and the reason to
take the cascade proposal seriously.

The full BIT portfolio is already loaded into every Investment editorial call.
`.agents/skills/fli-daily-intelligence/references/bit-investment-context.json`
is 103,115 characters and carries `portfolio.holdings` — 34 audited names with
weights, cited to page 8 of the 31 December 2025 annual report — plus 34
`company_profiles` with business summaries and operating drivers. It is wired
in at `src/fli/insights/editorial_runs.py:41`.

So the model has the book. It does not use it in proportion to the book.

Across 442 Investment insights there are 703 `affected_entities` mentions, 624
of them to audited roster names.

    Spearman(position weight, mention count) across 34 holdings = 0.205

Measured against the **current** top ten (30 June 2026 factsheet):

| Holding | Weight | Mentions |
| --- | ---: | ---: |
| Amazon | 10.4% | 40 |
| Micron | 8.6% | 6 |
| IREN | 8.5% | 4 |
| SanDisk | 6.0% | 0 |
| Robinhood | 5.0% | 0 |
| Marvell | 4.8% | 0 |
| TSMC | 4.6% | 7 |
| Infineon | 4.4% | 0 |
| Hinge Health | 4.2% | 1 |
| Oscar Health | 4.2% | 1 |
| **total** | **60.7%** | **59 — 8.5% of coverage** |

Against four names that are *not* in the current top ten:

| Holding | Dec-2025 weight | Mentions |
| --- | ---: | ---: |
| Alphabet | 4.48% | 160 |
| NVIDIA | 3.26% | 141 |
| Microsoft | 2.89% | 137 |
| Meta | 3.49% | 70 |
| **total** | **14.1%** | **508 — 73.4% of coverage** |

Eleven audited holdings, 27.3% of fund weight, were never named once in 17
days.

**The honest counter-argument, which should be conceded before it is raised.**
Those four are the frontier labs' closest public proxies — Alphabet is
DeepMind, Microsoft is OpenAI, Meta is Llama, NVIDIA is the substrate. A system
tracking frontier labs will mention them because they are the subject matter,
not because it is biased. "Not in the June top ten" also does not mean sold;
Alphabet at 4.48% in December could sit just under the 4.2% cut today.

So do not claim the system is broken. The defensible sentence is narrower:

> Coverage is a function of who the news is about, not of what the fund owns.

For a system whose stated job is connecting private-lab developments to
public-equity landing spots, that relationship should not be near zero.

**Why this matters for the cascade proposal.** The passive fix — put the roster
in context and let the model use it — has already been tried, for 17 days, and
this is the result. Availability is not consideration. A fan-out stage that
requires an explicit verdict per company is the difference between the two.

Commands:

    .venv/bin/python  # editorial_insight.analysis_json over audience='investment'
    # roster from bit-investment-context.json portfolio.holdings
    # weights cross-checked against the 30 Jun 2026 factsheet, ISIN DE000A2N8127

---

## 17. Three current top-ten positions do not exist in the system

The loaded roster is the 31 December 2025 audited baseline: 34 names, €1.088bn
fund assets. The fund as of 30 June 2026 is **28 positions, €1.594bn**. Three
names in the current top ten are absent from `bit-investment-context.json`
entirely — no holding row, no company profile, no aliases:

| Holding | Current weight |
| --- | ---: |
| SanDisk | 6.0% |
| Marvell Technology | 4.8% |
| Infineon | 4.4% |
| **total** | **15.2% of the fund** |

These are 2026 additions made after the audited baseline. The system is
structurally incapable of naming them, which is why each scores zero in finding
16 rather than scoring low.

**Marvell is the sharpest instance in this audit.** BIT's own June 2026
factsheet commentary supplies the mechanism:

> Marvell enables hyperscalers to connect non-NVIDIA AI accelerators to
> NVIDIA's networking architecture, addressing a key bottleneck in scaling
> heterogeneous AI clusters.

That is a frontier-lab read-through written by the client, in a document the
repository already cites, about a company the system cannot mention.

**Fix, roughly half a day.** Keep one roster with one provenance story — the
last complete audited portfolio — and add these three as rows carrying their
own `as_of: 2026-06-30` and the factsheet URL. Every row dated and cited, which
is the house style everywhere else in the repo. Do not build a
`confirmed_current` / `historical` tier vocabulary; it buys little and costs a
clean answer to "where did this list come from?".

**Disclosure limit worth stating out loud.** The June factsheet names only 10
of 28 positions — 60.7% of the fund. The remaining 18 positions, ~33.9%, are
not public. The 30 June 2026 semi-annual report would give the complete
current roster; it was not published as of 2026-07-27 (404 at the HansaInvest
path, while the 2025-06-30 equivalent returns 200). December therefore remains
the only complete roster that exists publicly, and using it is correct.

Suggested framing: *"I can see 60.7% of the book from public disclosure. Here
is the coverage gap I measured inside it, and here is the one file you would
swap on day one to point this at the live portfolio."*

---

## 18. Company linkage is high quality wherever it happens — strength

Recorded because two plausible failure modes were tested and both came back
clean. These should be said out loud, and they narrow the problem in finding 16
to *which companies get considered* rather than *how well they are linked*.

**No hallucinated holdings.** Of 614 entity mentions labelled
`scope: "portfolio"`, **614 matched an audited roster name or a declared alias.
Zero false claims** that a company is a BIT holding. Given that the scope label
is model-asserted and nothing validates it at write time, this could have gone
badly and did not.

**Mechanism is real, not decorative.** Median `mechanism` length is 147
characters — a sentence of transmission, not a tag.

**Impact direction is not cheerleading.**

| impact | count | share |
| --- | ---: | ---: |
| positive | 272 | 39% |
| mixed | 186 | 27% |
| uncertain | 137 | 20% |
| negative | 97 | 14% |

Alphabet's own mix is 50 positive / 44 mixed / 38 negative / 28 uncertain,
which is the profile of a system willing to argue against a holding.

Note for future auditors: 11 of the 703 entities use a legacy shape
(`as_of` / `name` / `relationship`) from a single early run. The current shape
is `name` / `scope` / `impact` / `mechanism`. Querying the wrong key returns
zeros and reads like a catastrophic gap. It is not one.

---

## 19. The blind spot is disruption-side, not small-cap

Finding 1 framed the concentration problem as mega-cap versus small-cap. That
framing is wrong, and a flat position-weight metric is the wrong denominator —
a frontier-lab intelligence system has no business writing about Luckin Coffee.

Splitting the roster by transmission mechanism instead:

- **Build-side** — TSMC, Micron, IREN, SanDisk, Marvell, Infineon, Coherent,
  Lumentum, Broadcom, AMD, Intel, HUT 8, Pure Storage. AI capex and scarcity
  flow to them.
- **Disruption-side** — Duolingo, Lemonade, Xometry, Axon, Datadog, Reddit,
  Rubrik, Netskope. A frontier model release changes their competitive
  position.
- **Out of scope** — Luckin Coffee, InPost, GCL-Poly, Kaspi, Grindr, AUTO1,
  Robinhood. Write the reason once and stop measuring against them.

The system covers build-side and is close to blind on disruption-side. Four
never-mentioned names are described as AI-native **in the repository's own
company profiles**:

| Holding | Repo's own description | Mentions |
| --- | --- | ---: |
| Duolingo | BIT thesis cites "Duolingo Max's generative-AI video call" | 0 |
| Lemonade | "an AI-powered, full-stack insurer" | 0 |
| Xometry | "an AI-native, two-sided marketplace" | 0 |
| Axon | "AI-enabled workflows" | 0 |

**And this is the direction where BIT actually acted.**
`docs/references/bit-capital-editorial-context.md` records that the team exited
software exposure in February 2026 "as application-layer disruption risk
increased," cutting from 39 positions to 29. That was a disruption-side call.
The system is blind in precisely the direction of the client's most visible
recent decision.

**Design consequence.** Define the coverage universe **once, in the repository,
with a written reason per name, in and out.** Not per-day by the model — if the
model chooses the universe each morning it will choose the mega-caps again and
the bias is simply laundered. BIT's own factsheet supplies the boundary
language: *"the structural beneficiaries of the AI investment cycle."*

Caution against over-excluding: Oscar Health and Hinge Health are both current
top-ten positions and Oscar was June's strongest contributor, so "healthtech is
out of scope" is wrong for the fund. Out of scope for *frontier-lab
transmission* is the accurate and more honest reason.

---

## Strengths worth rehearsing

These are already true and already measurable. They should be said out loud.

### S1. The ranker and the judge are information-isolated

`packet_from_event` sends the model the root post, same-author continuations,
and attached artifacts. It excludes vote counts, daily rank, engagement,
amplifier identities, third-party replies, and all retweets.

This is why the hit-rate gradient means something: the ranker sees only crowd
behavior, the judge sees only content, and neither can see the other. If the
judge could see the rank, the validation would be circular.

### S2. The old score was the exact thing BIT named as a red flag

> "An arbitrary weighted sum dressed up as a 'score' is a **red flag**; a
> simple model you can defend and have tested is exactly what we want."

`attention-v1.1` was a 55/25/20 weighted percentile blend. `daily-rank-v2` is
lexicographic with zero tunable constants, exact `Decimal` arithmetic,
tie-aware percentiles, and a deterministic Event-ID final tiebreak. Independent
replay reproduces `replay-validation.md` exactly.

That is not a small improvement. It is moving off the named red flag.

### S3. Hallucination control is enforced, not aspirational

`src/fli/insights/editorial_runs.py:1613`:

```python
if excerpt.casefold() not in artifact_text.casefold():
    raise ...
```

Artifact citations are rejected at the write boundary unless the excerpt occurs
verbatim in the frozen artifact text. Fabricated quotes are structurally
impossible.

**Known limit worth stating honestly:** this is a *quotation* check, not an
*entailment* check. It proves the quote is real. It does not prove the quote
supports the claim.

### S4. Deduplication works and leaves an audit trail

Of the 58 declined candidates on 21 July, 10 were rejected as duplicates with
an explicit back-pointer:

- "repeats the OpenAI incident selected at **rank 1** but adds speculation"
- "repeats the Laguna S 2.1 announcement already reviewed at **rank 3**"
- "repeats the Gemini release selected at **rank 5**" (×2)

Cross-Event story merging is handled — as suppression with a named target,
rather than as a merge.

### S5. The system tracks evidence that argues against its own conclusions

Editorial Events carry a role. Across 7 days: 15 of 84 insights are merges, and
the roles in use are `primary`, `supporting`, `context`, and
**`counterevidence` ×4**.

21 July, Insight #2, "Rubin gets a measured efficiency proof before its
software stack is ready":

| Event | Role |
| --- | --- |
| Feed #20 | primary |
| Feed #57 | supporting |
| Feed #62 | **counterevidence** — a PyTorch PR for Rubin support that a maintainer rejected over correctness issues |

The headline then reads "meaningful first-silicon evidence, **not yet proof of
broad production economics**." The counter-evidence changed the conclusion.

This was invisible in the UI until this session. It is now rendered.

### S6. The best single rejection on the list

Feed rank 28, on a legal-features paper:

> "The legal-feature paper is **not supported by the packet's stale unrelated
> artifacts** and does not clear the citation bar."

The model declined because its **own evidence packet was bad**. That is
evidence-quality awareness, not content judgment, and it is a strong thing to
show live.

---

## Measured limits worth disclosing before being asked

- **30.8% of amplification arrives after the ranking day closes.** 11,315
  same-day members versus 16,347 lifetime; 54% of Events are still growing when
  ranked. Clock bias is mild (70.3% captured for 00:00–03:59 posts versus 60.0%
  for 20:00–23:59), so this is a window-length issue, not a late-posting issue.
- **Events are ranked once and never reconsidered.** An Event is published on
  its earliest canonical source day; later activity appends without re-ranking.
  Verified: the Anthropic paper was active on both 5 and 6 July but appears in
  no later day's ranking.
- **Weekend degradation.** 1-vote Events in the top 100: Sun 5 Jul 55, Sat 11
  Jul 25, Sun 12 Jul 48, Sat 18 Jul 46, Sun 19 Jul 39 — and **zero on every
  weekday**. The hit-rate gradient flattens on those days (5 Jul: 33% / 32% /
  30%).
- **Window is 17 days, not the suggested ~3 months.** The prompt says "recency
  and **trend** matter." Trend claims over 17 days are thin.
- **35 of 60 artifacts on 21 July classify as `other`.** Catalog-wide the store
  holds 4,597 `ready`, 391 `unavailable`, 356 `catalogued`, 34 `retryable`.

---

## Shipped this session

Both changes surface judgment the system already recorded. Neither adds new
judgment, new data, or model spend.

1. **Funnel yield line** under the Insights page title:
   `6 published · 66 candidates reviewed · 58 declined in writing`, where the
   last part opens and scrolls to the declined log. Previously the page showed
   six insights with no denominator, and the declined log — the strongest
   signal-vs-noise evidence in the product — sat collapsed at the bottom behind
   six long insights.
2. **Merge and role labels** in the Sources block: `ORIGINAL FEED · 3 EVENTS
   MERGED`, then `PRIMARY` / `SUPPORTING` / boxed `COUNTEREVIDENCE`.

Also fixed earlier in the session: the How-page collect figure, which omitted
the tracked network entirely and showed Reply but not Retweet despite retweets
being the largest relation type (462 versus 89 on 21 July).
