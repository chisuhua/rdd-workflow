# Design: wire-plan-done-quality-gates

## Context

`guide-plan` consumes approved proposals and produces OpenSpec change artifacts under `openspec/changes/<name>/`. The terminal action of `guide-plan` is `plan_done_gate`, which currently produces a small set of hard checks (e.g. tasks completeness, openspec validate) and either blocks or allows the plan→ship handoff.

ADR-0007 establishes a two-tier gate semantics: `error` blocks the gate, `warning` does not. ADR-0019 layers a per-check strict-mode switch (`STRICT_CHANGE_GATE=yes`) that upgrades a specific check family (`change_alignment`) from warning to error.

Two check assets already exist in the repo:

- `run_plan_checks` — a domain-aware plan quality scan that is part of the plan-phase check inventory.
- `change_alignment` — a per-change alignment scan from ADR-0019 with three checks and its own `STRICT_CHANGE_GATE=yes` escalation.

The current `plan_done_gate` execution path does not consistently invoke these assets. As a result, the decisions captured by `propose-quality-autohook` (P0, approved 2026-07-28) and `add-change-content-review` (P1, approved 2026-07-29) are visible only when an ad-hoc runner is invoked, not on every normal `guide-plan` run. The wiring gap is the subject of this change.

## Goals / Non-Goals

**Goals**
- Make `run_plan_checks` and `change_alignment` run as part of the normal `plan_done_gate` execution path.
- Keep ADR-0007 (default warning, error blocks) and ADR-0019 (`STRICT_CHANGE_GATE` independent escalation) intact.
- Surface both check names, pass status, and failure reason in the gate output and event records.

**Non-Goals**
- Rewriting or adding to the rule sets of `run_plan_checks` or `change_alignment`.
- Implementing the proposal-quality hook (`propose-quality-autohook`) or the change-artifact content review (`add-change-content-review`) — those remain separate proposals.
- Modifying ADR documents, change artifact format, proposal index format, or any other phase's gate behavior.

## Decisions

### Decision 1: Wire via the existing `plan_done_gate` script entry point

The current entry point in `skills/guide-plan/scripts/plan_done_gate.sh` already collects results from individual check runners. The wiring extends that collection to invoke `run_plan_checks` and `change_alignment` for each active change under `openspec/changes/<name>/`, then merges their structured results into the gate's existing pass/warn/error ledger.

**Alternatives considered**

- *Add a separate pre-gate wrapper*: rejected — would create two code paths to maintain and undermine "single source of truth" for gate output.
- *Inline the checks into `plan_done_gate.sh`*: rejected — would duplicate check logic; the existing `run_plan_checks` / `change_alignment` modules must remain the implementation owners.

### Decision 2: Honor ADR-0019's independent escalation switch

`STRICT_CHANGE_GATE=yes` continues to apply only to `change_alignment` failures. We do not invent a new strict-mode flag and we do not extend `STRICT_CHANGE_GATE` to cover `run_plan_checks` in this change. `run_plan_checks` failures always follow ADR-0007 default-warning semantics.

**Alternatives considered**

- *Single unified strict mode*: rejected — would violate ADR-0019 §3 by coupling an unrelated check family to the alignment-specific switch.
- *Always-block on `run_plan_checks` failure*: rejected — would conflict with ADR-0007 warning default and break the no-FF contracts of approved low-severity checks.

### Decision 3: Failures are surfaced, not swallowed

Every `run_plan_checks` and `change_alignment` invocation produces a structured result. `plan_done_gate` records the check name, the change it ran against, the severity (pass / warning / error), and the reason on failure. Silent default-skip is forbidden — if a check is unavailable, the gate prints "check unavailable" plus reason and continues with the remaining checks.

**Alternatives considered**

- *Suppress results when quiet*: rejected — would defeat diagnostic visibility (AGENTS.md guideline: every changed line traces to a request).
- *Fail-closed if any check is unavailable*: rejected — would block the gate on transient infrastructure issues and violate ADR-0007's warning-default contract.

## Risks / Trade-offs

- **[Risk]** `run_plan_checks` may have been excluded intentionally from `plan_done_gate` for performance reasons. → **Mitigation**: invocation cost is bounded per-change; benchmarks added to the regression suite. If cost proves too high, future iteration can move to a sampled/async invocation, but this change preserves the original semantics.
- **[Risk]** Wiring may inadvertently upgrade default-warning items to blocking. → **Mitigation**: explicit `STRICT_CHANGE_GATE` gate in `plan_done_gate.sh`; regression tests assert that default failures do not block.
- **[Risk]** Touching the gate script may break unrelated tests. → **Mitigation**: keep the change additive — only add new invocations and result merges, do not modify existing check ordering or exit code paths.

## Migration Plan

1. Land this change in a single PR (or single change archive).
2. Run `./test.sh --full --regression` to confirm no new failures vs. `KNOWN_FAILURES.txt` baseline.
3. The change is self-contained: no schema bumps, no state-file format changes, no ADR edits.
4. Rollback: revert the PR — no data migration needed (no persistent state is added by this wiring).

## Open Questions

- None at design time. If a future iteration needs to extend `STRICT_CHANGE_GATE` to other check families, that should be a separate proposal per ADR-0019 §3.