# Findings

Every finding here was measured against the live service at
`http://127.0.0.1:8797` or the repository databases on 2026-07-27, not read
from documentation. The command that produced each number is recorded so the
finding can be re-checked or shown live.

Severity is judged by one question: **does this cost Adi the job?**

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

Command:

```bash
for d in 2026-07-05 ... 2026-07-21; do
  curl -s "http://127.0.0.1:8797/api/insights?audience=investment&date=$d&status=kept"
done  # then count analysis.affected_entities by scope
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
