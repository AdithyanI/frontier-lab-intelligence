# Network Source Architecture — Problem Statement

Date: 2026-07-14  
Status: frozen pre-change baseline; decision implemented.

The counts below preserve the state that motivated the audit. The accepted
decision, refreshed counts, and comparison evidence are in
`architecture-decision.md`.

## The Exact Problem

Frontier Lab Intelligence needs a defensible answer to two questions that are
currently too easy to confuse:

1. **Who should the product monitor?**
2. **How should those monitored identities be described, compared, or
   prioritized?**

The current active Registry contains 2,197 identities: 2,104 people and 93
organizations. It was assembled from multiple broad candidate sources and then
subjected to structural classification, identity resolution, relevance
screening, reviewed organization coverage, and reversible rejection. It is not
random, but it has not been proven to be the best possible 500, 1,000, or
2,197-source watchlist.

Those active identities serve two current functions:

- their X accounts form the daily collection cohort; and
- their outgoing X follows form the screened population whose aggregate
  behavior produces network-support evidence.

The immutable following snapshot contains 2,219 complete source accounts,
2,197 distinct voting entities, 2,456,305 directed edges, and 463,180 target X
accounts. Each voting Registry entity contributes at most one vote to a target,
even if that source entity owns several X accounts. Adi has explicitly accepted
this flat one-entity/one-vote rule for the present review.

The current Registry UI's `Network rank` does **not** rank an identity only
against the 2,197 active Registry identities. It projects the best global
position of any owned X account from the 463,180-target discovery ranking. For
multi-channel organizations, the projection selects the best account rather
than unioning the distinct Registry identities supporting any official channel.
The displayed ordinal can therefore be both unintuitive in scope and incomplete
as an entity-level aggregation.

At the same time, a request such as “keep the best 1,000” is not yet well
defined. Selecting the top 1,000 by the same cohort's follow support and then
claiming that support proves they are the best sources would be circular. A
clean numerical cutoff can also discard quiet but important first-hand
researchers, specialists, or official sources that publish intermittently.

The architectural blind spot to audit is therefore:

> The system has strong identity, curation, collection, and follow evidence,
> but has not yet defined and validated the boundaries between monitored
> membership, network recognition, source role, operational priority, and
> observed information yield.

## Known Facts, Not Conclusions

| Fact | Current value | Meaning |
| --- | ---: | --- |
| Canonical identities | 2,220 | Includes active and reversible rejected records. |
| Active people | 2,104 | Structurally people and currently admitted. |
| Active organizations | 93 | Structurally organizations and currently admitted. |
| Active monitored identities | 2,197 | Current Registry attention/collection population. |
| Rejected identities | 23 | Preserved, reason-bearing, inactive records. |
| Latest daily X-account cohort | 2,234 | Accounts, not identities; organizations may own several. |
| Complete following sources | 2,219 | Accessible/complete source accounts in the immutable snapshot. |
| Distinct voting entities | 2,197 | Entity-deduplicated screened sources. |
| Following edges | 2,456,305 | Raw directed source-account to target-account evidence. |
| Distinct target accounts | 463,180 | Discovery universe, not the monitored Registry. |
| Active identities posting in the measured seven-day Feed window | 1,309 | Activity evidence only; quiet does not mean irrelevant. |

These facts establish scale and current behavior. They do not prove that the
cohort is optimal, that centrality equals source quality, or that organizations
should receive a blanket advantage.

## Concepts That Must Be Separated

### Registry membership

Whether an identity is sufficiently relevant and collectable to remain in the
screened identity register. This is an admission state, not a rank.

### Monitoring cohort

Which admitted identities are actively collected for public evidence. It may
equal the active Registry, but that equality must be an explicit contract, not
an accident.

### Network support

How many distinct eligible Registry entities follow a target. This is an
explainable recognition/attention feature. It does not establish importance,
credibility, activity, or downstream usefulness by itself.

### Source role

Why an identity is authoritative or useful: frontier lab, official research
organization, lab leader, first-hand researcher, evaluator, specialist,
commentator, aggregator, or another explicit role. Structural kind
(`person`/`organization`) is not a role.

### Source priority

An operational policy such as guaranteed primary-source monitoring or a review
tier. If introduced, it must be rule-based, inspectable, and independent from
the descriptive support ordinal.

### Public reach

Observed X followers. It measures audience scale, not trust or source quality.

### Observed information yield

The source's measured contribution to useful, novel, first-hand, cited events
or insights, including unique contributions and noise. This is the most direct
product measure but is currently available only in small evaluated slices.

## Organization-Specific Question

Organizations should not receive an automatic ranking multiplier simply for
being organizations. A generic product or community can be less authoritative
than a first-hand researcher. Conversely, official frontier labs should not be
lost merely because their social-graph position or recent posting frequency is
lower.

The review must compare two explicit mechanisms instead of hiding this concern
inside one number:

1. **Entity-level aggregation:** union all distinct eligible Registry entities
   that follow any official X channel owned by the organization; count one
   source identity once even if it follows several channels.
2. **Role-based policy:** guarantee or tier verified primary sources such as
   frontier labs through an explicit role/admission rule, not a blanket kind
   bonus.

People and organizations can then share the same descriptive network-support
definition while roles determine any separate operational guarantees.

## Questions Every Review Must Answer

1. What exact product job should network support perform?
2. Is the current broad monitored cohort defensible for recall, and what
   evidence would justify shrinking or tiering it?
3. Which candidate-source biases came from the original lists, X-only focus,
   follower floor, English-language ecosystem, and previous cleanup?
4. Should Registry membership, daily collection, amplification voting, and UI
   display use the same cohort or separate explicit cohorts?
5. How should source-side and target-side multi-account entities be
   deduplicated?
6. Should the Registry show a rank within active Registry identities, a global
   discovery rank, raw support, or more than one clearly scoped value?
7. What role taxonomy, if any, is small enough to be trustworthy and useful?
8. How should official frontier labs and other primary sources receive
   guaranteed treatment without making every organization “better”?
9. What real-data evaluation can distinguish graph popularity from actual
   information value without circular labels?
10. What is the strongest case for leaving the current architecture unchanged?

## Required Alternatives

Every synthesis must include at least these baselines:

1. **No semantic change:** retain the broad active Registry, current voting,
   and global discovery support; improve only explanation if the evidence says
   the architecture is already correct.
2. **Entity-scoped descriptive support:** keep broad monitoring and voting,
   union target support across official channels, and rank active Registry
   entities only against active Registry entities. Keep discovery rank in the
   Ranking view.
3. **Explicit source tiers:** retain broad monitoring for recall, add a small
   primary-source/anchor tier with deterministic role evidence, and keep
   support separate from tier.
4. **Bounded core cohort:** use fewer monitored or voting identities only if a
   non-circular real-data evaluation shows comparable coverage with better
   signal density, stability, or operational value.

Reviewers may propose other alternatives, but must retain the current design as
a measured baseline.

## Evaluation Standard

A proposal is not accepted merely because its top names look sensible. The
smallest credible comparison should predeclare and inspect:

- coverage of official frontier labs and known key people;
- first-hand versus commentary/aggregation output;
- unique useful events or cited insights contributed;
- noise and redundancy;
- important omissions and long-tail specialist losses;
- stability across several days or windows;
- sensitivity to the original candidate lists and network-support threshold;
- understandable denominators, ties, missing data, and rejection behavior;
- migration and rollback cost.

Follower count and network support may be inputs or diagnostics, but neither
may be the sole validation label for a cohort selected by the same feature.

## Instructions For Independent Agents

- Read `docs/projects/cited-insights/tasks.md` and this workstream's
  `project-brief.md` first.
- Do not edit the parent `tasks.md`; the parent agent is its single writer.
- Audit before proposing implementation.
- Cite local files, SQL reconciliations, or external primary sources for factual
  claims.
- Explicitly separate evidence, inference, recommendation, and unknowns.
- Challenge the premise. A well-supported no-change recommendation is valid.
- Do not select 500 or 1,000 because it is visually tidy.
- Write durable findings to the assigned topic file beside this document, then
  report that path to the parent agent.

Suggested independent lanes:

- `current-state-audit.md`: code, data, denominators, snapshot freshness, and
  multi-channel semantics.
- `product-architecture-review.md`: concept boundaries, user meaning,
  alternatives, and interview defensibility.
- `adversarial-review.md`: selection bias, circularity, counterexamples, and
  strongest no-change case.
- `evaluation-plan.md`: non-circular measures, cohorts, sampling, labels, and
  decision thresholds.

## Current Safety Boundary

Until the review reaches an accepted decision:

- keep all 2,197 active identities monitored;
- keep the current one-entity/one-vote amplification rule;
- do not add an organization multiplier;
- do not adopt a 500/1,000 cutoff;
- do not reinterpret global discovery position as validated source priority;
- do not mutate the immutable following snapshot;
- do not let this audit silently displace cited-insight delivery work.
