# general Specification

## Purpose
TBD - cross-cutting documentation / contract sync requirement (v2.0.2 sync-workflow-contracts).
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
All user-facing documentation in `USAGE.md`, `README.md`, `docs/adr/*.md`, `skills/*.md`, and `tests/README.md` SHALL accurately reflect the actual code state as of the change's commit (v2.0.2 sync-workflow-contracts).

#### Scenario: USAGE.md ship-side phase count (v2.0.1)
- **WHEN** `USAGE.md` is read
- **THEN** it SHALL describe ship-side as **7 编号子阶段** (numbered subphases: Phase 1, 1.5, 2, 2.5, 3, 4, 5 — plan / verification / execute / review / archive / cleanup / ship-done)
- **AND** it SHALL NOT contain the legacy 五阶段加一退出描述 (legacy: 五阶段 plus 退出)
- **AND** it SHALL list the phase sequence as `plan → verification → execute → review → archive → cleanup → ship-done`

#### Scenario: USAGE.md state-file table (v2.0.1 dotted canonical paths)
- **WHEN** `USAGE.md` is read
- **THEN** the state-file table SHALL include `proposal-suggestions.md`, `openspec/changes/<name>/tasks.md`, `docs/adr/ADR-*.md`, `.rddf/plans/<name>.md`, `.rddf/state/.arch-handoff.json`, `.rddf/state/.plan-handoff.json`, `.rddf/state/roadmap-state.json`, `.rddf/state/deps-analysis.json`, `.rddf/state/iteration.json`, `.rddf/state/sessions.json`, `.rddf/state/.deps-candidates.json`, `.rddf/state/.deps-output.md`, and `.rddf/state/index.md`
- **AND** it SHALL NOT reference the legacy undotted `.rddf/state/handoff.json` (replaced by `.arch-handoff.json` / `.plan-handoff.json`)
- **AND** it SHALL NOT reference the legacy plan path under `.sisyphus/` (replaced by `.rddf/plans/<name>.md`)

#### Scenario: skill files do not hardcode main branch
- **WHEN** `skills/*.md` is searched for the literal word "main 分支" or "main branch" in user-facing output
- **THEN** it SHALL NOT appear (use `${DEFAULT_BRANCH:-master}` or dynamic detection instead)

#### Scenario: status.md sample output uses generic paths
- **WHEN** `skills/status.md` L68-70 is read
- **THEN** the sample `git worktree list` output SHALL use `/path/to/PROJECT_ROOT` (not `/path/to/CppHDL`)

#### Scenario: ADR-0001 reflects actual architecture (v2.0.1 supersession)
- **WHEN** `docs/adr/ADR-0001-propose-plan-execute-state-machine.md` is read
- **THEN** its Decision section SHALL list spec-side as 5 phases (setup/roadmap/propose/deps/spec-done) and ship-side as **7 编号子阶段** (plan/verification/execute/review/archive/cleanup/ship-done, v2.0.1 supersedes v1.x 五阶段加一退出)
- **AND** it SHALL reference the **three-phase** consumers `guide-arch`, `guide-plan`, `guide-ship` (NOT the v1.x spec-side 别名 that merged arch + plan)
- **AND** it SHALL list **13 subskills** (NOT v1.x 9 or v1.x 10)

#### Scenario: INSTALL.md version matches package.json
- **WHEN** `skills/INSTALL.md` is read
- **THEN** its version SHALL be `1.1.0` (matching `package.json`)
- **AND** its embedded package.json heredoc SHALL include `feature` + `rddf-session` in the skills array (Decision 3 = A, v2.0.2 publishes all 13)

#### Scenario: proposal-suggestions-format consumers list v2.0+
- **WHEN** `docs/proposal-suggestions-format.md` is read
- **THEN** the consumer list SHALL include `propose`, `guide`, `status`, `deps`, `guide-arch`, `guide-plan`, `guide-ship` (NOT the v1.x spec-side 别名 that merged arch + plan)

#### Scenario: propose.md uses 4-digit ADR pattern
- **WHEN** `skills/propose.md` L193 is read
- **THEN** the regex SHALL use `ADR-NNNN` (4-digit) to match `docs/adr/README.md` convention

#### Scenario: tests/README.md matches actual file layout
- **WHEN** `tests/README.md` Layout section is read
- **THEN** it SHALL include `smoke.bats` and `test_helper.bash` at the root
- **AND** it SHALL list actual files in `tests/_lib/` (including `deps-subagent.bash`)

#### Scenario: package.json::skills[] publishes all 13 disk skills (Decision 3 = A)
- **WHEN** `package.json::skills[]` is read
- **THEN** it SHALL contain 13 entries matching `ls skills/*.md` exactly (INSTALL + guide + guide-arch + guide-plan + guide-ship + feature + rddf-session + propose + execute + status + roadmap + deps + spec-workflow-writing-plans)
- **AND** it SHALL NOT define a `_comment` field (Decision 3 = A path, no src-only exceptions)

#### Scenario: AGENTS.md skill + ADR counts reflect disk
- **WHEN** `AGENTS.md` is read
- **THEN** it SHALL state **13 个 .md** (skills count matching disk)
- **AND** it SHALL state **ADR-0001~0019 (19 个唯一编号 / 20 个实体文件; ADR-0013 重复)** in the docs/adr/ description

#### Scenario: docs/adr/README.md status table covers all real ADRs (0001-0019) with ADR-0013 dup flag
- **WHEN** `docs/adr/README.md` is read
- **THEN** the v2.0 status table SHALL include ADR rows for 0001 through 0019 (with ADR-0013 row explicitly flagged ⚠️重复)
- **AND** it SHALL NOT reference ADR numbers beyond 0019