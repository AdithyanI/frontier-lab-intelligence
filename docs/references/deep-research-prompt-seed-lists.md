# Deep-research prompt: bootstrap lists for the people registry

Prompt for an external deep-research tool (ChatGPT/Gemini deep research) to
find curated lists we can bootstrap the registry from. Written 2026-07-08.
Paste results back into the repo when done (see notes at bottom).

---

**Context:** I'm building an intelligence system that tracks frontier AI labs and their key people, for an investment-research use case. The core asset is a "people registry": for each lab, the ~10–30 individuals whose public output (papers, code, posts) actually signals the lab's direction — leadership (CEO, chief scientist), research leads, and prolific individual researchers. For each person I ultimately need: real name, lab affiliation, role, X/Twitter handle, and ideally GitHub username and arXiv author identity. I will build this mapping myself; your job is to find existing curated or ranked lists I can bootstrap candidates from.

**Labs in scope:** OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral AI, xAI, DeepSeek, Alibaba Qwen. (Lists covering "AI in general" are still useful — I'll filter to these labs.)

**Already known (don't re-report, but DO find their details):** Digg AI rankings (digg.com/tech/x/rankings — if you can find how they select people, or an API/JSON endpoint behind the page, report it); the smol.ai / AI News whitelist (if their people-list is in a public GitHub repo like smol-ai/ainews-web-2025, give the exact file path); public X Lists such as x.com/i/lists/1585430245762441216 (identify who owns this list and its member count).

**Find additional sources in these categories:**

1. **Public X Lists about AI researchers/AI voices, whoever maintains them.** For each: list URL, owner account, member count, last activity. Also identify who owns x.com/i/lists/1585430245762441216 and what it contains. Finding these may require searching "site:x.com/i/lists AI researchers" or coverage articles like "best AI Twitter lists".
2. **Editorial rankings:** TIME100 AI (all editions 2023–2026), any Forbes/Fortune/Business Insider AI-people lists, MIT Tech Review Innovators Under 35 (AI category).
3. **Academic/algorithmic rankings:** Semantic Scholar highly-cited AI authors (they have a free public API — report relevant endpoints), Google Scholar top authors in cs.AI/cs.LG/cs.CL, AMiner AI 2000 most influential scholars list (aminer.org — verify it still exists), csrankings.org faculty data.
4. **Conference signals:** NeurIPS/ICML/ICLR award winners, invited speakers, area chairs 2023–2026 — any consolidated lists.
5. **GitHub repos** containing researcher or handle lists: search terms like "AI twitter list", "ML researchers", "llm researchers list", "AI influencers csv/json".
6. **Newsletters/trackers that disclose whom they follow:** AI News (smol.ai), Interconnects (Nathan Lambert), Import AI (Jack Clark), ChinAI, Zvi's newsletter, LessWrong/AF author rankings.
7. **China-lab coverage specifically** (DeepSeek, Qwen are underrepresented in Western lists): any lists of Chinese AI lab researchers with social handles (X or otherwise).
8. **Anything else** ranking AI researchers by citations, influence, followers, or output.

**For every source report:** exact working URL; maintainer; curation method (editorial/algorithmic/community — quote their methodology statement if one exists); person count; whether X handles are included; whether lab affiliations are included; machine-readability (raw HTML / JSON / CSV / API / GitHub file / JS-rendered / login-gated / paywalled); date last updated. Exclude tool/company/resource lists and anything stale (pre-2024) unless historically definitive.

**Output:** a table sorted by usefulness (handles + affiliations + machine-readable + recent first), then per-source extraction notes (e.g. "JSON endpoint at …", "parse the second table on page", "clone repo, file at path …"). Flag anything whose terms of service prohibit scraping. End with the top 5 sources you'd use if you could only pick 5, and why.

---

## Notes

- Results should become a short source inventory in `docs/references/` and
  rows in `docs/references/sources.md` for anything we actually use.
- Do not recreate the old `data/raw/registry-seed/` scratch folder. The next
  useful artifact is a reviewable candidate table derived from `data/fli.db`
  plus any approved external source inventory.
