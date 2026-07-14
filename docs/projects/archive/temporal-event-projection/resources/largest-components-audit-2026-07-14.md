# Largest-component Adversarial Audit — 2026-07-14

## Scope

Manual/data review of the 20 largest components in the final nine-day Event v3
publication:

- Event run:
  `f8999fcd2b674bf46557023ec8dcab2ac4a8bc115fea8158b4b713a276b588a9`
- Feed run:
  `adb2b4949de74a7a3120e71b62366acfcdca0656d0b49c07af10d4e5323f7f96`
- contract: `exact-structural-v5-provider-edges`

## Result

**Passed.** The largest 20 components are coherent provider-linked stories.
No conversation-only merge, unrelated reply branch, duplicate post ownership,
or missing renderable relation was found. The former Greg/OpenAI split is one
69-member component with the provider quote chain intact.

Representative large components include:

| Members | Representative | Subject |
| ---: | --- | --- |
| 118 | Prime Intellect | $130M Series A / Open Superintelligence Stack |
| 117 | Anthropic | global-workspace language-model research |
| 116 | Alexandr Wang | Muse Spark 1.1 launch thread |
| 112 | Daniel Kokotajlo | AI 2027 follow-up thesis |
| 90 | xAI | Grok 4.5 coding/agent launch |
| 84 | Fink | Muse Spark 1.1 release thread |
| 69 | OpenAI | GPT-5.6 Sol/Terra/Luna announcement |
| 64 | Claude | Fable 5 access extension |
| 57 | OpenAI | GPT-Live launch |
| 50 | Sakana AI | AI Picbreeder experiment |

The top 20 range from 42 to 118 members. All are held together by quote,
retweet, or explicit reply-parent links. Conversation IDs are not part of the
component graph.

## Specific Regression

The OpenAI launch component is event
`fc976363e42eb81652e4967aa0acf6a5f7ad46275ef423d2d9258f3bb68d8a16`.
It contains:

- OpenAI root `2074704958419792299`;
- Greg Brockman quote `2074707927844446527`;
- Ben Hylak quote-of-quote `2074709406428913753`.

The links are Greg → OpenAI and Ben → Greg. None of these posts appears as a
competing top-level envelope in the same projection.

## Long-running Components

The Anthropic global-workspace event is active on seven days. Another event is
active on six days, and three are active on five days. Daily API projection
shows one cutoff-local cumulative revision per active day; weekly output owns
each event only once through week-end.

## Machine Checks Supporting the Review

The final full-corpus audit additionally asserts:

- one event owner per provider-qualified post per projection;
- stored member/link counts equal row counts;
- every normalized relation is represented by one Event link;
- relation endpoints cannot be split across renderable components;
- daily and weekly event IDs are unique;
- no member, embedded item, or relation is disclosed after the cutoff;
- independent repeat builds have identical semantic fingerprints.

This bounded review does not claim semantic equivalence between unrelated posts.
Semantic/topic clustering remains a separate future layer.
