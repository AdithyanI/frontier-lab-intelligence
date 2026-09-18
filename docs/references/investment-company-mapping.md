# Investment company mapping

A Development is evidence; company research is prior context. Require a
credible causal connection to a company's standing bet instead of matching
on general AI exposure. Attribute BIT's public views only to their recorded
sources; analyst context must remain distinguishable.

## Current authority

- `docs/references/company-memos.json` is the generated company/memo/bet packet.
  `src/fli/insights/company_context.py` validates it and resolves memo-owned
  direction. The skill's BIT background packet is research provenance, not an
  alternate current runtime store.
- `src/fli/insights/investment_agent.py` owns screening, memo retrieval, prompt,
  and result schema. `investment_agent_runs.py` owns validated persistence and
  publication; `fli insights contract` exposes the active contract.
- The model selects a valid company/bet and explains impact. Code resolves bet
  direction. `threshold_met` distinguishes an established threshold from an
  early signal; company weight or prominence cannot manufacture relevance.
- `docs/references/insight-refresh.md` owns dry-run/run and publication proof.
  The repo remains parked until an explicit resume request.

Do not maintain a second output-schema example or a fixed model/version list
here. Use the actual contract and the source-bearing memo packet when changing
or evaluating Investment behavior.

## Research history

[The 28 July design and research snapshot](archive/event-to-company-mapping-2026-07-28.md)
retains the original memo-batch provenance and rationale. Its old schema,
per-company promotion directory, and prospective selector are historical.
