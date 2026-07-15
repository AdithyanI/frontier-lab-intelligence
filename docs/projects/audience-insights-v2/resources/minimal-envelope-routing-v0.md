# Minimal Envelope Routing v0 — Design Draft

Status: product-design handoff for the next working session. Nothing in this
document is implemented or authorized for model execution yet. Generated
Audience Insights data remains intentionally empty.

## Why this reset exists

The previous Audience Insights pipeline mixed audience extraction with several
later editorial and audit stages. Adi wants to rebuild the product one visible
step at a time from the cleaned Evidence envelope.

The immediate question is narrower:

> Given one complete, correctly attributed Evidence envelope, is there useful
> evidence for AI Engineering, Investment, both, or neither?

Only after answering that question should the system generate an audience
insight.

## Recommended two-stage shape

```text
accepted Feed envelope
  -> one audience-routing audit
       -> AI Engineering: yes / no
       -> Investment: yes / no
  -> one separate extraction call for each yes audience
  -> application-owned exact citation binding
```

Do not add another general relevance gate. Feed already owns `keep` / `drop`.
The Insight stage should use different language so the product does not have
two incompatible meanings of “kept.” Source availability, hashes, and packet
integrity are application checks, not model judgments. A mechanically invalid
packet never reaches the router; every valid packet receives only an audience
route.

The four normal routing outcomes are derived from two independent booleans:

- AI Engineering only;
- Investment only;
- both; or
- neither.

Do not represent these as one mutually exclusive model enum. Independent
booleans make `both` natural and keep the two audience judgments inspectable.

## Stage 1 — Complete-envelope audience router

### Input

The router receives one immutable envelope with every block explicitly
attributed and related to the event:

- root post;
- same-author thread continuations;
- replies and quote-posts, each retaining its own author and relationship;
- accepted canonical artifacts and their full fetched bodies when available;
- runner-owned block ID, source type, author, relation, URL, and source hash.

Replies and quote-posts may supply a useful independently attributed claim.
They must never be flattened into the root author's claim or silently treated
as corroboration. Retweets without new text remain omitted.

Artifacts must come only from the cleaned, audited artifact lineage. In
particular, an artifact discovered in an unrelated reaction must not attach to
the root envelope. Every artifact block needs an explicit verified author when
known; do not expect the model to infer authorship from the root post.

The model does not receive Feed rank, engagement, follower counts, Registry
prominence, or an editorial score.

### Candidate minimal output

This is a discussion draft, not a frozen schema:

```json
{
  "ai_engineering": {
    "useful": true,
    "reason": "One short evidence-grounded reason."
  },
  "investment": {
    "useful": false,
    "reason": "One short evidence-grounded reason."
  }
}
```

The router may reason deeply, but its stored output should stay small and
auditable. It does not write an Insight, select a daily set, rank the event, or
rewrite evidence. The application owns run IDs, event IDs, evidence hashes,
prompt versions, and telemetry; none should be model-generated fields.

### Question to settle together

Should the router also identify candidate evidence block IDs for each audience?
The safer initial default is **no**: let each positive audience extractor see
the same complete packet so a routing hint cannot accidentally hide decisive
evidence. Add block selection only if measured context or quality problems
justify it.

One combined routing call is appropriate for the first version because this is
a bounded multi-label classification task, not shared insight generation. The
prompt must define the two reader standards separately and require two
independent decisions. Before scaling, compare a small sample with separate
single-audience judgments to detect systematic compromise or cross-audience
bias.

## Stage 2 — Audience-specific extraction

Run this only for an audience whose Stage 1 route is `useful: true`.

- AI Engineering and Investment use separate prompts and schemas.
- Each extractor sees the complete immutable packet plus its audience route.
- Each returns at most one Insight for this initial MVP.
- Each may still return no insight when closer extraction shows that the router
  produced a false positive; routing is a cost/attention filter, not authority
  to publish.
- Each Insight chooses one exact supporting quote from one numbered block.
- The application, not the model, binds block ID to source URL, author, hash,
  and character offsets.
- If exact citation binding fails, the result is an extraction failure, not a
  published Insight.

The exact extraction fields are intentionally open for the next session. Start
with the smallest reader-visible result rather than restoring the previous
review/editor/publication schemas.

## First envelope to review

Use this envelope as the first prompt-design example:

```text
56ec1710fbc2f39b18aad549d21b38581a115b5dcf09d9b79dd4522d56bef56d
```

Current facts for 2026-07-12:

- Feed rank is currently #2, but rank must not enter model judgment.
- Root post is Satya Nadella linking to the X Article “The Reverse Information
  Paradox.”
- The cleaned artifact store attaches that full article through the root
  author's lineage.
- The Feed envelope also contains 14 independently authored quote-posts.
- The old extractor packet contained only the root link and article body; the
  revised router proposal would also receive the independently attributed
  reactions.
- The prior packet left the article author empty. The rebuilt packet must
  preserve verified artifact authorship before any model call.

## Next-session sequence

1. Render this exact envelope using the current cleaned artifact and reaction
   data; inspect the block list together.
2. Agree which replies/quotes belong in the complete router packet and verify
   every author/relation.
3. Write the short Stage 1 routing prompt together.
4. Freeze the minimal routing JSON schema.
5. Dry-run only this envelope and inspect the two audience decisions.
6. Agree one minimal extraction schema and prompt per audience.
7. Run this envelope again end to end before trying a full day.

Do not regenerate a day, restore deleted Insight databases, or revive the old
editor/reviewer/publication stages before steps 1–6 are agreed.

## Design audit verdict

The two-stage design is a good simplification with four guardrails:

1. Feed remains the only keep/drop gate.
2. The router returns two independent audience booleans, not one compromise
   label or an Insight.
3. Reaction text may inform routing or become its own attributed claim, but
   reaction-owned links do not enter the root author's artifact lineage.
4. Extraction and exact citation binding remain separate per positive audience.

For the initial envelope, include all reactions already frozen into that Feed
envelope. Do not fetch arbitrary additional X replies and do not introduce a
new top-N reaction ranking yet. Measure packet sizes first; add a deterministic
bound only if real envelopes exceed the model or quality boundary.
