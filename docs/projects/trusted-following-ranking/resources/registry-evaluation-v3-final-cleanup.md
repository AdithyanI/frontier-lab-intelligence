# Registry Evaluation v3 — Final Cleanup

Date: 2026-07-12

## Decision

Stop treating a missing X bio or a quiet recent feed as evidence that a person
is outside the Registry. For the 192 GPT-5.4-mini person-removal candidates,
v3 first researched missing-bio identities and then evaluated durable Registry
membership separately from recent posting activity.

The final canonical mutation was deliberately narrower than the model output:
an identity was rejected only when both conditions held:

1. the v3 evaluator returned `remove`; and
2. the accepted `entity-overlap-v2` snapshot placed the identity in the bottom
   decile of active Registry source support (79 or fewer source entities).

Rejection uses `entity_registry_rejections`. It does not delete the entity,
channel, cached posts, or graph evidence, and can be reversed with
`registry.clear_rejection`.

## Run

- Artifact: `data/derived/registry-evaluation/person-remove-identity-v3-gpt54mini-high-2026-07-12.db`
- Cohort: 192 prior GPT-5.4-mini person-removal candidates
- Final evaluator: GPT-5.4-mini, high reasoning, prompt v3
- Missing-bio research: required hosted web search; 108 complete and 2 failed
- Final evaluation: 190 complete and 2 held out
- Decisions: 157 keep, 21 remove, 12 review
- Identity research: 4,066,225 input tokens, 521,216 cached tokens, 755,575
  output tokens, 1,076 hosted-search actions, and `$6.1166097` stored-result
  proxy cost
- Final evaluation: 1,761,927 input tokens, 971,520 cached tokens, 126,120
  output tokens, 20 hosted-search actions, and `$1.2583785` stored-result proxy
  cost
- Combined stored-result proxy cost: `$7.3749882`; failed-response or retry
  overhead without a persisted cost header is not included
- Twitter provider requests: zero; the run reused the exact stored post bundles

The two held-out identities were not changed: `@bouzoukipunks` repeatedly hit
the provider content filter, and `@uncatherio` repeatedly returned no usable
structured payload.

## Applied Rejections

| Handle | Trusted source entities | Decision |
| --- | ---: | --- |
| `@cto_junior` | 79 | rejected |
| `@zarazhangrui` | 63 | rejected |
| `@erika_alden_d` | 45 | rejected |
| `@jeremynguyenphd` | 43 | rejected |
| `@jimmykoppel` | 39 | rejected |
| `@vladquant` | 35 | rejected |
| `@tomjaguarpaw` | 24 | rejected |
| `@fkadev` | 20 | rejected |
| `@cmonkey` | 18 | rejected |
| `@danpeguine` | 5 | rejected |

Each row stores the model's reason, the trust-support count and threshold, the
v3 prompt provenance, and the accepted overlap run identifier.

The other 11 v3 removals were retained because their trusted-follow support was
above the bottom decile. This includes `@jeff_weinstein`, `@austen`,
`@justinkan`, `@travisk`, `@shadcn`, and `@erictopol`. Jeff Bezos also remains
active: v3 returned `keep`, and this conservative cleanup does not override a
keep decision merely because an earlier model disagreed.

## Result

The live Registry now contains 2,104 active people, 93 active organizations,
zero unsure or unknown identities, and 23 reason-bearing rejected identities.
This closes the broad cleanup loop. Future ranking work should evaluate the
accepted graph rather than reopen marginal identity-by-identity curation.
