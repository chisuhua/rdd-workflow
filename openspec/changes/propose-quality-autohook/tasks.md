## Tasks

### [1/5] Create propose_quality_hook.py module
- [x] Create skills/propose/scripts/propose_quality_hook.py with:
  - [x] `run_quality_check(project_root, change_name)` - calls run_all_checks, writes .rddf/state/propose-quality.json, returns dict
  - [x] `invoke_from_propose_phase4(change_name)` - reads PROJECT_ROOT env var, calls run_quality_check, prints stdout, returns exit code (0 default, 1 strict + warnings)
  - [x] `__main__` block invoking invoke_from_propose_phase4 with sys.argv[1]
- [x] JSON schema: schema_version=1, change, warnings, checked_at (ISO), strict_mode, check_count=5, passed_count
- [x] Honor STRICT_PROPOSE_GATE=yes env var (use is_strict_mode from arch_quality_gate)

### [2/5] Create propose_quality_hook.sh bash wrapper
- [x] Create skills/propose/scripts/propose_quality_hook.sh with `invoke_propose_quality_hook <name>` function
- [x] Env-var only passing (PROJECT_ROOT, CHANGE_NAME) - Oracle C1 safe (no bash string interpolation)
- [x] Delegate to python3 propose_quality_hook.py

### [3/5] Wire propose.md Phase 4 to invoke the hook
- [x] Add Step 4e (after propose_create_change / propose_finalize_change): source propose_quality_hook.sh + invoke_propose_quality_hook <name>
- [x] Wrap in `if [ -f ... ]` guard for forward compatibility
- [x] Hook runs in both skeleton and full branches

### [4/5] Register propose_quality_checks Check in gate.py plan_done
- [x] Add `_check_propose_quality(ctx)` function in skills/_lib/gate.py
- [x] Read state vector's `plan_side.current_change` (fallback to `arch_side.current_change`)
- [x] Read .rddf/state/propose-quality.json (fallback to re-running run_all_checks)
- [x] Return (len(warnings) == 0, "warning")
- [x] Register in `_DEFAULT_CHECKS["plan_done"]` with `strict_wrap(_check_propose_quality, env_var="STRICT_PROPOSE_GATE")`
- [x] Import `run_all_checks` from skills.propose.scripts.propose_quality_check

### [5/5] Write tests + verify
- [x] Create tests/unit/test_propose_quality_hook.py with:
  - [x] test_run_quality_check_writes_valid_json
  - [x] test_invoke_returns_zero_in_default_mode
  - [x] test_invoke_returns_one_under_strict_with_warnings
  - [x] test_invoke_returns_zero_under_strict_no_warnings
  - [x] test_report_has_correct_schema_version
  - [x] test_report_has_correct_check_count
- [x] Extend tests/unit/test_gate.py with:
  - [x] test_plan_done_includes_propose_quality_checks
  - [x] test_propose_quality_check_default_warning
  - [x] test_propose_quality_check_strict_error
  - [x] test_propose_quality_check_missing_state_vector_skips
- [x] Create tests/integration/test_propose_quality_hook.bats with:
  - [x] helper_exists - propose_quality_hook.sh + invoke_propose_quality_hook function
  - [x] propose_md_invokes_hook - grep propose.md for propose_quality_hook.sh
  - [x] gate_py_registers_check - grep gate.py for propose_quality_checks
  - [x] hook_valid_proposal_exits_zero
  - [x] hook_broken_proposal_default_exits_zero
  - [x] hook_broken_proposal_strict_exits_one
  - [x] hook_writes_json_state_file
- [x] Run `python3 -m pytest tests/unit/test_propose_quality_hook.py tests/unit/test_gate.py -q --tb=short`
- [x] Run `bats tests/integration/test_propose_quality_hook.bats`
- [x] Run `bats tests/smoke.bats tests/integration/test_propose_skill.bats tests/integration/test_propose_phase4_extraction.bats` (no regressions)
- [x] Run `python3 -m pytest tests/unit/ -q --tb=short` (full unit suite, no regressions)
- [x] Stage only this change's files (not pre-existing working tree changes)
- [x] Commit with message: `feat(propose): wire propose_quality_check.py into Phase 4 + plan_done gate`
