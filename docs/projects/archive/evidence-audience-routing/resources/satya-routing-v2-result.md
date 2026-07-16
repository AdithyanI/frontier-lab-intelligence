# Satya audience-routing v2 result

Status: completed one authorized Luna-medium call on 2026-07-15. No other v2
envelope has been routed.

The exact prompt, cleaned YAML input, cache configuration, schema, and hashes
are preserved in [`satya-routing-v2-attempt.md`](satya-routing-v2-attempt.md).

## Result

```json
{
  "ai_engineering": {
    "relevant": true,
    "reason": "The artifact provides concrete engineering guidance on private evaluations, tenant-boundary learning environments, ownership of traces and adapted weights, model- and orchestration-layer portability, and continuous enterprise learning loops."
  },
  "investment": {
    "relevant": true,
    "reason": "The artifact and reactions present a specific enterprise-AI thesis that data and learning sovereignty will drive build-versus-buy changes, model and harness independence, proprietary platforms, and potentially startup acquisitions, with implications for competitive positioning and AI infrastructure demand."
  }
}
```

## Telemetry

| Field | Value |
| --- | ---: |
| Model | `gpt-5.6-luna` |
| Reasoning effort | `medium` |
| Input tokens | 3,171 |
| Output tokens | 119 |
| Cached tokens | 0 |
| Cache-write tokens | 0 |
| LiteLLM-reported cost | $0.003885 |
| Duration | 4.172 seconds |
| Prompt cache key | `fli:audience-routing:audience-routing-v2:shard-00` |
| Response status | `complete` |

This was the first request with the v2 prefix, so zero cached tokens are
expected. The Azure-backed route also reported zero cache-write tokens, which
means this request alone does not prove that the prefix was written. A second
approved envelope using the same key is required to test for an actual cache
read.

## v1 versus v2

| Measure | v1 flat input | v2 cleaned input | Change |
| --- | ---: | ---: | ---: |
| Input tokens | 4,698 | 3,171 | -1,527 (-32.5%) |
| Output tokens | 210 | 119 | -91 (-43.3%) |
| Reported cost | $0.005958 | $0.003885 | -$0.002073 (-34.8%) |
| Model outcome | Both | Both | unchanged |
| Reactions shown to model | 14 | 8 | -6 |

The v2 Engineering reason is grounded in the authored artifact. The v2
Investment reason uses both the artifact and distinct reactions, explicitly
connecting the thesis to build-versus-buy decisions, portability, proprietary
platforms, acquisitions, and competitive positioning.

## Provenance

- Run database:
  `data/derived/audience-routing/audience-routing-v2-2026-07-12-satya/routing.db`
- Event ID:
  `56ec1710fbc2f39b18aad549d21b38581a115b5dcf09d9b79dd4522d56bef56d`
- Prompt SHA-256:
  `b3fec75f322ce5654a74423f9cfec3d060ee7acdfded935680ee5d5f7fd81ed3`
- Evidence SHA-256:
  `47a7a55e8d2c6adfe05138a32cc56c9c0d18430676664b2fbbd811ab0d5c94fe`
- Input SHA-256:
  `51741123340a42f229adc078e7cd1c437b0c38f1fb07d076934d30a0bc76f6b5`
- SQLite integrity check: `ok`
