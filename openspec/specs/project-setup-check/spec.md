# project-setup-check Specification

## Purpose
TBD - created by archiving change check-project-setup. Update Purpose after archive.
## Requirements
### Requirement: Helper exposes a single JSON-reporting function
The helper `skills/_lib/check_project_setup.sh` SHALL expose exactly one public function `check_project_setup <project_root>` that writes a valid JSON array to stdout and returns 0 regardless of issue status. Every gitignore-related issue's `detail` SHALL state both the detected current state (`现状`) and the required state (`期望`).

#### Scenario: Successful invocation on a passing project
- **WHEN** `check_project_setup /path/to/project` is invoked in a project with a valid `.gitignore` and no large untracked directories
- **THEN** stdout is a JSON array containing one object per check, each object has fields `name`, `status`, `severity`, `fix_command`, and `detail`; each gitignore-related `detail` includes both `现状` and `期望`

### Requirement: `.rddf/state/` must be ignored
The helper SHALL report `status: fail` with `severity: error` when `.rddf/state/` is not ignored by the project's `.gitignore`; otherwise it SHALL report `status: pass` with `severity: info`.

#### Scenario: Missing `.rddf/state/` ignore rule
- **WHEN** the project root contains a `.gitignore` file that does not ignore `.rddf/state/`
- **THEN** the helper emits an issue whose `name` is `rddf_state_ignored`, `status` is `fail`, `severity` is `error`, and `fix_command` is `echo ".rddf/state/" >> .gitignore`

#### Scenario: `.rddf/state/` correctly ignored
- **WHEN** `.gitignore` contains `.rddf/state/`
- **THEN** the helper emits an issue whose `name` is `rddf_state_ignored`, `status` is `pass`, and `severity` is `info`

### Requirement: `.rddf/wt/` must be ignored
The helper SHALL report `status: fail` with `severity: error` when `.rddf/wt/` is not ignored by the project's `.gitignore`; otherwise it SHALL report `status: pass` with `severity: info`.

#### Scenario: Missing `.rddf/wt/` ignore rule
- **WHEN** the project root contains a `.gitignore` file that does not ignore `.rddf/wt/`
- **THEN** the helper emits an issue whose `name` is `rddf_wt_ignored`, `status` is `fail`, `severity` is `error`, and `fix_command` is `echo ".rddf/wt/" >> .gitignore`

#### Scenario: `.rddf/wt/` correctly ignored
- **WHEN** `.gitignore` contains `.rddf/wt/`
- **THEN** the helper emits an issue whose `name` is `rddf_wt_ignored`, `status` is `pass`, and `severity` is `info`

### Requirement: `.rddf/plans/` must NOT be ignored
The helper SHALL detect regression cases where `.rddf/plans/` is ignored and report `status: fail` with `severity: error`.

#### Scenario: `.rddf/plans/` accidentally ignored
- **WHEN** `.gitignore` contains `.rddf/plans/`
- **THEN** the helper emits an issue whose `name` is `rddf_plans_not_ignored`, `status` is `fail`, `severity` is `error`, and `fix_command` removes the matching line from `.gitignore`

#### Scenario: `.rddf/plans/` remains tracked
- **WHEN** `.gitignore` does not contain `.rddf/plans/`
- **THEN** the helper emits an issue whose `name` is `rddf_plans_not_ignored`, `status` is `pass`, and `severity` is `info`

### Requirement: openspec CLI must be available
The helper SHALL report `status: pass` when `openspec --version` succeeds and `status: fail` with `severity: error` otherwise.

#### Scenario: openspec CLI is installed
- **WHEN** the project environment contains an `openspec` executable
- **THEN** the helper emits an issue whose `name` is `openspec_cli_available`, `status` is `pass`, and `severity` is `info`

#### Scenario: openspec CLI is missing
- **WHEN** no `openspec` executable is found in PATH
- **THEN** the helper emits an issue whose `name` is `openspec_cli_available`, `status` is `fail`, `severity` is `error`, and `fix_command` points to the rdd-workflow installation instructions

### Requirement: Git HEAD must exist
The helper SHALL report `status: pass` when the project is inside a git repository with a HEAD commit and `status: fail` with `severity: error` otherwise.

#### Scenario: Valid git repository with HEAD
- **WHEN** the project root is a git clone with at least one commit
- **THEN** the helper emits an issue whose `name` is `git_head_exists`, `status` is `pass`, and `severity` is `info`

#### Scenario: Git repository without commits
- **WHEN** the project root is a git directory but has no HEAD commit
- **THEN** the helper emits an issue whose `name` is `git_head_exists`, `status` is `fail`, `severity` is `error`, and `fix_command` is `git commit --allow-empty -m "initial commit"`

### Requirement: Large untracked directories must be reported for safe cleanup
The helper SHALL report any top-level untracked directory larger than 10MB as `status: warn` with `severity: safe_auto_fix`.

#### Scenario: Large untracked build directory exists
- **WHEN** the project root contains an untracked directory whose total size exceeds 10MB
- **THEN** the helper emits an issue whose `name` is `large_untracked_dirs`, `status` is `warn`, `severity` is `safe_auto_fix`, and `fix_command` suggests adding the directory to `.gitignore`

#### Scenario: No large untracked directories
- **WHEN** all top-level untracked directories are 10MB or smaller
- **THEN** the helper emits an issue whose `name` is `large_untracked_dirs`, `status` is `pass`, and `severity` is `info`

### Requirement: `guide-arch` Phase 1 hard-blocks on error issues
`skills/guide-arch/scripts/arch_env_check.sh` SHALL source the helper and, if any issue has `severity == error` and `status == fail`, print each failing issue's `name`, `detail`, and `fix_command`, then `return 1` to stop the phase before arch-done.

#### Scenario: Missing ignore rules during `guide-arch`
- **WHEN** `arch_env_check.sh` runs in a project whose `.gitignore` lacks `.rddf/state/`
- **THEN** the script exits with a non-zero status and the stdout contains the `fix_command` for `.rddf/state/`

#### Scenario: Passing project during `guide-arch`
- **WHEN** `arch_env_check.sh` runs in a project with all required ignore rules
- **THEN** the script continues past the setup check without blocking

### Requirement: `guide` recommender soft-presents all issues
`skills/guide/scripts/scan-state.sh` SHALL source the helper and display every issue as a `safe_auto_fix` candidate before the recommender menu, without blocking the menu or returning a failure exit code.

#### Scenario: User runs `skill_use("guide")` on a project with setup issues
- **WHEN** `scan-state.sh` runs in a project with a large untracked directory
- **THEN** the recommender prints the issue and its `fix_command` but still shows the menu and exits 0

### Requirement: `INSTALL.md` shows a post-install checklist
`skills/INSTALL.md` SHALL include Section 5 that invokes `check_project_setup`, prints a friendly checklist using ✅/❌ markers, and continues installation regardless of results.

#### Scenario: Fresh installation on a passing project
- **WHEN** the user completes `skill_use("INSTALL")`
- **THEN** Section 5 prints all checks as passing and does not block the installation

#### Scenario: Fresh installation on a project missing ignore rules
- **WHEN** the user completes `skill_use("INSTALL")` on a project without `.rddf/state/` in `.gitignore`
- **THEN** Section 5 prints a failing check with its `fix_command` and still finishes installation

