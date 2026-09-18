---
name: fli-daily-intelligence
description: Generate, rerun, inspect, or debug dated Frontier Lab Intelligence briefs for Investment or AI Engineering, including the company packet used for Investment analysis. Respect the repo's parked/resume boundary.
---

# FLI Daily Intelligence

The model owns judgment; repository code owns evidence, schema, persistence,
and reader URLs. Investment and AI Engineering have separate generators and
publication stores over the same frozen Development lineage.

Check the repository's parked state before running anything. An inspection or
maintenance request does not authorize collection, model calls, or a service restart.

## Find the current contract

- `src/fli/insights/cli.py` exposes `fli insights contract` and `summary`.
  Use their current output for schema/model identity rather than a copied version.
- Repo `docs/references/insight-refresh.md` owns cohort selection, dry-run/run
  commands, atomic publication, retries, and reader verification. Use the
  requested date range/audience; a single-rank diagnostic is not a complete day.
- Investment reads `docs/references/company-memos.json` through
  `src/fli/insights/company_context.py`; Engineering reads
  `docs/references/aion-surfaces.json`.
- The skill's `references/bit-investment-context.json` preserves attributed BIT
  background. Analyst context is not BIT's thesis or proof that a Development
  affects a company. Follow the source ledger of the current company packet.

After an authorized run, prove the published cohort, not just stored rows.
Partial results cannot replace a complete publication; retries may repeat paid
calls. Preserve traces and report missing reader/runtime proof. External sends
or sharing require their own explicit authorization.
