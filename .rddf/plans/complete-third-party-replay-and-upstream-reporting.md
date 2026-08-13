# complete-third-party-replay-and-upstream-reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `skill_use("execute")` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make globally installed rdd-workflow usable from third-party projects for trace replay, local failure buffering, and safe submission of workflow issues to `chisuhua/rdd-workflow`.

**Architecture:** Keep the installed tool root separate from the invoking business project root. Resolve project state from explicit `RDDF_PROJECT_ROOT`, Git root, or cwd; resolve tool modules from the installed package. Make finalize own the classify-and-report transition, while preserving fail-open behavior for reporter and GitHub failures.

**Tech Stack:** Bash, Python 3.11, pytest, bats-core, `gh` CLI mocks, existing `.rddf` state and OpenSpec test helpers.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/cli/orchestrate_cmd.py` | Root-aware trace lookup and finalize-to-reporter wiring. |
| `_lib/cli/__main__.py` | Preserve third-party project root when routing the global CLI. |
| `_lib/cli/issue_cmd.py` | Package-safe reporter imports and local issue commands. |
| `_lib/cli/report_issue_cmd.py` | Package-safe reporter imports and manual reporting policy. |
| `_lib/issue_reporter.py` | Effective reporting configuration and upstream target behavior. |
| `_lib/config.py` / `_lib/core/defaults.py` / `_lib/schemas/config_schema.json` | Align declared and runtime reporting configuration. |
| `_lib/close_issues.py` / `_lib/archive.sh` | Safe, non-blocking archive close behavior. |
| `skills/_lib/orchestrator_entry.sh` | Tool-root/project-root separation and global helper execution. |
| `skills/_lib/post_flow_wrap.sh` | Shared helper lookup and compatibility behavior. |
| `skills/guide-arch/scripts/arch_env_check.sh` | External-project helper bootstrap. |
| `skills/guide-plan/scripts/plan_intake.sh` | External-project helper bootstrap. |
| `skills/guide-ship/scripts/ship_env_check.sh` | External-project helper bootstrap. |
| `skills/execute/scripts/select_worktree.sh` | External-project helper bootstrap. |
| `install.sh` / `skills/INSTALL.md` | Install helper exposure and user-facing documentation. |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_orchestrate_cmd.py` | Trace directory, finalize reporting, and report status. |
| `tests/unit/test_cli_reporter.py` | CLI imports, local issue commands, and submission policy. |
| `tests/unit/test_issue_reporter.py` | Repo target, dedup, CI and local fallback behavior. |
| `tests/unit/test_close_issues.py` | Archive close fallback and safe argument handling. |
| `tests/integration/test_global_install_external_project.bats` | Global-install replay and issue flow in an isolated third-party repo. |
| `tests/integration/test_orchestrator_default_on.bats` | Existing default-ON regression coverage plus root ownership. |
| `tests/integration/test_archive_*_close_hook.bats` | Worktree/lightweight archive close behavior. |

---

### Task 1: Establish project-root and tool-root resolution

**Files:**
- Modify: `skills/_lib/orchestrator_entry.sh`
- Modify: `skills/_lib/post_flow_wrap.sh`
- Modify: `skills/guide-arch/scripts/arch_env_check.sh`
- Modify: `skills/guide-plan/scripts/plan_intake.sh`
- Modify: `skills/guide-ship/scripts/ship_env_check.sh`
- Modify: `skills/execute/scripts/select_worktree.sh`
- Test: `tests/integration/test_global_install_external_project.bats`

- [ ] **Step 1: Write the failing tests**

Add an isolated third-party Git repository test that sources each phase helper through the global fallback, runs one wrapped command, and asserts: `RDDF_PROJECT_ROOT` equals the third-party root, a trace is under third-party `.rddf/state/trace`, and the rdd-workflow tool root has no new issue/trace artifact.

- [ ] **Step 2: Run tests to verify failure**

Run: `bats tests/integration/test_global_install_external_project.bats`
Expected: FAIL because the phase scripts only probe `<third-party>/skills/_lib` and the current wrapper derives `RDDF_PROJECT_ROOT` from its own package location.

- [ ] **Step 3: Implement the minimal root contract**

Use explicit `RDDF_PROJECT_ROOT` first, otherwise `git -C "$PWD" rev-parse --show-toplevel`, otherwise cwd. Keep the helper file location only for `RDDF_TOOL_ROOT`. Add the existing global resolver fallback to all four entry scripts. Do not use `BASH_SOURCE` as the business root and do not interpolate values into Python source.

- [ ] **Step 4: Run tests to verify they pass**

Run: `bats tests/integration/test_global_install_external_project.bats tests/integration/test_orchestrator_default_on.bats`
Expected: PASS, with all generated state confined to the isolated third-party repository.

- [ ] **Step 5: Defer commit**

Leave changes for the aggregate execute commit according to the repository worktree commit policy.

### Task 2: Make trace persistence project-root aware

**Files:**
- Modify: `_lib/cli/orchestrate_cmd.py`
- Modify: `_lib/cli/__main__.py` only if needed to preserve explicit root
- Test: `tests/unit/test_orchestrate_cmd.py`
- Test: `tests/integration/test_global_install_external_project.bats`

- [ ] **Step 1: Write the failing tests**

Add tests setting `RDDF_PROJECT_ROOT` to a temporary Git project and changing cwd to a child directory. Assert `_get_trace_dir()` is `<project>/.rddf/state/trace`, while an explicit `RDDF_TRACE_DIR` remains authoritative.

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py -k 'trace_dir or subdirectory' -v`
Expected: FAIL because the current default resolves `.rddf/state/trace` from cwd.

- [ ] **Step 3: Implement root-aware trace lookup**

Resolve the default as `Path(RDDF_PROJECT_ROOT) / ".rddf/state/trace"`; preserve absolute and relative explicit `RDDF_TRACE_DIR` semantics without changing filename matching or JSONL format.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py -k 'trace_dir or subdirectory' -v` and the external bats replay case.
Expected: PASS from project root and descendant cwd.

- [ ] **Step 5: Defer commit**

Keep the change in the aggregate execute commit.

### Task 3: Connect normal finalize to local issue buffering

**Files:**
- Modify: `_lib/cli/orchestrate_cmd.py`
- Modify: `_lib/post_flow_analysis.py` only if return semantics require it
- Test: `tests/unit/test_orchestrate_cmd.py`
- Test: `tests/unit/test_post_flow_analysis.py`

- [ ] **Step 1: Write the failing tests**

Mock `analyze_phase_trace` and `report_flow_bug`. Assert a reportable classification calls the reporter with the business project root and writes `report_written: true` only when a `Path` is returned. Add non-reportable and reporter-failure cases.

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py tests/unit/test_post_flow_analysis.py -k 'finalize or report_written' -v`
Expected: FAIL because finalize currently only classifies and marks any non-None classification as written.

- [ ] **Step 3: Implement finalize reporting**

After classification, call `report_flow_bug` only when `classification.should_report` and `classification.report_category` are set. Catch reporter exceptions as warnings, preserve the original phase result, and derive `report_written` from the returned issue path. Always append finalize.

- [ ] **Step 4: Run tests to verify they pass**

Run the targeted pytest command again, then simulate a failing subprocess and finalize in a temporary project. Expected: exactly one local issue file and a truthful finalize event.

- [ ] **Step 5: Defer commit**

Keep the change in the aggregate execute commit.

### Task 4: Repair reporter CLI imports and local commands

**Files:**
- Modify: `_lib/cli/issue_cmd.py`
- Modify: `_lib/cli/report_issue_cmd.py`
- Test: `tests/unit/test_cli_reporter.py`

- [ ] **Step 1: Write the failing tests**

Run the CLI entry point from a clean temporary project and assert `rddf issue list` and `rddf report-issue --no-submit` complete without `No module named 'issue_reporter'`. Add local issue list/show assertions.

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/unit/test_cli_reporter.py -v` and the temporary CLI smoke command.
Expected: FAIL with the current bare-import error.

- [ ] **Step 3: Implement package-safe imports**

Mirror the existing `_lib/post_flow_analysis.py` bootstrap or use a canonical package import that works under the global `rddf` launcher and project-local install. Do not duplicate competing module implementations.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_cli_reporter.py -v`; then run `rddf issue list` and `rddf report-issue --no-submit` from an isolated third-party project.
Expected: PASS with issue files under the third-party `.rddf/issues` directory.

- [ ] **Step 5: Defer commit**

Keep the change in the aggregate execute commit.

### Task 5: Align upstream reporting policy and configuration

**Files:**
- Modify: `_lib/post_flow_analysis.py`
- Modify: `_lib/issue_reporter.py`
- Modify: `_lib/config.py`
- Modify: `_lib/core/defaults.py`
- Modify: `_lib/schemas/config_schema.json`
- Test: `tests/unit/test_issue_reporter.py`
- Test: `tests/unit/test_cli_reporter.py`

- [ ] **Step 1: Write the failing tests**

Mock `gh` and assert default `--repo chisuhua/rdd-workflow`, explicit `RDDF_REPORT_GH_REPO` override, dedup lookup before create, CI suppression, category allowlist, and local file retention on `gh` failure.

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/unit/test_issue_reporter.py tests/unit/test_cli_reporter.py -k 'repo or submit or config or ci or dedup' -v`
Expected: FAIL for any declared configuration that currently has no runtime effect.

- [ ] **Step 3: Implement one effective configuration contract**

Keep local buffering unconditional for reportable classifications. Keep GitHub submission opt-in and category-filtered. Make `RDDF_REPORT_GH_REPO` the documented upstream selector and either wire `reporting.destination/config` end-to-end or remove unsupported values; do not silently accept configuration that changes nothing.

- [ ] **Step 4: Run tests to verify they pass**

Run the targeted pytest command and inspect captured `gh` argv. Expected: all paths use the intended upstream repository and preserve local issue files on failure.

- [ ] **Step 5: Defer commit**

Keep the change in the aggregate execute commit.

### Task 6: Harden archive close and installation documentation

**Files:**
- Modify: `_lib/close_issues.py`
- Modify: `_lib/archive.sh`
- Modify: `skills/guide-ship/scripts/ship_archive.sh`
- Modify: `install.sh`
- Modify: `skills/INSTALL.md`
- Test: `tests/unit/test_close_issues.py`
- Test: `tests/integration/test_archive_worktree_close_hook.bats`
- Test: `tests/integration/test_archive_lightweight_close_hook.bats`

- [ ] **Step 1: Write the failing tests**

Add tests for third-party archive with no upstream push permission, hostile change-name argument handling, correct version forwarding, and installer invocation of the orchestrator environment hook. Add documentation assertions for global replay and upstream issue submission.

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/unit/test_close_issues.py -v` and the two archive bats files.
Expected: FAIL on current string interpolation/import-path/version behavior or missing installer hook invocation.

- [ ] **Step 3: Implement safe non-blocking close/install behavior**

Pass archive values through argv/env, resolve the tool module independently from the project root, preserve manual-link fallback, invoke the intended installer hook, and document commands/paths/policy without changing L2 default-off behavior.

- [ ] **Step 4: Run tests to verify they pass**

Run the targeted close-hook, installer, and documentation tests. Expected: archive remains successful when close is unavailable and docs match runtime behavior.

- [ ] **Step 5: Defer commit**

Keep the change in the aggregate execute commit.

### Task 7: Run full third-party end-to-end validation

**Files:**
- Modify: `tests/integration/test_global_install_external_project.bats`
- Modify: `openspec/changes/complete-third-party-replay-and-upstream-reporting/tasks.md`

- [ ] **Step 1: Write the failing end-to-end test**

Create an isolated third-party Git repository with `.rddf/state`, run a wrapped failing command through the installed helper, finalize, replay from a child directory, and submit with a mocked `gh`. Assert all state belongs to the third-party root and the captured repo is `chisuhua/rdd-workflow`.

- [ ] **Step 2: Run the test to verify failure**

Run: `bats tests/integration/test_global_install_external_project.bats`
Expected: FAIL against the current helper lookup, finalize reporting, or CLI import behavior.

- [ ] **Step 3: Integrate only minimal compatibility changes**

Adjust only code paths already covered by Tasks 1-6. Do not add a second reporting pipeline or expand into dedup unification/realtime streaming.

- [ ] **Step 4: Run the complete targeted suite**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py tests/unit/test_cli_reporter.py tests/unit/test_issue_reporter.py tests/unit/test_close_issues.py -q` and `bats tests/integration/test_global_install_external_project.bats tests/integration/test_orchestrator_default_on.bats tests/integration/test_archive_worktree_close_hook.bats tests/integration/test_archive_lightweight_close_hook.bats`.
Expected: PASS except explicitly documented pre-existing environmental timing failures.

- [ ] **Step 5: Defer commit**

Keep the change in the aggregate execute commit.

### Task 8: Validate, update progress, and commit

**Files:**
- Modify: `openspec/changes/complete-third-party-replay-and-upstream-reporting/tasks.md`
- Modify: `.rddf/plans/complete-third-party-replay-and-upstream-reporting.md`

- [ ] **Step 1: Write the failing validation command**

Run `openspec validate complete-third-party-replay-and-upstream-reporting --json`, targeted tests, and `git diff --check`; record any pre-existing failures separately.

- [ ] **Step 2: Run validation and inspect failures**

Expected before completion: any failures identify either an implementation regression or the known environment-only event-log timing assertion; do not delete tests or baseline failures to force green.

- [ ] **Step 3: Apply only change-owned fixes**

Fix failures caused by this change, mark the corresponding OpenSpec tasks and plan checkboxes complete, and leave unrelated pre-existing failures documented.

- [ ] **Step 4: Run final verification**

Run `openspec validate complete-third-party-replay-and-upstream-reporting --json`, the complete targeted suite, `git diff --check`, and the project regression command available within the environment budget.

- [ ] **Step 5: Commit aggregate implementation**

In the lightweight branch, inspect status/diff, stage only implementation/tests/docs/tasks for this change, and create one conventional commit. Do not archive until the commit exists and the full regression gate has been attempted.
