# Unsure Entity Enrichment — Learnings

- Structural kind, relevance, and rejection are different decisions. Keeping
  them in separate persisted states prevented later cleanup from rewriting
  classifier provenance.
- A deterministic evidence ladder—profile, authored posts, then one bounded
  web escalation—was easier to test and defend than a general research agent.
- Protected-account checks belong before inference. They save spend and produce
  a truthful reason-bearing outcome.
- Resumability needs stable prompt/model/evidence identities and per-entity
  commits; otherwise bulk retries duplicate paid calls.
- Consulted-source volume is not evidence quality. A successful search can
  still cite a weaker secondary source, so safe abstention remains a valid
  final outcome.
- The main harness gap encountered was not model capability but provider
  response normalization. Centralizing translated Responses parsing kept that
  complexity out of individual pipeline stages.
