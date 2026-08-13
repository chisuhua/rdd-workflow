# Tasks: complete-third-party-replay-and-upstream-reporting

## 1. Root resolution and global helper distribution

- [ ] 1.1 Write failing tests for explicit `RDDF_PROJECT_ROOT`, Git-root fallback, and cwd fallback.
- [ ] 1.2 Write failing tests proving helper `BASH_SOURCE` does not become the business project root.
- [ ] 1.3 Implement shared tool-root/project-root resolution contract for CLI and shell helpers.
- [ ] 1.4 Add global-install fallback for `orchestrator_entry.sh` and `post_flow_wrap.sh`.
- [ ] 1.5 Add regression tests for source checkout, global install, and project-local install.
- [ ] 1.6 Verify no trace/session/issue artifact is written under the tool repository.

## 2. Trace persistence and replay

- [ ] 2.1 Write failing pytest for default trace directory based on `RDDF_PROJECT_ROOT`.
- [ ] 2.2 Write failing integration test for `rddf orchestrate show` from project root.
- [ ] 2.3 Write failing integration test for the same replay from a project subdirectory.
- [ ] 2.4 Implement root-aware trace directory resolution while preserving `RDDF_TRACE_DIR` override.
- [ ] 2.5 Verify session lookup and trace replay use the third-party project state directory.

## 3. Normal finalize reporting

- [ ] 3.1 Write failing tests for reportable finalize classification creating `.rddf/issues/*.md`.
- [ ] 3.2 Write failing tests for usage/environment/SIGINT/SIGTERM classifications not writing flow-bug issues.
- [ ] 3.3 Write failing test for `report_written` false when no issue is written and true only after successful write.
- [ ] 3.4 Implement `orchestrate finalize -> report_flow_bug` with non-blocking reporter failure handling.
- [ ] 3.5 Verify finalize always appends a trace event and preserves the original subprocess result.

## 4. Reporter CLI imports and local buffering

- [ ] 4.1 Write failing tests reproducing `rddf issue list` and `rddf report-issue --no-submit` import failures.
- [ ] 4.2 Add package-safe reporter imports for `issue_cmd.py` and `report_issue_cmd.py`.
- [ ] 4.3 Write tests for local issue creation/list/show in a third-party project.
- [ ] 4.4 Write tests for missing `gh`, timeout, and non-zero `gh` exit preserving the local issue.
- [ ] 4.5 Verify source, global, and project-local installation modes.

## 5. Upstream submission and reporting configuration

- [ ] 5.1 Write failing tests asserting default target `chisuhua/rdd-workflow`.
- [ ] 5.2 Write failing tests asserting explicit `RDDF_REPORT_GH_REPO` is honored by manual and automatic submission.
- [ ] 5.3 Write failing tests for dedup lookup before `gh issue create`.
- [ ] 5.4 Reconcile `RDDF_REPORT_DESTINATION`, `RDDF_REPORT_GH_REPO`, category allowlist, and `config` parameter behavior.
- [ ] 5.5 Verify automatic submission remains opt-in and CI-safe.

## 6. Archive close hook hardening

- [ ] 6.1 Write failing tests for archive close in a third-party project with no upstream push permission.
- [ ] 6.2 Write a security regression test proving change names are passed through argv/env, not Python source interpolation.
- [ ] 6.3 Fix archive close import path and third-party project-root handling.
- [ ] 6.4 Fix version argument naming/forwarding and preserve non-blocking archive behavior.
- [ ] 6.5 Verify manual close links are emitted when automatic close is unavailable.

## 7. Global-install end-to-end coverage

- [ ] 7.1 Extend `test_global_install_external_project.bats` with orchestrator availability checks.
- [ ] 7.2 Add isolated external-project test for wrapped failure -> finalize -> local issue.
- [ ] 7.3 Add mocked-`gh` test verifying submission to `chisuhua/rdd-workflow`.
- [ ] 7.4 Add assertion that tool-root `.rddf/` remains unchanged.
- [ ] 7.5 Add documentation for global install, replay, local issue buffer, upstream target, and opt-in submission.

## 8. Validation and handoff

- [ ] 8.1 Run targeted pytest tests for root resolution, orchestrator finalize, reporter CLI, configuration, and close hook.
- [ ] 8.2 Run targeted bats tests for global install and external-project replay/submission.
- [ ] 8.3 Run `openspec validate complete-third-party-replay-and-upstream-reporting --json` with zero errors.
- [ ] 8.4 Run the plan-done gate and write `.rddf/state/.plan-handoff.json`.
- [ ] 8.5 Record any pre-existing environment-only test failures separately from change failures.
