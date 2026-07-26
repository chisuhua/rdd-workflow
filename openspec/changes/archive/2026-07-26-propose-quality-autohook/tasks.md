## Tasks

### [1/5] Create propose_quality_hook.py module
- [x] 1.1 **Write failing test**: Write `tests/unit/test_propose_quality_hook.py` with `test_run_quality_check_writes_valid_json` using `tmp_path` fixture
- [x] 1.2 **Verify fail**: Run `python3 -m pytest tests/unit/test_propose_quality_hook.py::test_run_quality_check_writes_valid_json -xvs` — confirm it fails (module doesn't exist yet)
- [x] 1.3 **Implement**: Create `skills/propose/scripts/propose_quality_hook.py` with `run_quality_check()` and `invoke_from_propose_phase4()` — calls `run_all_checks()`, writes `.rddf/state/propose-quality.json` with schema_version=1, respects `STRICT_PROPOSE_GATE=yes`
- [x] 1.4 **Verify pass**: Re-run the test — confirm it passes
- [x] 1.5 **Commit**: `git add skills/propose/scripts/propose_quality_hook.py tests/unit/test_propose_quality_hook.py && git commit -m "feat(propose): add propose_quality_hook.py module"`

### [2/5] Create propose_quality_hook.sh bash wrapper
- [x] 2.1 **Write failing test**: Add `test_helper_exists` to `tests/integration/test_propose_quality_hook.bats` — assert `propose_quality_hook.sh` exists and contains `invoke_propose_quality_hook`
- [x] 2.2 **Verify fail**: Run `bats tests/integration/test_propose_quality_hook.bats` — confirm it fails (wrapper doesn't exist yet)
- [x] 2.3 **Implement**: Create `skills/propose/scripts/propose_quality_hook.sh` with `invoke_propose_quality_hook()` — env-var only passing (Oracle C1 safe), delegates to `python3 propose_quality_hook.py`
- [x] 2.4 **Verify pass**: Re-run the test — confirm it passes
- [x] 2.5 **Commit**: `git add skills/propose/scripts/propose_quality_hook.sh tests/integration/test_propose_quality_hook.bats && git commit -m "feat(propose): add propose_quality_hook.sh bash wrapper"`

### [3/5] Wire propose.md Phase 4 to invoke the hook
- [x] 3.1 **Write failing test**: Add `test_propose_md_invokes_hook` to integration test — grep propose.md for `propose_quality_hook.sh`
- [x] 3.2 **Verify fail**: Run the test — confirm it fails (propose.md doesn't yet reference the hook)
- [x] 3.3 **Implement**: Add Step 4e to `skills/propose/SKILL.md` after both skeleton and full artifact creation branches:
  ```bash
  if [ -f "$SCRIPT_DIR/scripts/propose_quality_hook.sh" ]; then
      source "$SCRIPT_DIR/scripts/propose_quality_hook.sh"
      invoke_propose_quality_hook "<name>"
  fi
  ```
- [x] 3.4 **Verify pass**: Re-run the test — confirm it passes
- [x] 3.5 **Commit**: `git add skills/propose/SKILL.md && git commit -m "feat(propose): wire quality hook into Phase 4"`

### [4/5] Register propose_quality_checks Check in gate.py plan_done
- [x] 4.1 **Write failing test**: Add `test_plan_done_includes_propose_quality_checks` to `tests/unit/test_gate.py` — assert `propose_quality_checks` in gate check names
- [x] 4.2 **Verify fail**: Run `python3 -m pytest tests/unit/test_gate.py::test_plan_done_includes_propose_quality_checks -xvs` — confirm it fails (check not yet registered)
- [x] 4.3 **Implement**: Add `_check_propose_quality(ctx)` to `skills/_lib/gate.py` — reads cached report from `.rddf/state/propose-quality.json`, falls back to `run_all_checks()`, returns `(len(warnings)==0, "warning")`. Register in `_DEFAULT_CHECKS["plan_done"]` with `strict_wrap(env_var="STRICT_PROPOSE_GATE")`. Import `run_all_checks` from `skills.propose.scripts.propose_quality_check`.
- [x] 4.4 **Verify pass**: Re-run the test — confirm it passes
- [x] 4.5 **Commit**: `git add skills/_lib/gate.py tests/unit/test_gate.py && git commit -m "feat(gate): register propose_quality_checks in plan_done"`

### [5/5] Write tests + verify no regressions
- [x] 5.1 **Write full test suite**:
  - [x] `tests/unit/test_propose_quality_hook.py`: 6 tests covering run_quality_check, invoke modes, strict mode, schema version
  - [x] `tests/unit/test_gate.py`: 4 tests covering check presence, default warning, strict error, missing state vector skip
  - [x] `tests/integration/test_propose_quality_hook.bats`: 7 tests covering helper existence, propose.md reference, gate.py reference, valid/broken/strict proposals
- [x] 5.2 **Verify**: Run `python3 -m pytest tests/unit/test_propose_quality_hook.py tests/unit/test_gate.py -q --tb=short` — all pass
- [x] 5.3 **Verify**: Run `bats tests/integration/test_propose_quality_hook.bats` — all pass
- [x] 5.4 **Verify**: Run `python3 -m pytest tests/unit/ -q --tb=short` — full unit suite, no regressions
- [x] 5.5 **Commit**: `git add tests/ && git commit -m "test: propose-quality-autohook full test suite"`