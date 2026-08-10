# Design: wire-design-content-review-gate

## Context

`guide-design` (added in v2.1) owns the design-time workflow between `arch-done` and `plan-done`: it consumes improvements, generates `proposal.md` drafts via `generate_full_proposal.py`, prompts the user for confirmation (per ADR-0025 §D1), then calls `approve_proposal.sh` to land the change under `openspec/changes/<name>/`.

ADR-0025 §D4 mandates a two-tier content review at approve time:

- **improvements 层**: review `improvements/<name>.md` for five-section completeness, ADR reference, quantifiable acceptance, and required head fields (`**阶段**` / `**分类**` / `**类型**`).
- **openspec proposal 层**: apply the proposal-applicable subset of `propose_quality_check` (length ≥500, ≥1 ADR ref, In/Out Scope) and `openspec validate <name> --json`.

The implementation scripts already exist:
- `skills/guide-design/scripts/design_content_review.py` (improvements-layer checks)
- `skills/guide-design/scripts/design_content_review.sh` (wrapper)
- `skills/propose/scripts/propose_quality_check.py::run_design_checks` (proposal-layer checks)

ADR-0025 also prescribes the severity model: default is warning; `STRICT_DESIGN_GATE=yes` upgrades to blocking; `SKIP_CONTENT_REVIEW=yes` is the explicit escape hatch that bypasses the improvements-layer review.

The current `guide-design` approve flow does not reliably call these existing scripts on the normal execution path. As a result, decisions encoded by `add-propose-content-review` (P1, approved 2026-07-28) and `add-change-content-review` (P1, approved 2026-07-29) are not enforced on every approve action.

## Goals / Non-Goals

**Goals**
- Make the existing `design_content_review.sh` invocation part of the `guide-design` approve execution path (single-item and batch).
- Preserve ADR-0025 §D4 severity defaults: warning by default; `STRICT_DESIGN_GATE=yes` blocking; `SKIP_CONTENT_REVIEW=yes` skips the improvements-layer review.
- Surface the review's success / warning / blocking output so the user can see what fired.

**Non-Goals**
- Redesigning or expanding `design_content_review.py`'s checks, prompts, or severity rules.
- Re-implementing the Oracle review (`add-propose-content-review`) or the plan-phase change-artifact review (`add-change-content-review`).
- Modifying ADR-0025, proposal content format, openspec proposal-layer checks, or `proposal-approved` state semantics.
- Removing `SKIP_CONTENT_REVIEW` or changing the default warning into a hard block.

## Decisions

### Decision 1: Single shared review-call path for single-item and batch approve

Both single-item approve and batch approve funnel through the same internal helper that invokes `design_content_review.sh`. We do not maintain two parallel review-call code paths. The helper runs before any approve-side-effect (status write, proposal file landing, iteration.json mutation) and forwards the review's exit code / structured result.

**Alternatives considered**

- *Two code paths (single vs batch)*: rejected — invites the very bug we're fixing (batch silently swallowing single-item warnings).
- *Wrap inside `approve_proposal.sh` only*: rejected — `approve_proposal.sh` is the per-item worker; batch coordination belongs in `design_proposal_review.sh` / approve-flow orchestrator, not duplicated per item.

### Decision 2: Honor the existing three-state severity model

The wrapper does not invent a new severity model. The script reads `STRICT_DESIGN_GATE` and `SKIP_CONTENT_REVIEW` and passes the review's natural exit code / output through. We do not silently downgrade a `STRICT_DESIGN_GATE=yes` blocking result, nor do we silently suppress a warning in default mode.

**Alternatives considered**

- *Always block on review failures*: rejected — violates ADR-0025 §D4 default-warning contract.
- *Treat all results as advisory*: rejected — nullifies the strict mode escape hatch.

### Decision 3: Pass project root and improvement path via environment variables (Oracle C1-safe)

The wrapper reads `IMPROVEMENTS_PATH` and `PROJECT_ROOT` from the environment rather than interpolating user content into shell or Python strings. This eliminates the Oracle C1 string-interpolation injection vector flagged by the prior security review.

**Alternatives considered**

- *Pass path as argv*: rejected — bash `$VAR` expansion in the callee still has injection risk if any callee does string ops.
- *Embed path in prompt text*: rejected — same class of risk.

## Risks / Trade-offs

- **[Risk]** Adding a review invocation to the approve path may slow down single-item approvals noticeably. → **Mitigation**: the improvements-layer review is bounded by file size; in practice <50ms; if overhead becomes a concern, future iteration can introduce async invocation, but this change keeps synchronous semantics.
- **[Risk]** Batch approve may regress if one item's review blocks the batch. → **Mitigation**: per-item isolation is explicit in the task list; regression test asserts batch processes each item through the same helper.
- **[Risk]** Touching the approve flow may break unrelated approval behavior. → **Mitigation**: the wrapper is additive — review runs before any existing approve-side-effect; existing approve semantics are preserved when `SKIP_CONTENT_REVIEW=yes` is set.

## Migration Plan

1. Land this change in a single PR.
2. Run `./test.sh --full --regression` to confirm no new failures vs. `KNOWN_FAILURES.txt` baseline.
3. The change is self-contained: no schema bumps, no state-file format changes, no ADR edits, no change in user-facing menus.
4. Rollback: revert the PR — no data migration needed.

## Open Questions

- None at design time. If future iterations want a separate strict-only path, that should be a separate proposal per ADR-0025 §D4.