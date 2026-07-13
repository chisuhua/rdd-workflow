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

The system SHALL ensure all user-facing documentation in `USAGE.md`, `README.md`,
`docs/adr/*.md`, `skills/*.md`, and `tests/README.md` accurately reflects the
actual code state as of the change's commit. The locked fields enumerated in
the Scenarios below SHALL additionally be enforced by the anti-drift tests
introduced in `openspec/specs/doc-truth-sync/spec.md::Requirement doc-contract-tests-required`.

#### Scenario: USAGE.md ship-side phase count

- **WHEN** `USAGE.md` is read
- **THEN** it SHALL describe ship-side as **7 numbered subphases (Phase 1, 1.5,
  2, 2.5, 3, 4, 5)** with sequence
  `plan → verification → execute → review → archive → cleanup → ship-done`
- **AND** it SHALL NOT describe ship-side as "5 phases + 1 exit" (the v1.x
  model is stale as of v2.0.1)
- **AND** Phase 2.5 Review SHALL be explicitly named (execute 后债务扫描)

#### Scenario: USAGE.md state-file table uses dotted prefix convention

- **WHEN** `USAGE.md` is read
- **THEN** the state-file table SHALL list only files that exist on disk
- **AND** all state files SHALL match production paths — specifically:
  - `.rddf/state/.arch-handoff.json`
  - `.rddf/state/.plan-handoff.json`
  - `.rddf/state/deps-analysis.json`
  - `.rddf/state/.deps-candidates.json`
  - `.rddf/state/.deps-output.md` (with legacy undotted path noted as compat)
  - `.rddf/state/sessions.json`
  - `.rddf/state/iteration.json`
  - `.rddf/state/index.md`
  - `.rddf/state/roadmap-state.json` and/or `.rddf/state/.roadmap-state.json` only if the doc explicitly labels which one is canonical and which one is legacy/compat
- **AND** the table SHALL NOT contain `handoff.json` (undotted) or
  `.sisyphus/plans/<name>.md` (wrong directory)
- **AND** `proposal-suggestions.md` at project root SHALL remain undotted
  (git-tracked, intentional)

#### Scenario: USAGE.md describes lightweight and worktree ship modes

- **WHEN** `USAGE.md` is read
- **THEN** it SHALL describe ship-side as supporting two execution modes:
  - **⚡ 轻量模式 (lightweight)**: no other worktree AND only this one change,
    creates `openspec/<name>` branch directly in main repo (skipping worktree)
  - **🔀 worktree 模式**: active worktree OR multiple changes, creates
    `.rddf/wt/<name>` isolated worktree
- **AND** it SHALL explain that lightweight mode skips the
  `git worktree remove` step during archive (no worktree to remove)

#### Scenario: package.json skills array aligns with INSTALL.md description

- **WHEN** `package.json::skills[]` is read
- **AND** `ls skills/*.md | wc -l` is computed
- **THEN** the difference SHALL be 0
- **AND** `package.json` SHALL NOT contain a `_comment` field (Decision 3 翻 A 后所有 skill 都通过 npm 发布,无 src-only 例外)
- **AND** `skills/INSTALL.md` description SHALL NOT enumerate skill names or state a src-only delta(描述应采用计数式,如"详见 skills/ 目录")
- **AND** upstream `package.json` MUST contain `feature` and `rddf-session`(Decision 3 = A 已锁定)

#### Scenario: status.md sample output uses generic paths

- **WHEN** `skills/status.md` L68-70 is read
- **THEN** the sample `git worktree list` output SHALL use `/path/to/PROJECT_ROOT`
  (not `/path/to/CppHDL`)
- **AND** any historical `/path/to/CppHDL` references SHALL be flagged
  drift-ignore

#### Scenario: skill files do not hardcode main branch

- **WHEN** `skills/*.md` is searched for the literal word "main 分支" or
  "main branch" in user-facing output
- **THEN** it SHALL NOT appear (use `${DEFAULT_BRANCH:-master}` or dynamic
  detection via `find_default_branch()` instead)

#### Scenario: ADR-0001 reflects actual three-phase architecture

- **WHEN** `docs/adr/ADR-0001-propose-plan-execute-state-machine.md` is read
- **THEN** its Decision section SHALL list spec-side as 5 phases
  (setup/adr-create/architecture/roadmap-define/arch-done per `guide-arch`)
  and ship-side as **7 numbered subphases (Phase 1, 1.5, 2, 2.5, 3, 4, 5)**
- **AND** it SHALL list current subskills including `feature` and
  `rddf-session` (13 on disk total, 13 in package.json publish set — Decision 3 = A)

#### Scenario: INSTALL.md version matches package.json

- **WHEN** `skills/INSTALL.md` is read
- **THEN** its version field SHALL match `package.json::version`
- **AND** its embedded package.json heredoc SHALL derive the `skills` array
  from the actual `package.json` (using python3 json.load, not hardcoded list)
- **AND** its description SHALL include the disk count (13) matching
  `package.json::skills[]` length (Decision 3 = A 已锁定,无 src-only 例外);
  不应出现"13 vs 11"或"src-only delta"等表述

#### Scenario: proposal-suggestions-format consumer list is current

- **WHEN** `docs/proposal-suggestions-format.md` is read
- **THEN** the consumer list SHALL include `propose`, `guide-arch`,
  `guide-plan`, `guide`, `status`, and `deps`
- **AND** it SHALL NOT list `guide-spec` (removed in v2.0)
- **AND** `roadmap` SHALL be listed if it consumes the format

#### Scenario: propose.md uses 4-digit ADR pattern

- **WHEN** `skills/propose.md` L193 is read
- **THEN** the regex SHALL use `ADR-NNNN` (4-digit) to match
  `docs/adr/README.md` convention

#### Scenario: tests/README.md matches actual file layout

- **WHEN** `tests/README.md` Layout section is read
- **THEN** it SHALL include `smoke.bats` and `test_helper.bash` at the root
- **AND** it SHALL list actual files in `tests/_lib/` (including
  `deps-subagent.bash`)
- **AND** test counts SHALL match `ls tests/unit/*.py | wc -l` and
  `ls tests/integration/*.bats | wc -l`

#### Scenario: npm test vs pytest caveat is locked

- **WHEN** `package.json::scripts.test` is read
- **THEN** it SHALL contain exactly `bats tests/` (and nothing else that would
  make `npm test` also invoke pytest)
- **AND** `USAGE.md` and `AGENTS.md` SHALL each contain a visible warning
  reminding readers that `npm test` does NOT run pytest
- **AND** the `doc-contract-tests-required` test in
  `openspec/specs/doc-truth-sync/spec.md` SHALL enforce this Scenario

