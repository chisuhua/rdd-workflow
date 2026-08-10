# Tasks: wire-plan-done-quality-gates

## 1. Wiring Investigation

- [ ] 1.1 Locate `run_plan_checks` and `change_alignment` entry points in `_lib/` and confirm public function signatures
- [ ] 1.2 Read `skills/guide-plan/scripts/plan_done_gate.sh` to identify the existing check-runner collection loop
- [ ] 1.3 Confirm that `plan_done_gate` currently does NOT invoke both checks on the normal path (or that invocation is incomplete)

## 2. Wire run_plan_checks into plan_done_gate

- [ ] 2.1 Add invocation of `run_plan_checks` per active change under `openspec/changes/<name>/` inside `plan_done_gate.sh`
- [ ] 2.2 Convert the check's return into a structured `{name, severity, reason}` record consistent with the gate's existing result ledger
- [ ] 2.3 Append the record to the gate's pass/warning/error aggregation

## 3. Wire change_alignment with STRICT_CHANGE_GATE escalation

- [ ] 3.1 Add invocation of `change_alignment` per active change inside `plan_done_gate.sh`
- [ ] 3.2 Honor `STRICT_CHANGE_GATE=yes`: when set, escalate `change_alignment` failures from warning to error
- [ ] 3.3 Ensure the escalation applies only to `change_alignment` (NOT to `run_plan_checks` or other existing checks)

## 4. Surface results in gate output and event records

- [ ] 4.1 Confirm gate output contains the check name (`run_plan_checks`, `change_alignment`) for both pass and fail cases
- [ ] 4.2 Confirm the structured failure reason is recorded when a check fails
- [ ] 4.3 Confirm unavailable-check states print "check unavailable" with reason and do NOT silently swallow

## 5. Regression Coverage

- [ ] 5.1 Add a bats test asserting `run_plan_checks` is invoked in the normal `plan_done_gate` path
- [ ] 5.2 Add a bats test asserting `change_alignment` is invoked in the normal `plan_done_gate` path
- [ ] 5.3 Add a bats test asserting default-mode failure remains a warning and does not block the gate
- [ ] 5.4 Add a bats test asserting `STRICT_CHANGE_GATE=yes` upgrades `change_alignment` failure to error and blocks the gate
- [ ] 5.5 Add a bats test asserting `run_plan_checks` failure does NOT block under `STRICT_CHANGE_GATE=yes`
- [ ] 5.6 Run `./test.sh --full --regression` and confirm no new failures vs. `KNOWN_FAILURES.txt`

## 6. Verification

- [ ] 6.1 Run `openspec validate wire-plan-done-quality-gates --type change --json` and confirm no errors
- [ ] 6.2 Confirm `proposal-suggestions.md`, all existing proposals, ADR files, and git history outside this change are unmodified