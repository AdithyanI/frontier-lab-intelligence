# BIT Capital Case Study Prompt — Lars

## Source metadata

- Received at: 2026-07-07 16:41 CEST (14:41 UTC)
- Sender: BIT Capital GmbH <career@bitcap.com> (Lars)
- Email/thread/source: Gmail message `19f3d0692e019e93`, thread `19f056ce40383638`, subject "Re: Re: Adithyan <> BIT Capital | Next Step: Interview with Vlad Gheorghe", account adithyan@wisdominanutshell.academy → adi@aipodcast.ing
- Local attachments folder: `docs/references/source-material/` (this repo); original capture also kept in the career tracker.
- Captured by: Dobby, 2026-07-07

## Verbatim prompt

Email body (verbatim):

```text
Hey Adi,

here is now the case study as promised. We would like you to send everything back on the 20th of July to us. Does that work for you?

Let me know if you have any questions and have a nice day!

Best, Lars
```

Full case study PDF (verbatim, canonical copy is the PDF itself):

- PDF: `docs/references/source-material/BIT_Capital-Case_Study-Frontier_Lab_Intelligence.pdf`
- Extracted text: `docs/references/source-material/BIT_Capital-Case_Study-Frontier_Lab_Intelligence.txt`

Case study title: **"Frontier Lab Intelligence" — AI Engineer (m/f/d) · BIT Capital · Take-home case study**

Condensed structure of the PDF (see extracted text for exact wording):

- **Logistics:** deadline in email (2026-07-20); after submission, on-site case discussion with the AI team going deep on design choices, trade-offs, and what you'd build next. €100 budget for APIs/services, reimbursed with receipts; they're interested in *how* it's spent.
- **Context:** BIT's edge depends on staying at the frontier of what labs are doing before it shows in products/stock prices. Frontier-lab people (OpenAI, Anthropic, GDM, Meta, xAI, Mistral, DeepSeek, Qwen, stealth spin-offs) + the labs' official channels broadcast public signal: papers, blogs, GitHub, talks, X, model/system cards. Build the system that tracks this. Before coding: research BIT publicly, understand who would use this and why it matters to the fund.
- **Task — a working system that:** (1) tracks a register of labs + key individuals; (2) ingests and extracts intelligence from what they publish; (3) scores/ranks contributors and insights (the data-science core, justified and reproducible); (4) delivers actionable intelligence as reports + alerts to two internal audiences.
- **AI tools:** "Use any AI coding tools you want. We expect you to, and we'll ask how you worked."
- **Success bar:** not a vibe-coded demo ticking boxes; a system that surfaces genuinely relevant intelligence with good filtering, taste, and detail. Key question: "did this surface something we'd genuinely want to know, and did it keep the noise out?"
- **Two audiences, one shared core:** Investment team (implications, tickers, theses; connect private-lab developments to public-equity landing spots) and AI team (what to adopt/investigate; technical, build-relevant). Tailored last-mile outputs, not two systems.
- **System parts:** 1 frame the problem (who/what to track, how "key" is defined, keeping the register current); 2 ingestion pipeline (heterogeneous scheduled sources, rate limits, dedup, freshness, justified coverage — scoped-well beats broad-badly); 3 register of labs *as first-class entities* + individuals incl. the layer below the obvious names, with entity resolution across X/arXiv/GitHub identities; 4 extraction into structured, attributed, cited insights over a recent window (~3 months suggested), LLM does heavy lifting, every insight traceable to primary source; 5 scoring/rating with data-science rigor — validated against ground truth/human judgment/defensible proxy; "arbitrary weighted sum dressed up as a score is a red flag; a simple model you can defend and have tested is exactly what we want"; 6 signal-vs-noise: the most important part, weighted accordingly; 7 reports (periodic digest, readable in app + exportable PDF) + alerts (push, e.g. Slack/email, to the right audience), cited, per-persona, "actionable = reader knows what it means and what to do"; 8 small web interface (browse register, scored insights + why flagged, past reports, configure tracking — don't over-polish).
- **Prioritization weights (descending):** registry 20% · signal-vs-noise + intelligence quality 20% · scoring/rating rigor + validation 20% · actionable delivery (reports+alerts, two personas, cited) 15% · ingestion pipeline 10% · extraction 10% · web interface 5%. Deliberately ambitious high ceiling; depth in a few sections beats superficial box-ticking.
- **Deliverables:** source code in a Git repo (clear, modular, good primitives; README + locally runnable demo or live deployment); the database (schema + real data); architecture write-up incl. model selection per task + fallbacks; prompts with design rationale; evaluation (extraction quality, hallucination control, scoring validation, ground-truth approach); tokenomics (approx token usage + $ cost per workflow, cost-quality trade-offs); final report (what works, next steps, learnings, and the 3–5 most interesting real insights the system surfaced — "proof that it works"); optional short Loom/video demo.

## Attachments / links

| Item | Type | Local path / URL | Notes |
| --- | --- | --- | --- |
| BIT_Capital-Case_Study-Frontier_Lab_Intelligence.pdf | PDF, 4 pages, 75 KB | `docs/references/source-material/BIT_Capital-Case_Study-Frontier_Lab_Intelligence.pdf` | The full case study; canonical source |
| Extracted text | txt | `docs/references/source-material/BIT_Capital-Case_Study-Frontier_Lab_Intelligence.txt` | pdftotext -layout extraction for agent reading |

## Deadline / timezone

- Deadline: **2026-07-20** ("send everything back on the 20th of July") — Lars asked "Does that work for you?", so the deadline is confirmable/negotiable in reply.
- Timezone: not stated; assume CET/Berlin (BIT is Berlin-based). Treat as end-of-day 2026-07-20 unless clarified.
- Expected timebox, if stated: none stated; ~2 weeks implied by the window. €100 API/services budget (reimbursed with receipts).
- Submission method: not explicitly stated — reply by email implied ("send everything back … to us"). Repo link + write-ups by email is the natural reading. Confirm in reply if needed.

## Constraints / confidentiality

- Is provided material confidential/private? Not stated. Treat the PDF as private-process material: do not publish or share outside this process.
- Are public web sources allowed? Yes — explicitly required ("research BIT Capital using whatever is public"; ingest public papers/blogs/GitHub/X).
- Are LLM/agent tools allowed or expected? Explicitly expected: "Use any AI coding tools you want. We expect you to, and we'll ask how you worked." → keep a build log so the "how you worked" discussion is easy.
- Are dependencies/cloud services allowed? Yes — €100 budget for APIs/services, reimbursable with receipts; they care how it's spent. Live deployment is an accepted demo path.
- Are there restrictions on publishing/pushing/sharing? Not stated. Default: private repo; share access at submission.

## Deliverables

### Required

- Source code in a Git repo: clear, modular, good primitives (ingestion, extraction, scoring, storage, orchestration, delivery); README + locally runnable demo or live deployment.
- The database: schema and real data.
- Architecture write-up: stack + why, model selection per task, fallback strategies.
- Prompts with design rationale.
- Evaluation: extraction quality, hallucination control, scoring validation, ground-truth approach.
- Tokenomics: approx token usage + $ cost per workflow; how cost shaped model choices.
- Final report: what works, what's next, learnings, and the 3–5 most interesting *real* insights the system surfaced.
- Working system covering: register (labs + individuals, entity-resolved, current), ingestion, extraction (structured, attributed, cited), scoring (validated), signal-vs-noise filtering, reports (in-app + PDF export) + alerts (Slack/email push), two persona-tailored outputs, small web interface.

### Optional / nice-to-have

- Short Loom / video demo.
- API/services receipts for reimbursement (up to €100).

## Evaluation criteria

### Explicit criteria from prompt

- Weighted rubric: registry 20% · signal-vs-noise 20% · scoring rigor + validation 20% · actionable delivery 15% · ingestion 10% · extraction 10% · web UI 5%.
- "Did this surface something we'd genuinely want to know, and did it keep the noise out?" — the single most important question.
- Depth in a few sections > superficial completeness across all.
- Scoring must be justified, validated, reproducible; arbitrary weighted sums are an explicit red flag.
- Every insight traceable to primary source; clean citations.
- Persona-tailored outputs from one shared core, not two systems.
- Post-submission on-site discussion: design choices, trade-offs, what to build next, and how AI tools were used while building.
- How the €100 budget was spent.

### Likely implicit BIT criteria

- Investment relevance / alpha or risk signal (connect lab moves to public tickers/theses).
- Source grounding and provenance.
- Evals, monitoring, and failure-mode thinking.
- Human-in-the-loop investment decision boundary.
- Cost/latency/reliability awareness (tokenomics is explicit here).
- Pragmatic shipping and clear reviewer path.
- Agent-native building practice — they will ask *how* Adi worked with AI tools; the workflow itself is being evaluated.

## Unknowns / clarifying questions

Ask only if the answer materially changes the work.

| Question | Why it matters | Ask Lars? yes/no |
| --- | --- | --- |
| Confirm deadline works (he asked "does that work for you?") | Politeness + locks the date | yes — in the reply |
| Submission method (repo link by email? live URL?) | Packaging decision, but answerable by reasonable default | no for now — repo link + docs by email is safe; can confirm in reply naturally |
| Timezone/EOD for 2026-07-20 | Marginal | no — assume EOD Berlin |
| X/Twitter API access is expensive; is scraping/third-party acceptable? | Coverage decision | no — this is exactly the "reason about which sources are worth the effort" judgment they want; decide and justify |

## Working-surface decision

- Classification: **Prototype/code task + hybrid** — full agentic pipeline (signal-extraction/research-agent archetype) with runnable code, DB, web UI, evals, and write-ups.
- Work location: **separate repo `/Users/dobby/GitHub/frontier-lab-intelligence`** (renamed from `bit-capital-case-study-2026` on 2026-07-08) per the default rule (runnable code, dependencies, tests, eval harness, agent pipeline). This Dobby project stays the career/control-plane tracker.
- Reason: runnable code + demo + DB + web UI are explicitly required; the checklist rule mandates a separate implementation repo built from `agent-native-repo-template.md`.

## Historical intake notes

The sections below preserve the initial planning snapshot from 2026-07-08.
They are provenance, not current execution state. For the present system status
and assignment gap, read [`../STATUS.md`](../STATUS.md) and the active
[`audience-insights-v2` tracker](../projects/audience-insights-v2/tasks.md). Do not rebuild
the repository or interpret the `todo` values below as live status.

## Initial first-day execution plan (historical)

1. Reply to Lars: confirm receipt + the 2026-07-20 deadline (Adi approval before send).
2. Re-read PDF + this brief; rebuild `tasks.md` Current Batch from the actual weighted rubric (registry/signal-noise/scoring first, UI last).
3. Create the implementation repo from `agent-native-repo-template.md`; decide stack per `case-study-playbook.md` (Python core; scheduling; SQLite/Postgres; light web UI).
4. Design pass on the top-3 weighted areas before any pipeline code: register schema + entity resolution approach; signal/noise filtering concept; scoring model + validation/ground-truth plan.
5. Start build log (AI-tool usage + budget receipts) from hour one — both are explicitly examined.

## Initial prompt requirements map (historical)

| Prompt requirement | Planned deliverable | Status | Evidence path |
| --- | --- | --- | --- |
| Register of labs + individuals (20%) | Register schema, seed data, entity resolution, currency mechanism | todo | impl repo |
| Signal-vs-noise filtering (20%) | Filtering logic + documented judgment | todo | impl repo |
| Scoring/rating + validation (20%) | Defensible scoring model + ground-truth validation | todo | impl repo |
| Reports + alerts, two personas, cited (15%) | Digest (app + PDF export) + Slack/email alerts, persona-tailored | todo | impl repo |
| Ingestion pipeline (10%) | Scheduled multi-source ingestion, dedup, rate limits | todo | impl repo |
| Extraction into structured cited insights (10%) | LLM extraction with attribution + citations | todo | impl repo |
| Web interface (5%) | Light browse/config UI | todo | impl repo |
| Git repo + README + runnable demo | Repo scaffold + README + demo path | todo | impl repo |
| Database schema + real data | DB with real ingested data | todo | impl repo |
| Architecture write-up (models per task, fallbacks) | `docs/architecture/overview.md` in impl repo | todo | impl repo |
| Prompts + design rationale | Prompt files + rationale doc | todo | impl repo |
| Evaluation (extraction, hallucination, scoring) | Eval harness + write-up | todo | impl repo |
| Tokenomics (usage + $ per workflow) | Cost tracking + write-up | todo | impl repo |
| Final report + 3–5 real surfaced insights | `docs/final-report.md` | todo | impl repo |
| Optional Loom/video demo | decide near submission | todo | — |
| Reply confirming 2026-07-20 deadline | Email reply (Adi-approved) | todo | Gmail thread |
