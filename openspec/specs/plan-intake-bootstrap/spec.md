# plan-intake-bootstrap Specification

## Purpose
TBD - created by archiving change harden-plan-intake-bootstrap-and-design-gate-tests. Update Purpose after archive.
## Requirements
### Requirement: plan-intake-detects-missing-design-handoff

The plan phase intake (`plan_intake.sh`) MUST detect the absence of `.design-handoff.json` and exit non-zero with a guidance message, not silently passing.

#### Scenario: missing design-handoff

- WHEN a user runs `guide-plan` without first running `guide-design` (no `.rddf/state/.design-handoff.json` exists)
- THEN `plan_intake.sh` exits with non-zero status
- AND outputs a guidance message: "Please run `guide-design` first"
- AND does NOT silently create changes

### Requirement: plan-intake-tolerates-v2-handoff-missing-field

The plan phase intake MUST treat `.design-handoff.json` files with `version: 2` but missing the `changes_pre_created` field as v1-compatible (treat `changes_pre_created` as empty array) with a warning log.

#### Scenario: v2 handoff missing changes_pre_created

- WHEN `.design-handoff.json` has `version: 2` but lacks `changes_pre_created`
- THEN `plan_intake.sh` proceeds with empty `changes_pre_created: []`
- AND logs a warning: "v2 handoff missing changes_pre_created, treating as v1"
- AND does NOT block plan phase entry

### Requirement: plan-intake-detects-stale-handoff

The plan phase intake MUST detect stale `.design-handoff.json` (where `design_complete_at` is more than 30 days old) and emit a warning without blocking.

#### Scenario: stale design-handoff

- WHEN `.design-handoff.json` `design_complete_at` is more than 30 days ago
- THEN `plan_intake.sh` outputs "handoff is stale, consider re-running guide-design"
- AND continues with plan phase execution (no block)

### Requirement: plan-intake-detects-empty-changes-pre-created

The plan phase intake MUST detect `changes_pre_created: []` (empty array, design phase produced no changes) and exit non-zero with guidance.

#### Scenario: empty changes_pre_created

- WHEN `.design-handoff.json` has `changes_pre_created: []`
- THEN `plan_intake.sh` exits non-zero
- AND outputs "no proposals to plan, exiting. Run `guide-design` first to create proposals"

### Requirement: plan-intake-reports-interrupted-trace

The plan phase intake MUST detect interrupted traces (missing `finalize_at` field in `.rddf/state/trace/*.json`) and emit a warning without blocking.

#### Scenario: interrupted trace

- WHEN `.rddf/state/trace/<phase>.json` lacks `finalize_at`
- THEN `plan_intake.sh` outputs "interrupted trace from <timestamp>, run `rddf orchestrate show <phase>` to triage"
- AND does NOT block plan phase entry

### Requirement: plan-intake-marks-abandoned-sessions

The plan phase intake MUST detect abandoned rddf-sessions in `.rddf/state/sessions.json` and mark them as orphans without blocking.

#### Scenario: abandoned session

- WHEN `sessions.json` contains a session with `end_reason: user-abandoned-via-guide-design-transition`
- THEN `plan_intake.sh` marks the session as orphan
- AND outputs a hint to run `rddf-session archive-history` for cleanup
- AND does NOT block plan phase entry

### Requirement: plan-intake-skip-propose-for-design-precreated

The plan phase MUST skip the propose step for changes listed in `.design-handoff.json::changes_pre_created`.

#### Scenario: design-pre-created change

- WHEN `proposal-approved.md` lists `name=X` AND `.design-handoff.json::changes_pre_created` contains `X`
- THEN `guide-plan` Phase 2 (propose) does NOT call `propose --create X`
- AND `guide-plan` Phase 2.5 (fill) writes `design.md` and `tasks.md` for `X`
- AND `guide-plan` does NOT modify `proposal.md` (Path A invariant)

### Requirement: design-content-review-characterization-baseline

The pytest unit tests for `propose_quality_check.py::run_design_checks` MUST lock the **current behavior** as a characterization baseline, regardless of whether the current behavior is correct.

#### Scenario: characterization test on known edge case

- WHEN a test improvement file with head field `**类型**` missing is processed by `run_design_checks`
- THEN the characterization test asserts whatever the CURRENT behavior is (pass or fail)
- AND the test is marked with `@pytest.mark.characterization`
- AND the test does NOT fail or expect a specific outcome (only documents reality)

### Requirement: plan-intake-stale-handoff-with-empty-changes-folder

The plan phase intake MUST handle the case where `.plan-handoff.json` references a `current_change` that has been archived while `openspec/changes/` is empty.

#### Scenario: stale plan-handoff referencing archived change

- WHEN `.plan-handoff.json::current_change = "some-archived-change"` AND `openspec/changes/` has no such directory
- THEN `plan_intake.sh` detects the inconsistency
- AND emits a warning suggesting re-running `guide-plan` from fresh state
- AND does NOT silently proceed with stale state

