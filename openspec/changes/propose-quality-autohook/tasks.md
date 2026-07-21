## Tasks

### [1/5] Create propose_quality_hook.py module
- [ ] Create skills/propose/scripts/propose_quality_hook.py with:
  - [ ] `run_quality_check(project_root, change_name)` - calls run_all_checks, writes .rddf/state/propose-quality.json, returns dict
  - [ ] `invoke_from_propose_phase4(change_name)` - reads PROJECT_ROOT env var, calls run_quality_check, prints stdout, returns exit code (0 default, 1 strict + warnings)
  - [ ] `__main__` block invoking invoke_from_propose_phase4 with sys.argv[1]
- [ ] JSON schema: schema_version=1, change, warnings, checked_at (ISO), strict_mode, check_count=5, passed_count
- [ ] Honor STRICT_PROPOSE_GATE=yes env var (use is_strict_mode from arch_quality_gate)

### [2/5] Create propose_quality_hook.sh bash wrapper
- [ ] Create skills/propose/scripts/propose_quality_hook.sh with `invoke_propose_quality_hook <name>` function
- [ ] Env-var only passing (PROJECT_ROOT, CHANGE_NAME) - Oracle C1 safe (no bash string interpolation)
- [ ] Delegate to python3 propose_quality_hook.py

### [3/5] Wire propose.md Phase 4 to invoke the hook
- [ ] Add Step 4e (after propose_create_change / propose_finalize_change): source propose_quality_hook.sh + invoke_propose_quality_hook <name>
- [ ] Wrap in `if [ -f ... ]` guard for forward compatibility
- [ ] Hook runs in both skeleton and full branches

### [4/5] Register propose_quality_checks Check in gate.py plan_done
- [ ] Add `_check_propose_quality(ctx)` function in skills/_lib/gate.py
- [ ] Read state vector's `plan_side.current_change` (fallback to `arch_side.current_change`)
- [ ] Read .rddf/state/propose-quality.json (fallback to re-running run_all_checks)
- [ ] Return (len(warnings) == 0, "warning")
- [ ] Register in `_DEFAULT_CHECKS["plan_done"]` with `strict_wrap(_check_propose_quality, env_var="STRICT_PROPOSE_GATE")`
- [ ] Import `run_all_checks` from skills.propose.scripts.propose_quality_check

### [5/5] Write tests + verify
- [ ] Create tests/unit/test_propose_quality_hook.py with:
  - [ ] test_run_quality_check_writes_valid_json
  - [ ] test_invoke_returns_zero_in_default_mode
  - [ ] test_invoke_returns_one_under_strict_with_warnings
  - [ ] test_invoke_returns_zero_under_strict_no_warnings
  - [ ] test_report_has_correct_schema_version
  - [ ] test_report_has_correct_check_count
- [ ] Extend tests/unit/test_gate.py with:
  - [ ] test_plan_done_includes_propose_quality_checks
  - [ ] test_propose_quality_check_default_warning
  - [ ] test_propose_quality_check_strict_error
  - [ ] test_propose_quality_check_missing_state_vector_skips
- [ ] Create tests/integration/test_propose_quality_hook.bats with:
  - [ ] helper_exists - propose_quality_hook.sh + invoke_propose_quality_hook function
  - [ ] propose_md_invokes_hook - grep propose.md for propose_quality_hook.sh
  - [ ] gate_py_registers_check - grep gate.py for propose_quality_checks
  - [ ] hook_valid_proposal_exits_zero
  - [ ] hook_broken_proposal_default_exits_zero
  - [ ] hook_broken_proposal_strict_exits_one
  - [ ] hook_writes_json_state_file
- [ ] Run `python3 -m pytest tests/unit/test_propose_quality_hook.py tests/unit/test_gate.py -q --tb=short`
- [ ] Run `bats tests/integration/test_propose_quality_hook.bats`
- [ ] Run `bats tests/smoke.bats tests/integration/test_propose_skill.bats tests/integration/test_propose_phase4_extraction.bats` (no regressions)
- [ ] Run `python3 -m pytest tests/unit/ -q --tb=short` (full unit suite, no regressions)
- [ ] Stage only this change's files (not pre-existing working tree changes)
- [ ] Commit with message: `feat(propose): wire propose_quality_check.py into Phase 4 + plan_done gate`
