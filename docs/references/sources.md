# Sources

Provenance for factual/company/market claims used in this case study. Add an
entry whenever a claim in the write-up depends on an external source.

| Claim | Source | Retrieved | Notes |
| --- | --- | --- | --- |
| smol.ai/AI News ingestion scale (~550 X accounts, 24 Discords, 12 subreddits), denominator disclosure, "not much happened today" issues | buttondown.com/ainews issue archives + sitemap | 2026-07-08 | Research-agent report; issue headers disclose counts per day |
| smol.ai tagging pipeline: gpt-4.1-mini + structured outputs + controlled vocabularies | github.com/smol-ai/ainews-web-2025 (`oneoffs/process-emails.ts`, `oneoffs/preferredTags.ts`) | 2026-07-08 | Public code; reference pattern for our extraction stage |
| Digg 2026 pivot to AI-signal aggregator tracking top 1,000 AI voices via influence cascades | techcrunch.com/2026/05/11/digg-tries-again-this-time-as-an-ai-news-aggregator/ | 2026-07-08 | Also Kevin Rose X threads |
| Digg community-voting phase failed to bots ("votes couldn't be trusted") | techcrunch.com/2026/03/13/digg-lays-off-staff-and-shuts-down-app-as-company-retools/ | 2026-07-08 | Anti-pattern evidence for no-voting design |
| Techmeme editorial pyramid (algorithm proposes, editors dispose) | techmeme.com/about | 2026-07-08 | Convergent human-in-the-loop pattern |
| HN ranking gravity formula `(P−1)/(T+2)^1.8` with multiplicative penalties | medium.com/hacking-and-gonzo/how-hacker-news-ranking-algorithm-works-1d9b0cf2c08d | 2026-07-08 | Time-decay reference for freshness input |
| Market gaps: no researcher-move-as-signal product; no persona re-scoring product | Landscape audit across Zeta Alpha, CB Insights, Emergent Mind, Crunchbase, Ben's Bites, TLDR | 2026-07-08 | Research-agent survey; differentiation claims in architecture doc |
| Digg top-1000 AI voices list: no public methodology (no about/FAQ/methodology page as of 2026-07-08); TechCrunch reports algorithmic ranking via real-time X engagement cascades, no evidence of hand-curation | techcrunch.com/2026/05/11/digg-tries-again-this-time-as-an-ai-news-aggregator/ + x.com/kevinrose/status/2052423288878735744 | 2026-07-08 | Corrects earlier "hand-curated" inference; research sub-agent verified 404s on digg.com/about, /faq, /methodology |
| X API pricing is pay-per-use credits (no subscription): posts $0.005/read, users $0.01/read, follows $0.01/user returned; est. full case-study X ingestion ~$60-80 | docs.x.com/x-api/getting-started/pricing | 2026-07-08 | Replaces stale Basic-$200/mo tier info; 20% back as xAI credits |
