# Entity-kind classification snapshots

Captured from the local production Registry on 2026-07-10 after promoting the completed entity-kind classification run.

- `registry-unsure-overview.png` shows the final distribution across 2,966 identities: 2,639 people, 182 organizations, and 145 unsure. The selected Unsure view makes the classifier's abstention cohort visible.
- `registry-unsure-philschmid.png` shows a grounded abstention example. With only a handle-like name and no observed biography, the model preserves the identity as `unsure` and exposes its short rationale.

The full pass used `gpt-5.6-luna` with medium reasoning through the shared LiteLLM endpoint. Approximate inference cost was $1.459852; no direct Azure OpenAI calls were made.

These files are durable presentation artifacts, not source evidence.
They preserve the classifier state at capture time; a later explicit corpus
cleanup removed `@philschmid` and 38 sub-1,000-follower entities, so the images
are historical rather than the current Registry totals.
