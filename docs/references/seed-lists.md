# AI People Seed Lists

**Created:** 2026-07-08  
**Updated:** 2026-07-08 (second pass — public X list URL discovery via third-party pages; membership not verified on-platform)  
**Purpose:** Seed sources for Frontier Lab Intelligence people registry (researchers, builders, founders, frontier lab employees). Broad lists preferred — filter downstream to target labs (OpenAI, Anthropic, Google DeepMind, Meta AI, xAI, Mistral, DeepSeek, Qwen + general high-signal AI).  
**Source:** Live web + X searches (Grok tools). No hallucinations of membership.  
**Usage:** Extract handles/names, dedupe, enrich with affiliation/role/GitHub/arXiv. Prefer X Lists and GitHub files for direct handles.  
**Discovery note:** `x.com/i/lists/...` pages are login/JS-gated from here — URLs and curators verified via linking pages (GitHub, blogs, newsletters); sample handles only when the linker names them.

## X Lists

**Aldo Cortesi — AI Anthropic Staff**  
- URL: https://x.com/i/lists/1892848970994766018  
- Type: X List  
- Why useful: Lab-specific staff list for Anthropic; this is cleaner than broad "AI people" lists because nearly every member should be a candidate or validation target for one frontier lab.  
- Samples: samples not verified from full member export; Grok/X probes surfaced Anthropic staff examples from posts/bios, but full list membership still needs X API/export or manual inspection.

**Claude Code / Anthropic builders**  
- URL: https://x.com/i/lists/2034354907646476299  
- Type: X List  
- Why useful: Focused list around Claude Code and Anthropic-adjacent builders/engineers; good for the "layer below famous leaders" technical-builder slice.  
- Samples: samples not verified from full member export.

**swyx AI people / researchers list**  
- URL: https://x.com/i/lists/1585430245762441216  
- Type: X List  
- Why useful: Curated by @swyx (Smol AI / Latent Space); actively used by smol.ai AINews to monitor ~500+ high-signal AI accounts for news and research aggregation.  
- Samples: samples not verified (public list; associated in references with frontier researchers/builders)

**Scobleizer AI Founders #1**  
- URL: https://x.com/i/lists/1744564719309279599  
- Type: X List  
- Why useful: Large curated collection of AI company founders and leaders by long-time tech list curator with thousands of AI entries across lists.  
- Samples: samples not verified

**Scobleizer AI Founders #2**  
- URL: https://x.com/i/lists/1828820239175590166  
- Type: X List  
- Why useful: Follow-up AI founders/leaders list.  
- Samples: samples not verified

**Scobleizer AI Newsmakers**  
- URL: https://x.com/i/lists/1953536336675365173  
- Type: X List  
- Why useful: Hand-picked high-signal AI/tech newsmakers, leaders, and researchers (frequently referenced by Scobleizer and others).  
- Samples: samples not verified

**llm-tracker AI Twitter list**  
- URL: https://x.com/i/lists/1633321011394510848  
- Type: X List  
- Why useful: Curator's dedicated "firehose" list for staying on top of AI news, research, and builders (includes JP variant).  
- Samples: samples not verified

**OpenAI employees list**  
- URL: https://x.com/i/lists/1639070776178475011  
- Type: X List  
- Why useful: Direct OpenAI employee targeting; useful if still maintained, but should be checked carefully for stale memberships.  
- Samples: samples not verified.

**Simplescraper AI list**  
- URL: https://twitter.com/i/lists/1678688265367429122  
- Type: X List  
- Why useful: Public AI-focused list referenced in scraping/monitoring tooling contexts.  
- Samples: samples not verified

**Scobleizer AI/ML (general)**  
- URL: https://x.com/i/lists/952969346518720512  
- Type: X List  
- Why useful: Broad Scoble-curated list of people and companies in AI/ML; indexed in securibee/Awesome-Twitter-Lists.  
- Samples: samples not verified

**Altryne AI, AiArt, Generative**  
- URL: https://x.com/i/lists/1318967584721690626  
- Type: X List  
- Why useful: Curated by @altryne; builders and promoters of generative AI tools/models — useful for builder-layer discovery beyond pure research.  
- Samples: samples not verified

**llm-tracker JP AI Twitter list**  
- URL: https://x.com/i/lists/1738064886427734518  
- Type: X List  
- Why useful: AUGMXNT / llm-tracker companion list for Japan AI scene; regional coverage often missing from Western lists.  
- Samples: samples not verified

**Anne T Griffin — Dose of AI**  
- URL: https://x.com/i/lists/1798016427745571174  
- Type: X List  
- Why useful: Mix of leaders building with AI and AI product leaders; disclosed on annetgriffin.com/ai-resources.  
- Samples: samples not verified

**Łukasz Wróbel — AI Experts**  
- URL: https://x.com/i/lists/1613128091437604864  
- Type: X List  
- Why useful: @lukaszwrobel; 500+ individual AI experts curated over several years (people only, not tools).  
- Samples: samples not verified

**swyx ai-notes Researchers/Developers sub-list**  
- URL: https://x.com/i/lists/1713824630241202630  
- Type: X List  
- Why useful: Linked from swyxio/ai-notes README under Researchers/Developers alongside handles like @nisten and @far__el; owner not confirmed from linker.  
- Samples: samples not verified

**「AI 精选」 (AI curated picks)**  
- URL: https://x.com/i/lists/2021198996157710621  
- Type: X List  
- Why useful: Recommended as a high-quality AI content source in vigorX777/x-ai-topic-selector tooling docs.  
- Samples: samples not verified

**securibee/Awesome-Twitter-Lists (AI/ML index)**  
- URL: https://github.com/securibee/Awesome-Twitter-Lists  
- Type: other (meta-index)  
- Why useful: Curated index of public X lists including AI/ML entries (swyx, Scoble, Altryne); good discovery starting point, not a list itself.  
- Samples: @swyx list 1585430245762441216, @Scobleizer 952969346518720512, @altryne 1318967584721690626

## GitHub Files

**smol-ai / AINews preferred tags (`prefPeople`)**  
- URL: https://github.com/smol-ai/ainews-web-2025/blob/main/oneoffs/preferredTags.ts  
- Raw URL: https://raw.githubusercontent.com/smol-ai/ainews-web-2025/main/oneoffs/preferredTags.ts  
- Type: GitHub file  
- Why useful: Machine-readable preferred people list used by smol.ai/AI News tagging; small but very clean source of high-signal AI X handles.  
- Samples: swyx, bindureddy, kevinweil, karpathy, fchollet, ylecun, sama, joannejang, sarahookr, _aidan_clark_, danhendrycks

**L3S/twitter-researcher (multiple data files)**  
- URL: https://github.com/L3S/twitter-researcher (data/candidates_matched.tsv, candidates_verified.tsv, seeds.tsv, etc.)  
- Type: GitHub file  
- Why useful: Academic paper dataset with thousands of Twitter screen names matched to real computer science / ML / AI researchers (DBLP-linked, conference seeds).  
- Samples: 01Myers (Michael Myers), 0xcharlie (Charlie Miller), and 9k+ matched candidates (many AI/ML academics)

**CosmoBlk vibe coders & AI builders list**  
- URL: https://github.com/CosmoBlk/bestemaildesigns/blob/main/twitter-lists-vibe-coders-email-experts.md  
- Type: GitHub file  
- Why useful: Explicit structured table of ~100 AI builders / indie / vibe coders with @handles, names, follower counts, and role descriptions.  
- Samples: @swyx (Shawn Wang - Latent Space / smol-ai), other tiered AI-native builders

**lreverchuk Top AI Experts / Best Engineers**  
- URL: https://gist.github.com/lreverchuk/282799677d0a53ff27cec5f678f7c819  
- Type: GitHub gist  
- Why useful: Curated list of prominent AI researchers and engineers (GitHub-focused but maps to X presence); includes roles and affiliations.  
- Samples: Andrej Karpathy (karpathy), François Chollet (fchollet), Soumith Chintala (soumith), Tim Dettmers (timdettmers), Jason Wei (jasonwei20), Harrison Chase (hwchase17)

## Rankings, Articles & Curated Lists

**Om Bharatiya — 100 Best AI Researchers and Engineers to Follow on Twitter/X (2026)**  
- URL: https://www.ombharatiya.com/blog/100-ai-voices-reference  
- Type: ranking / article  
- Why useful: High-quality editorial curation of 100 credible voices, strictly filtered for signal (researchers, founders, engineers, professors, safety, investors, journalists). No anons or marketing.  
- Samples: Andrej Karpathy, Ilya Sutskever, Demis Hassabis, Jim Fan, Lilian Weng, Sebastian Raschka, Ian Goodfellow, Jason Wei, Hyung Won Chung, Percy Liang, Sam Altman, Dario Amodei, Greg Brockman, Yann LeCun, Andrew Ng, Geoffrey Hinton, François Chollet, Chip Huyen, Simon Willison, swyx, Timnit Gebru, Nathan Benaich, Jack Clark, Cade Metz, Karen Hao, Will Knight

**Feedspot Top 100 AI Influencers (2026)**  
- URL: https://x.feedspot.com/artificial_intelligence_twitter_influencers/  
- Type: ranking  
- Why useful: Ranked list with explicit verified X handles + short bios. Easy to scrape or copy. Companion ML influencers page available.  
- Samples: @lexfridman, @sama, @karpathy, @AndrewYNg, @kaifulee, @ID_AA_Carmack, @ylecun, @drfeifei, @gdb, @fchollet, @rowancheung, @Scobleizer, @geoffreyhinton, @demishassabis, @jeffdean, @goodfellow_ian, @soumithchintala, @jeremyphoward, @GaryMarcus, @timnitgebru, @oriolvinyalsml

**Reddit r/MachineLearning — "genuinely substantial ML/AI" recommendations**  
- URL: https://www.reddit.com/r/MachineLearning/comments/1ko64s6/d_who_do_you_all_follow_for_genuinely_substantial/  
- Type: other (community list)  
- Why useful: Community-vetted recommendations focused on real research and technical depth rather than hype.  
- Samples: Sebastian Raschka, Yannic Kilcher, Maxime Labonne, Chip Huyen, François Chollet, Frank Nielsen

**Digg Tech / AI Rankings (X social graph)**  
- URL: https://digg.com/tech/x/rankings  
- Type: ranking  
- Why useful: Algorithmic rankings of people shaping AI/tech, built from ~9 million X follow relationships (social graph influence).  
- Samples: samples not extracted in full (includes prominent researchers and leaders such as Karpathy, Schulman per coverage)

**Inline X post curated lists (multiple "AI founders/builders to follow")**  
- URLs: Various recent posts (e.g. from @ai_explorer25, @anshumanjazz, @drq_ai)  
- Type: article / X post list  
- Why useful: Fresh, repeated high-signal shortlists of frontier-relevant individuals (founders + builders + researchers).  
- Samples: @sama, @AravSrinivas, @karpathy, @darioamodei, @demishassabis, @hwchase17, @AndrewYNg, @jeremyphoward, @DrJimFan, @natfriedman, @swyx, @fchollet, @rasbt, @simonw, @_jasonwei, @omarsar0, @adcock_brett, @levelsio, @ilyasut, @maximelabonne, @chipro, @drfeifei, @GaryMarcus

**"36 X (Twitter) AI Accounts to Follow in 2026" (verified frontier set)**  
- URL: https://pasqualepillitteri.it/en/news/3633/ai-x-twitter-accounts-to-follow-2026 (and Stormap variant)  
- Type: article  
- Why useful: Curated set spanning Anthropic, OpenAI, Google, Cursor, xAI, Meta, Mistral + key commentators and builders.  
- Samples: Includes @swyx and core lab-affiliated individuals (full list in article)

**AI-supremacy curated AI Twitter accounts lists**  
- URL: https://www.ai-supremacy.com/p/top-twitter-accounts-on-artificial (and related)  
- Type: article  
- Why useful: Balanced portfolios across researchers, authors, builders, journalists.  
- Samples: Varies by edition; commonly includes core researchers + @sama / @gdb types

**whotofollow.online — X / Twitter most influential AI voices**  
- URL: https://whotofollow.online/en (X/Twitter section)  
- Type: ranking  
- Why useful: Aggregated influential AI voices list.  
- Samples: @karpathy, @ylecun and similar high-signal names

**smol.ai / AINews (list usage + disclosures)**  
- URL: https://news.smol.ai/ (uses the swyx list above)  
- Type: newsletter / other  
- Why useful: Publicly discloses monitoring scale and the exact X list used for AI voice ingestion.  
- Samples: Not a standalone list but directly references/uses https://x.com/i/lists/1585430245762441216

## Other / Supporting

**Scobleizer full lists collection**  
- URL: https://x.com/scobleizer/lists  
- Type: X List collection  
- Why useful: Claims 50,000+ AI people across  multiple specialized lists (Founders, People, Newsmakers, etc.).  
- Samples: samples not verified

**L3S seeds and academic conference Twitter seeds**  
- URL: Same repo as above (data/seeds.tsv)  
- Type: GitHub file  
- Why useful: Early seed set of conference-associated accounts for researcher discovery.  
- Samples: Conference org accounts (e.g. CVPR, NeurIPS-related)

**Regional / lab-adjacent threads (e.g. Singaporean AI researchers by @YiTayML)**  
- Type: article / X thread  
- Why useful: Surfaces high-signal regional researchers that often cross into frontier work.  
- Samples: Various Singaporean AI researchers (thread-specific)

## Top 5 Sources to Extract First

1. **smol.ai preferred tags** (https://github.com/smol-ai/ainews-web-2025/blob/main/oneoffs/preferredTags.ts) — smallest clean machine-readable handle seed; extract first to prove the pipeline.
2. **swyx X list** (https://x.com/i/lists/1585430245762441216) — broad high-signal AI people list already used in production news workflows.
3. **Aldo Cortesi Anthropic staff list** (https://x.com/i/lists/1892848970994766018) — best lab-specific seed found so far; use for Anthropic registry depth.
4. **Digg Tech / AI Rankings** (https://digg.com/tech/x/rankings) — graph-derived ranked people/source signal with visible handles and bios.
5. **Scobleizer AI Newsmakers / Founders lists** (1953536336675365173 and 1744564719309279599) — large but noisier expansion set for xAI/founders/builders.

**Next steps notes (for project):**  
- Clone or curl raw GitHub files where possible for automation.  
- For X lists, use list member tools/APIs if budget allows (or manual export via X Pro / third-party).  
- Cross-reference extracted names against lab affiliations (papers, LinkedIn, company about pages).  
- Record actual extraction results and spend in working-log.md.  
- Add durable provenance to sources.md when using specific claims from these.

All entries compiled from live tool results on 2026-07-08. X list URLs from the second pass (2026-07-08) added above; broad lists retained intentionally.
