# general Specification

## Purpose
TBD - created by archiving change add-skill-bats-tests. Update Purpose after archive.
## Requirements
### Requirement: general-add-skill-bats-tests
The system SHALL provide add-skill-bats-tests functionality.

#### Scenario: Successful execution
- **WHEN** user invokes the feature
- **THEN** system implements add-skill-bats-tests correctly

### Requirement: general-implement-deps-subagent-analysis
The system SHALL provide implement-deps-subagent-analysis functionality.

#### Scenario: Successful execution
- **WHEN** user invokes the feature
- **THEN** system implements implement-deps-subagent-analysis correctly

### Requirement: general-init-adr-directory
The system SHALL provide init-adr-directory functionality.

#### Scenario: Successful execution
- **WHEN** user invokes the feature
- **THEN** system implements init-adr-directory correctly

### Requirement: general-harden-doc-consistency
The system SHALL harden documentation and code consistency for spec-workflow v1.1 by removing orphan bash helpers, fixing hardcoded branch references, and synchronizing all docs with actual code state.

#### Scenario: Orphan bash helpers removed
- **WHEN** `_lib/state.sh` is inspected
- **THEN** it SHALL NOT export `safe_python_json`, `safe_python_yaml`, `read_suggestions`, or `write_suggestions` (zero call sites confirmed)
- **AND** the file SHALL either be removed entirely or reduced to a stub

#### Scenario: is_change_committed removed
- **WHEN** `_lib/worktree.sh` is inspected
- **THEN** it SHALL NOT export `is_change_committed` (zero call sites confirmed)

#### Scenario: Duplicate wt_path_for_branch_inline removed
- **WHEN** `skills/status.md` and `skills/execute.md` are inspected
- **THEN** neither SHALL define an inline `wt_path_for_branch_inline` function
- **AND** both SHALL call `_lib/worktree.sh::wt_path_for_branch` (after sourcing)

#### Scenario: find_default_branch works in worktree context
- **WHEN** `find_default_branch` is called from inside a worktree
- **THEN** it SHALL return the project's default branch (`master`/`main`/`develop`)
- **AND** it SHALL NOT return the worktree's own `openspec/<name>` branch as fallback

### Requirement: general-docs-match-code
All user-facing documentation in `USAGE.md`, `README.md`, `docs/adr/*.md`, `skills/*.md`, and `tests/README.md` SHALL accurately reflect the actual code state as of the change's commit.

#### Scenario: USAGE.md ship-side phase count
- **WHEN** `USAGE.md` is read
- **THEN** it SHALL describe ship-side as `5 阶段 + 1 退出` (plan / execute / archive / cleanup + ship-done)
- **AND** it SHALL list the phase sequence as `plan → execute → archive → cleanup`

#### Scenario: USAGE.md state-file table
- **WHEN** `USAGE.md` is read
- **THEN** the state-file table SHALL include `proposal-suggestions.md`, `tasks.md`, `docs/adr/ADR-*.md`, `.sisyphus/plans/<name>.md`, `.zcf/.handoff.json`, `.zcf/.roadmap-state.json`, `.zcf/.deps-candidates.json`, `.zcf/.deps-output.md`, and `.zcf/index.md`

#### Scenario: skill files do not hardcode main branch
- **WHEN** `skills/*.md` is searched for the literal word "main 分支" or "main branch" in user-facing output
- **THEN** it SHALL NOT appear (use `${DEFAULT_BRANCH:-master}` or dynamic detection instead)

#### Scenario: status.md sample output uses generic paths
- **WHEN** `skills/status.md` L68-70 is read
- **THEN** the sample `git worktree list` output SHALL use `/path/to/PROJECT_ROOT` (not `/path/to/CppHDL`)

#### Scenario: ADR-0001 reflects actual architecture
- **WHEN** `docs/adr/ADR-0001-propose-plan-execute-state-machine.md` is read
- **THEN** its Decision section SHALL list spec-side as 5 phases (setup/roadmap/propose/deps/spec-done) and ship-side as 5 phases + 1 exit (plan/execute/archive/cleanup/ship-done)
- **AND** it SHALL list 10 subskills (not 9)

#### Scenario: INSTALL.md version matches package.json
- **WHEN** `skills/INSTALL.md` is read
- **THEN** its version SHALL be `1.1.0` (matching `package.json`)
- **AND** its embedded package.json heredoc SHALL include `prometheus-planning` in the skills array

#### Scenario: proposal-suggestions-format lists all 5 consumers
- **WHEN** `docs/proposal-suggestions-format.md` is read
- **THEN** the consumer list SHALL include `propose`, `guide-spec`, `guide`, `status`, and `deps` (not just the first 4)

#### Scenario: propose.md uses 4-digit ADR pattern
- **WHEN** `skills/propose.md` L193 is read
- **THEN** the regex SHALL use `ADR-NNNN` (4-digit) to match `docs/adr/README.md` convention

#### Scenario: tests/README.md matches actual file layout
- **WHEN** `tests/README.md` Layout section is read
- **THEN** it SHALL include `smoke.bats` and `test_helper.bash` at the root
- **AND** it SHALL list actual files in `tests/_lib/` (including `deps-subagent.bash`)

