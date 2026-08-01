## 1. Implement project-setup helper

- [ ] 1.1 Create `skills/_lib/check_project_setup.sh` exposing `check_project_setup <project_root>` that writes a JSON array to stdout with fields `name`, `status`, `severity`, `fix_command`, and `detail` for the six checks.
  - Verification: `bash -c 'source skills/_lib/check_project_setup.sh && check_project_setup /workspace/project/rdd-workflow' | python3 -m json.tool >/dev/null && echo "JSON OK"`
- [ ] 1.2 Implement gitignore checks for `.rddf/state/`, `.rddf/wt/`, `.rddf/plans/` using exact-pattern matching first and `.rddf/` fallback; emit `error` severity for failures. For every gitignore issue, format `detail` with both the detected current state (`现状`) and required state (`期望`) so users can compare them directly.
  - Verification: `source skills/_lib/check_project_setup.sh && check_project_setup /workspace/project/rdd-workflow | jq '.[] | select(.name=="rddf_state_ignored") | .status' | grep -q pass`
- [ ] 1.3 Implement openspec CLI availability check by invoking `openspec --version`.
  - Verification: `source skills/_lib/check_project_setup.sh && check_project_setup /workspace/project/rdd-workflow | jq '.[] | select(.name=="openspec_cli_available") | .status' | grep -q pass`
- [ ] 1.4 Implement git HEAD existence check by invoking `git rev-parse HEAD`.
  - Verification: `source skills/_lib/check_project_setup.sh && check_project_setup /workspace/project/rdd-workflow | jq '.[] | select(.name=="git_head_exists") | .status' | grep -q pass`
- [ ] 1.5 Implement large-untracked-directory check using `git ls-files --others --exclude-standard` and `du -sm`, threshold 10MB, severity `safe_auto_fix`.
  - Verification: `source skills/_lib/check_project_setup.sh && check_project_setup /workspace/project/rdd-workflow | jq '.[] | select(.name=="large_untracked_dirs") | .severity' | grep -q safe_auto_fix`

## 2. Add bats integration tests

- [ ] 2.1 Create `tests/integration/test_check_project_setup.bats` with a passing-project fixture.
  - Verification: `bats tests/integration/test_check_project_setup.bats --filter "passing project"`
- [ ] 2.2 Add test for missing `.rddf/state/` ignore rule asserting `status == fail` and `severity == error`.
  - Verification: `bats tests/integration/test_check_project_setup.bats --filter "missing rddf_state_ignored"`
- [ ] 2.3 Add test for missing `.rddf/wt/` ignore rule asserting correct `fix_command`.
  - Verification: `bats tests/integration/test_check_project_setup.bats --filter "missing rddf_wt_ignored"`
- [ ] 2.4 Add regression test for `.rddf/plans/` accidentally ignored asserting `status == fail`.
  - Verification: `bats tests/integration/test_check_project_setup.bats --filter "plans regression"`
- [ ] 2.5 Add test for missing `.gitignore` file asserting hard failure and suggested creation command.
  - Verification: `bats tests/integration/test_check_project_setup.bats --filter "no gitignore"`
- [ ] 2.6 Add test for large untracked directory (>10MB) asserting `severity == safe_auto_fix`.
  - Verification: `bats tests/integration/test_check_project_setup.bats --filter "large untracked"`
- [ ] 2.7 Add JSON schema compliance test verifying every issue object has `name`, `status`, `severity`, `fix_command`, and `detail`.
  - Verification: `bats tests/integration/test_check_project_setup.bats --filter "JSON schema"`

## 3. Integrate helper into workflow entry points

- [ ] 3.1 Append a `check_project_setup` call to `skills/guide-arch/scripts/arch_env_check.sh` near the end of Phase 1; if any issue has `severity == error` and `status == fail`, print `name`, `detail`, and `fix_command`, then `return 1`.
  - Verification: `bats tests/integration/test_arch_env_check.bats --filter "setup gate" 2>/dev/null || echo "run bats tests/integration/test_arch_env_check.bats"`
- [ ] 3.2 Replace the legacy inline large-untracked-directory block in `skills/guide/scripts/scan-state.sh` with one non-blocking `check_project_setup` analysis block before the menu. Remove the existing `du -sm`/`LARGE_DIRS` implementation so large directories are reported exactly once; treat every helper issue as `safe_auto_fix` and continue regardless.
  - Verification: `grep -n "check_project_setup" skills/guide/scripts/scan-state.sh && ! grep -q "LARGE_DIRS" skills/guide/scripts/scan-state.sh`
- [ ] 3.3 Add Section 5 "项目设置检查" to `skills/INSTALL.md` that sources the helper, prints ✅/❌ per issue, and does not block installation.
  - Verification: `grep -n "项目设置检查" skills/INSTALL.md`

## 4. Update documentation and refactor duplicated assertions

- [ ] 4.1 Update `USAGE.md` "常见陷阱" with one line explaining that first `guide-arch` failure due to `.gitignore` should be fixed by running the printed `fix_command` and rerunning.
  - Verification: `grep -n "fix_command" USAGE.md`
- [ ] 4.2 Update `docs/v2-workflow-overview.md` with a short paragraph describing project-setup check triggers and user expectations.
  - Verification: `grep -n "project-setup" docs/v2-workflow-overview.md`
- [ ] 4.3 Refactor `tests/integration/test_plan_review_phase.bats:62-66` to assert via `check_project_setup` output instead of inline `.gitignore` grep.
  - Verification: `sed -n '60,70p' tests/integration/test_plan_review_phase.bats`

## 5. Acceptance validation

- [ ] 5.1 Run the new bats suite and confirm all cases pass.
  - Verification: `bats tests/integration/test_check_project_setup.bats`
- [ ] 5.2 Run Python tests to ensure no regressions.
  - Verification: `python3 -m pytest tests/ -q --tb=short`
- [ ] 5.3 Run npm test to ensure bats smoke/static/worktree subsets pass.
  - Verification: `npm test`
- [ ] 5.4 Run `openspec validate check-project-setup --strict` and confirm it passes.
  - Verification: `openspec validate check-project-setup --strict`
- [ ] 5.5 Run `openspec status --change check-project-setup --json` and confirm all artifacts are reported complete.
  - Verification: `openspec status --change check-project-setup --json | jq '.isComplete'`
- [ ] 5.6 Verify helper runtime is under 50ms on a local SSD fixture.
  - Verification: `source skills/_lib/check_project_setup.sh && time check_project_setup /tmp/test-fixture >/dev/null`
- [ ] 5.7 Run manual `guide-arch` Phase 1 e2e checks against three temporary git fixtures: correctly configured `.gitignore`, missing `.rddf/state/`, and incorrectly ignored `.rddf/plans/`; confirm pass, hard-block, and hard-block behavior respectively.
  - Verification: record the three commands and exit codes in the change execution log; expected exit codes are `0`, non-zero, non-zero, with each failure printing its exact `fix_command`.
