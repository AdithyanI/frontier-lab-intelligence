# Audience Routing v7: Targeted Boundary Rerun

Date: 2026-07-15

## Decision

Adi approved two narrow routing rules:

1. A specific attributed Investment thesis, forecast, report, or allegation
   may qualify without independent verification when the reason preserves its
   epistemic status. One material proposition is enough; a complete financial
   case is not required.
2. Temporary model access, subscription entitlement, resets, and usage or rate
   limits do not qualify for AI Engineering by themselves. They need a
   persistent operational constraint or a measured actionable technical
   effect. A promised improvement is not a measured effect.

The exact two-judgment output schema, GPT-5.4-mini model, and high reasoning
effort were unchanged.

## Final v7 Results

| Packet | Engineering | Investment | Interpretation |
| --- | --- | --- | --- |
| Sam Altman net-job-creation thesis | no | yes | Specific labor/adoption thesis with named hiring anecdotes; the reason preserves that it is anecdotal and unverified. |
| Uber 85% human-driver policy allegation | no | yes | Specific attributed policy allegation with identifiable AV-adoption, competition, and margin consequences; explicitly described as unverified. |
| Temporary Claude Fable access extension | no | no | Temporary entitlement plus subjective reactions supplies neither actionable engineering evidence nor a material investment proposition. |
| Fable access plus 50% higher Claude Code limits | no | yes | The temporary limit is not Engineering evidence; the first-party distribution change plus explicitly attributed competitive reactions is useful for Investment monitoring. |
| Removed Codex cap plus 6M active users | no | yes | The promised efficiency improvement is not measured Engineering evidence; 6M active users is a concrete adoption signal for Investment. |

All five final reasons preserve author and epistemic status. None invents a
claim or transfers a reaction author's statement to the primary author.

## Telemetry

- Prompt: `audience-routing-v7`
- Prompt SHA-256:
  `3d35c2d8f31a7cd3823fae2d34d32145b44684d0510cee6e39b57fd7f69e37a6`
- Model / effort: `gpt-5.4-mini` / `high`
- Completed: 5/5; failures: 0
- Input tokens: 12,482
- Cached tokens: 7,168 (57.43%); four of five requests hit the prefix cache
- Output tokens: 4,700
- Proxy-reported cost: $0.0256731

The first v5 and v6 attempts were useful calibration evidence but were not
accepted: v5 still rejected the labor thesis and treated a promised efficiency
change as measured; v6 fixed Engineering but still imposed a complete-financial
case on Investment. v7 made the two approved boundary decisions prominent and
passed all five targeted cases coherently.
