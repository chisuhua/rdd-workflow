## ADDED Requirements

### Requirement: general-status-guide-skill-revision

The skill documentation at `skills/guide.md` and `skills/status.md` SHALL accurately reflect the codebase state, ship with bats regression tests locking the structural and content invariants, and never contain known correctness or safety defects catalogued in the audit log.

#### Scenario: Frontmatter version key uniqueness

- **WHEN** `skills/guide.md` or `skills/status.md` frontmatter `metadata:` block is parsed with PyYAML
- **THEN** it SHALL contain AT MOST one `version:` key per block
- **AND** `metadata.version` SHALL resolve to the most-recent semver string declared in that block

#### Scenario: Status Mode A status vocabulary unification

- **WHEN** `status.md` Mode A dynamic status block is read
- **THEN** it SHALL mention each iteration.json status (planned / proposed / in_worktree / completed / archived)
- **AND** a "💼 committed" or equivalent state SHALL exist for changes committed to HEAD without a worktree
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
