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

### Requirement: general-status-guide-skill-revision

The skill documentation at `skills/guide.md` and `skills/status.md` SHALL accurately reflect the codebase state, ship with bats regression tests locking the structural and content invariants, and never contain known correctness or safety defects catalogued in the audit log.

#### Scenario: Frontmatter version key uniqueness

- **WHEN** `skills/guide.md` or `skills/status.md` frontmatter `metadata:` block is parsed with PyYAML
- **THEN** it SHALL contain AT MOST one `version:` key per block
- **AND** `metadata.version` SHALL resolve to the most-recent semver string declared in that block

#### Scenario: Status Mode A status vocabulary unification

- **WHEN** `status.md` Mode A dynamic status block is read
- **THEN** it SHALL mention **all six** iteration.json schema states: `planned`, `proposed`, `in_worktree`, `review`, `completed`, `archived`
- **AND** the previously-undocumented `review` state SHALL be explicitly visible (it was missing from the pre-change doc despite being a valid schema state since v2.0)
- **AND** Mode A SHALL also classify and surface the "💼 committed-no-wt" display-time state — distinct from any schema state — for changes committed to HEAD where no worktree exists yet
- **AND** the placeholder string "⏸ 暂停" SHALL NOT appear in the Mode A table template

#### Scenario: Status Mode C archive confirmation gate

- **WHEN** `status.md` Mode C Step 1-5 is read
- **THEN** a user-confirmation block (`read -r` / `confirm` / `case "yes"`) SHALL appear BEFORE the first reference to `archive_change`
- **AND** a `--yes` or `-y` CLI flag SHALL provide a non-interactive bypass for CI usage

#### Scenario: Status Mode B path uniformity

- **WHEN** `status.md` Mode B `PLAN_FILE` and `TASKS_FILE` variables are read
- **THEN** both SHALL be prefixed with `$PROJECT_ROOT`
- **AND** `source "$SCRIPT_DIR/_lib/worktree.sh"` SHALL NOT appear at the top of the file
- **AND** the awk column comment (around line 382) SHALL mention all three of `$1` (path), `$2` (commit hash), `$3` ("[branch]")

#### Scenario: Status Mode D python uses os.environ

- **WHEN** `status.md` Mode D `python3 -c` invocations are read
- **THEN** path access SHALL go through `os.environ["PROJECT_ROOT"]` instead of bash `$PROJECT_ROOT` interpolation into Python source

#### Scenario: Status Mode E no exec $0 + uses list_planned helper

- **WHEN** `status.md` Mode E Step 3 is read
- **THEN** it SHALL NOT contain `exec $0`
- **AND** Mode E Step 2b SHALL use `iteration.list_planned()` from `skills/_lib/iteration.py` rather than calling `json.load(open(...))` directly

#### Scenario: guide binding skip + flags

- **WHEN** `skills/guide.md` top-level input handling is read
- **THEN** it SHALL document graceful-skip semantics when `BINDING_LINES` is empty (no `📍 No current binding` line printed by default)
- **AND** `--help` and `--no-binding` CLI flags SHALL be supported

#### Scenario: scan-state.sh priority count alignment

- **WHEN** `skills/_lib/scan-state.sh` priority comment block is read
- **THEN** the number of numbered priority entries (1, 1.5, 2, 2.5, 3-10 = 12) SHALL match the count claimed in `skills/guide.md`
- **AND** `scan_state()` header SHALL include a `# EXPORTED_VARS: {RECOMMEND REASON}` declaration line

#### Scenario: stale workflow-state.md runtime check

- **WHEN** `scan_state()` is invoked on a project root containing a `workflow-state.md` (pre-refactor format)
- **THEN** `check_stale_workflow_state()` SHALL emit a one-line warning with the message "Stale workflow-state.md detected"
- **AND** the warning SHALL NOT auto-delete the file

#### Scenario: status output style guide

- **WHEN** `skills/status.md` "输出风格指南" subsection is read
- **THEN** it SHALL define a locked emoji vocabulary covering 🔍 💡 ⚠️ ✅ ❌ 📋 🎉 💼 🔧 ✔ 📦
- **AND** it SHALL prescribe alignment rules for the Mode A progress column

#### Scenario: regression suite covers all 12 work-units

- **WHEN** the bats test sweep runs (`bats tests/smoke.bats tests/integration/test_*_*.bats`)
- **THEN** it SHALL include baseline 16 cases + 30+ new cases from `tests/integration/test_frontmatter_dupkey.bats`, `test_status_state_table.bats`, `test_archive_confirmation.bats`, `test_scan_state_doc.bats`, `test_status_mode_router.bats`, `test_status_mode_b_path_hygiene.bats`, `test_status_mode_d_env_safe.bats`, `test_status_mode_e_exec_safe.bats`, `test_status_mode_a_polish.bats`, `test_guide_binding_skip.bats`, `test_stale_workflow_state.bats`, `test_skill_style_guide.bats`
- **AND** total ≥ 46 cases SHALL be green

#### Scenario: status.md top-level mode router (S8)

- **WHEN** `status.md` "## 输入" subsection is read
- **THEN** it SHALL contain a top-level `case "$1" in` dispatcher that routes user input to Mode A (no args), Mode B (change name), Mode C (with `--archive` or `--yes`), Mode D (`--roadmap` / `roadmap`), Mode E (`--iteration` / `iteration`), or a `--help` / `-h` listing

#### Scenario: status.md Mode A no longer duplicates `git worktree list` (S3)

- **WHEN** the entire `skills/status.md` file is scanned with `grep -cE "^git worktree list"`
- **THEN** the count SHALL be ≤ 1 (only the top-of-skill initialization, not duplicated in Mode A)
- **AND** Mode A's case handler in `status.md` SHALL include an `i|` branch that captures custom user input rather than falling into the wildcard `*)` arm

#### Scenario: status.md Mode A case handler accepts `i` choice (S11)

- **WHEN** `status.md` Mode A `case "$choice" in` is read
- **THEN** the case pattern list SHALL include `i|` mapping to a `read -r CUSTOM` prompt that surfaces the user's free-text intent
- **AND** the wildcard `*)` arm SHALL remain for genuinely invalid input but SHALL NOT capture `i`

