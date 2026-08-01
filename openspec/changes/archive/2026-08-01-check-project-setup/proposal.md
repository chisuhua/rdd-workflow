## Why

The rdd-workflow runtime relies on a clear `.gitignore` contract: `.rddf/state/`, `.rddf/wt/`, `.rddf/detectors/`, and `.rddf/actions/` are runtime-only and must be ignored, while `.rddf/plans/` must remain tracked. Today the COMMIT GATE in `guide-ship` hard-blocks when required artifacts are not committed, but the complementary check that runtime directories are ignored is only a soft suggestion in the `guide` recommender. This asymmetry lets downstream projects accidentally track runtime state. This change introduces a reusable project-setup helper that hard-blocks `guide-arch` Phase 1 when critical ignore rules are missing, surfaces setup issues in the `guide` recommender, and adds a post-install sanity checklist to `INSTALL.md`.

## What Changes

- Add `skills/_lib/check_project_setup.sh` exposing a single function `check_project_setup <project_root>` that writes a JSON issue array to stdout.
- Add `tests/integration/test_check_project_setup.bats` covering the six checks and JSON schema compliance.
- Integrate the helper into `skills/guide-arch/scripts/arch_env_check.sh` as a hard gate before arch-done; any `severity == error` issue with `status == fail` causes `return 1`.
- Integrate the helper into `skills/guide/scripts/scan-state.sh` as a non-blocking pre-menu analysis that presents all issues as `safe_auto_fix` candidates.
- Add Section 5 "项目设置检查" to `skills/INSTALL.md` that prints a friendly checklist after installation.
- Update `USAGE.md` "常见陷阱" and `docs/v2-workflow-overview.md` with a short note explaining when the project-setup check runs and what users should expect.
- Refactor `tests/integration/test_plan_review_phase.bats:62-66` to assert through the new helper instead of duplicating `.gitignore` inspection logic.

## Capabilities

### New Capabilities

- `project-setup-check`: Validates that a downstream project's `.gitignore` and git state satisfy rdd-workflow runtime assumptions before workflow entry points run.

### Modified Capabilities

(none — no existing spec-level behavior changes)

## Impact

- Affects `guide-arch` Phase 1 hard gate, `guide` recommender soft analysis, `INSTALL.md` post-install UX, and one existing bats test assertion. Does not change source-code behavior outside setup verification. Does not require a new ADR.
