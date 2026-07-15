# Audience Routing v4: Contextual Audit v1

Date: 2026-07-15

## Verdict

GPT-5.4 mini at high reasoning did a good first-pass routing job, but the
current boundary is not yet clean enough to freeze without one small prompt
clarification. The model is strong on obvious research, product, evaluation,
and operational evidence. Its two visible weaknesses are:

1. it is sometimes too strict about specific but unverified Investment
   theses, even though the prompt says attributed reports and forecasts can be
   useful when their epistemic status is preserved; and
2. it applies an inconsistent AI Engineering threshold to temporary model
   access, rate-limit, and usage-cap announcements.

These are boundary-policy problems, not evidence-comprehension failures. No
clear attribution error or invented packet fact appeared in the reviewed
sample.

## Method

- Reviewed 26 packets from the 74 unique events in the 90-row, nine-day run.
- Stratified the sample across all four outcomes: seven `both`, five
  Engineering-only, six Investment-only, and eight `neither` packets.
- Included clear positives, single-audience decisions, hard negatives,
  repeated announcement types, and likely boundary cases.
- Compared the exact stored packet sources with both audience labels and both
  reasons. This was a contextual reviewer pass, not a randomized or blind
  accuracy study, so the counts below are directional rather than a population
  accuracy estimate.

Result:

| Review outcome | Packets | Interpretation |
| --- | ---: | --- |
| Clear agreement | 21 | Label and reason follow the approved audience standard. |
| Boundary unclear/inconsistent | 3 | A stable product-policy rule is missing. |
| Likely disagreement | 2 | Investment appears to be a false negative under the current prompt. |

## What worked well

### Strong evidence grounding

- The SWE-Bench Pro audit was correctly routed to both audiences: the reason
  cited the supplied 30% broken-task estimate, concrete benchmark failure
  modes, and the consequences for technical evaluation and investor diligence.
- GPT-Live was correctly routed to both audiences from the full artifact, not
  the short launch post. The reasons used the supplied full-duplex design,
  delegation behavior, evals, adoption, and rollout facts.
- Perplexity's Grok orchestrator announcement was correctly routed to both:
  specific WANDR performance and half-Opus-cost claims for Engineering, and
  product availability plus competitive economics for Investment.
- The Fable-assisted native Command & Conquer port was correctly
  Engineering-only. It contained a concrete implementation result but no
  supplied commercial consequence.
- The proprietary-data packet was correctly Investment-only. The model used a
  reaction author's specific commercial practice—trading model access for
  aerial imagery and teleoperation traces—as a data-moat signal without
  transferring that claim to the root author.
- Pure praise such as “Fable is so insanely good” was correctly rejected for
  both audiences.

### Good attribution and epistemic language

The reviewed reasons generally distinguish first-party announcements,
reported results, reactions, anecdotes, claims, and forecasts. They use terms
such as “reports,” “claims,” “anecdotal,” and “if true” rather than silently
turning reactions into established facts.

### Concise reasons

Across all 90 rows, Engineering reasons average 44.3 words and range from 33
to 52; Investment reasons average 43.6 words and range from 34 to 54. That is
close to the requested 40–50-word guidance without requiring schema
truncation.

### Stable repeated-event behavior

The 90 rows contain 74 unique event IDs and 15 events repeated on later Feed
days. All 15 repeated events kept the same Engineering/Investment label pair;
there were zero repeated-event label conflicts.

## Likely disagreements

### Sam Altman's net-job-creation thesis — Investment false negative

Event `f31875369dcc16bd19e9a618ef05f166c6c9959e2d57658d8f28a2040a61cddd`
was routed to neither audience on July 11 and July 12. The model rejected the
Investment case because it was unquantified and supported by hiring anecdotes.

Under the approved prompt, this should probably be Investment-relevant. It is
an attributed frontier-lab executive thesis about labor substitution and AI
adoption, accompanied by concrete—but still anecdotal—claims about hiring at
OpenAI, Anthropic, and Databricks. The right response is to preserve that weak
epistemic status, not require the packet to prove the thesis before routing it.

### Uber autonomous-vehicle policy allegation — Investment false negative

The July 12 rank-8 packet was routed to neither audience. It specifically
alleges that Uber wants autonomous-vehicle services to retain human drivers
for 85% of rides. That is unverified in the packet, but it is an attributed,
company-specific policy claim with an identifiable competitive and regulatory
consequence.

The prompt explicitly allows specific unverified reports when they are
described as such. Investment should probably be relevant with a reason such
as: this is an unverified allegation worth monitoring, not evidence that the
policy exists or will be adopted.

In both disagreements, the model added a stronger verification requirement
than the prompt intended.

## Boundary inconsistency: access and rate limits

Closely related packets received materially different Engineering treatment:

- July 7: temporary Claude Fable access extension — neither.
- July 10: temporary ChatGPT Work/Codex resets — neither.
- July 12: Claude Fable extension plus 50% higher Claude Code weekly limits —
  both.
- July 12: removed Codex/ChatGPT Work five-hour cap, promised efficiency
  improvement, and 6M active users — Investment-only.
- July 13: continued GPT-5.6 inclusion in paid subscriptions — neither.
- July 13: 7M active users — Investment-only.

The Investment distinctions are mostly defensible: quantified adoption,
explicit limit changes, or a supported competitive consequence can matter,
while a celebratory reset usually cannot. The Engineering distinction is less
stable. The Claude reason treats entitlement and rate limits as technical
capacity-planning evidence, while the more detailed Codex packet is rejected
for lacking reproducible technical information.

Recommended rule:

> For AI Engineering, model availability, subscription entitlement, temporary
> resets, and usage limits are not sufficient by themselves. Mark them
> relevant only when the packet supplies a persistent operational constraint or
> a measurable effect on cost, reliability, throughput, reproducibility, or
> system behavior that a technical team could act on.

This should be added as one clarification, then tested only on the few boundary
packets before any broad rerun.

## Upstream packet-quality issue

The July 6 Claude Code history packet was correctly routed to neither based on
the supplied evidence, but the linked Anthropic artifact had been extracted as
blocks of `████` characters. The reason explicitly noticed that the article was
effectively redacted.

This is not a routing-model error. It is an artifact-extraction failure that
hides what is probably the most substantive part of the packet. The shared
artifact boundary now rejects a body before successful text-snapshot creation
when its visible characters are at least 90% exact extraction placeholders
(`█` or the Unicode replacement character). The known Claude Code fetch was
corrected from `success` to terminal
`extraction_placeholder_content`; its immutable raw response remains stored.
A scan of the remaining 880 successful text snapshots found zero violations.

The rule intentionally does not attempt to detect arbitrary gibberish, shell
pages, poor prose, code, foreign languages, or suspicious text. Those remain in
the packet until a separate evidence-readiness contract is justified by real
failures.

## Recommendation

Keep GPT-5.4 mini at high reasoning. Do not move to xhigh and do not redesign
the schema. Make one narrow prompt revision covering:

1. specific attributed claims, forecasts, and allegations may be
   Investment-relevant without verification when the reason clearly preserves
   their epistemic status; and
2. temporary access/entitlement/rate-limit changes are not automatically AI
   Engineering evidence.

Then rerun only the two likely false negatives and the three access/rate-limit
boundary cases. If those move coherently without weakening the clear
negatives, the routing boundary is good enough to freeze before Insight
generation.
