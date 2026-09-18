# Frontier Lab Intelligence

Tracks frontier AI labs and people, preserves public evidence, and produces
separate Investment and AI Engineering Insights. The case-study intent is a
coherent, defensible end-to-end demonstration, not platform breadth.

## Parked runtime

Adi parked this project on 2026-09-16. Preserve code and research data. Do not
start services, collection, generation, delivery, or production reconciliation
without an explicit resume request. Storage and restart boundaries are in
`docs/references/service-lifecycle.md`; the reserved hostname is intentionally idle.

## Grounding

- For case-study requirements, use `docs/references/case-prompt.md`.
- For conceptual status and remaining proof, use `docs/STATUS.md`.
- For implementation ownership, use `docs/architecture/code-map.md`; system
  boundaries are in `docs/architecture/overview.md`.
- Product/UI changes use `PRODUCT.md` and `DESIGN.md`. The UI is desktop-first.
- Daily briefs and reruns use `$fli-daily-intelligence`; review uses `$fli-review`.
- Project tracking is opt-in: use `$project` only when Adi explicitly invokes it.

## Boundaries and validation

- Preserve raw evidence, schemas, and provenance. Read
  `docs/references/data-lifecycle.md` before moving or deleting data. Do not
  commit `data/raw/`, `data/derived/`, secrets, or private inputs.
- Model calls go through shared LiteLLM. Routing and cost contracts are in
  `docs/references/model-routing.md`; cache diagnostics in
  `docs/references/prompt-caching.md`.
  Cost is telemetry unless Adi sets a cap; parked status still forbids generation.
- Submission, public sharing/uploads, or contacting case-study stakeholders
  needs explicit authorization. Prepare the artifact and validation first.
  Local publication of generated cohorts is distinct from external delivery.
- Keep Dobby/person-memory architecture out of this project.
- Record only material decisions/milestones in the build log under
  `docs/references/build-log.md`. Update conceptual status when its boundary changes.
- Run `scripts/check-fast.sh` before handoff. Its dependency-free parked mode
  does not start services or open preserved research data. Runtime work after
  an authorized resume uses `--require-runtime` and appropriate product proof.
