# Manual Registry Intake

## Goal

Let an operator paste an X profile in the Registry UI and either
run the normal evidence-based screen or admit it directly with an auditable
human-override reason.

## Why / Impact

The Registry is 20% of the case-study rubric, but its canonical onboarding
workflow is currently CLI-only. The operator needs a safe, duplicate-free UI
and API path for adding a known profile during the case-study demo.

## Scope / Non-Goals

### In Scope

- API for `screen` and `direct` X-profile intake.
- Existing-profile detection, profile evidence collection, structural kind
  resolution, Registry admission/rejection, and durable audit provenance.
- Inline Registry UI with explicit mode descriptions, direct-admission reason,
  loading/error/success states, and entity refresh.
- Focused backend/frontend tests, production build, docs, and browser proof.

### Out of Scope

- General multi-platform onboarding beyond X.
- Automatic following-snapshot refresh or historical evidence collection after
  admission.
- A feature-specific password or a full user-account system; Adi will protect
  the whole site later.

## Context / Constraints

- Date started: 2026-07-15.
- `fli entity-kinds onboard --handle` is the existing structural lifecycle;
  `registry-evaluation-v3` is the existing combined relevance screen.
- The live case-study site is temporarily a demo. Adi explicitly decided that
  this step should not add a feature-specific password; whole-site access
  control will be enabled separately later.
- `@thsottiaux` already resolves to active Registry entity 612 (`Tibo`); the
  new flow must return the existing entity without duplication or model spend.

## Done When

- [x] An API caller can submit an X URL in `screen` or `direct` mode.
- [x] Screen mode applies current follower/protection gates and the combined
  Registry evaluator; direct mode bypasses the relevance/follower decision but
  retains profile fetch, structural classification, and a mandatory reason.
- [x] Every attempt and result is auditable; existing profiles are idempotent.
- [x] The Registry page exposes a clear inline workflow without adding a third
  peer tab or a feature-specific password.
- [x] Focused tests, `scripts/check-fast.sh`, production build, and live browser
  verification pass.

## Milestones

- [x] Milestone 1 — Intake API and audit contract. Acceptance:
  screen/direct/existing/error behavior is covered by focused tests. Validate:
  `.venv/bin/pytest tests/test_registry_intake.py tests/test_web_registry_intake.py`.
- [x] Milestone 2 — Registry UI workflow. Acceptance: mode choice, reason gate,
  loading, success, and error states build and regressions pass. Validate:
  `npm --prefix frontend test && npm --prefix frontend run build`.
- [x] Milestone 3 — Durable handoff and live proof. Acceptance: docs/build log
  match behavior, fast check passes, and the local served SPA is exercised in
  browser. Validate: `scripts/check-fast.sh` plus browser smoke.

## Execution Rules

- Keep work scoped to the current milestone unless the tracker explicitly expands scope.
- Run validation after each milestone or risky batch and fix failures before advancing.
- Continue working until the scoped project is done or a true blocker requires human input.
- Archive this tracker when all scoped work is complete and validation is acceptable.
- Do not provision Key Vault secrets, change Cloudflare policy, publish, or push.

## Decisions

- Place `Add profile` inside Registry, because intake mutates the Registry and is
  not a third view of the Network.
- Do not add a feature-level password. Whole-site access control will own
  authentication later, per Adi's 2026-07-15 decision.
- Direct admission bypasses relevance and follower-floor rejection, but not a
  protected-account collection failure; an uncollectable source cannot produce
  evidence for the product.
- Existing active profiles return immediately with no provider/model calls.

## Open Questions / Blockers

- None.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Implement intake schema, engine, API, and tests | parent | — |
| done | Build and verify the inline Registry intake UI | parent | — |
| done | Update durable docs, run full validation/browser proof, and archive | parent | — |

## Backlog / Remaining Work

- [x] Implement backend contract and focused tests.
- [x] Implement frontend interaction and regression coverage.
- [x] Update architecture, curation contract, design contract, and build log.
- [x] Run fast checks, production build, and live browser verification.
- [x] Close out and archive this tracker.

## Validation / Test Plan

- `.venv/bin/pytest tests/test_registry_intake.py tests/test_web_registry_intake.py`
- `npm --prefix frontend test`
- `npm --prefix frontend run build`
- `scripts/check-fast.sh`
- Live local `127.0.0.1:8797` browser smoke for existing `@thsottiaux`.

## Progress Log

- 2026-07-15: [IN-PROGRESS] Created the project tracker after confirming both
  API modes, frontend exposure, public-demo authentication needs, and the
  existing `@thsottiaux` Registry identity.
- 2026-07-15: [DONE] Shipped the duplicate-safe screen/direct API, durable
  audit table, inline Registry UI, focused backend/frontend coverage, docs,
  production bundle, and live `$agent-browser` proof. The example returned
  existing entity 612 with zero provider/model tokens; whole-site access will
  own authentication later. Archived after the repo check required one active
  execution owner.
