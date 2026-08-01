# ship-done-orphan-cleanup Specification

## Purpose
TBD - created by archiving change improve-ship-done-cleanup-orphan-sessions. Update Purpose after archive.
## Requirements
### Requirement: count_orphaned_sessions is read-only and returns an integer
`skills/_lib/sessions_count.sh::count_orphaned_sessions <project_root>` SHALL read `.rddf/state/sessions.json`, count sessions whose `state` equals `"orphaned"`, and echo only the count. The function SHALL be read-only, SHALL NOT modify `sessions.json`, and SHALL NOT invoke any other skill or helper.

#### Scenario: helper returns count for mixed sessions
- **GIVEN** `.rddf/state/sessions.json` contains two `orphaned` sessions, one `active` session, and one `completed` session
- **WHEN** `count_orphaned_sessions "$PROJECT_ROOT"` is called
- **THEN** it echoes `2`
- **AND** the exit code is `0`
- **AND** `sessions.json` is unchanged

#### Scenario: helper returns 0 when no orphaned sessions exist
- **GIVEN** `.rddf/state/sessions.json` contains one `active` session and zero `orphaned` sessions
- **WHEN** `count_orphaned_sessions "$PROJECT_ROOT"` is called
- **THEN** it echoes `0`
- **AND** the exit code is `0`

### Requirement: helper tolerates missing or corrupt sessions.json
`count_orphaned_sessions` SHALL echo `0` and exit `0` when `.rddf/state/sessions.json` is missing, unreadable, or contains invalid JSON. The caller SHALL NOT be blocked by a broken state file.

#### Scenario: sessions.json does not exist
- **GIVEN** `.rddf/state/sessions.json` does not exist
- **WHEN** `count_orphaned_sessions "$PROJECT_ROOT"` is called
- **THEN** it echoes `0`
- **AND** the exit code is `0`
- **AND** no error is printed to stdout

#### Scenario: sessions.json contains invalid JSON
- **GIVEN** `.rddf/state/sessions.json` contains the text `{not valid json}`
- **WHEN** `count_orphaned_sessions "$PROJECT_ROOT"` is called
- **THEN** it echoes `0`
- **AND** the exit code is `0`
- **AND** no error is printed to stdout

### Requirement: ship-done menu shows an orphan warning and option 5 when orphans exist
`skills/guide-ship/scripts/ship_done.sh::check_remaining_work` SHALL call `count_orphaned_sessions`. When the count is greater than zero, it SHALL print a warning line listing the first three orphaned session IDs followed by a cleanup suggestion, and SHALL append option 5 (`🧹 清理 N 个 orphaned sessions ...`) before the `i. 其他输入` fallback.

#### Scenario: three orphans and no remaining changes
- **GIVEN** `.rddf/state/sessions.json` contains three sessions with ids `rds_a1b5`, `rds_1221`, and `rds_0569` and `state == "orphaned"`
- **AND** zero active worktrees and zero unprocessed changes
- **WHEN** `check_remaining_work "$PROJECT_ROOT"` is called
- **THEN** the output contains `✅ 所有 changes 已处理完毕`
- **AND** the output contains `⚠️ 发现 3 个 orphaned rddf-sessions (rds_a1b5, rds_1221, rds_0569)`
- **AND** the output contains `建议清理:`
- **AND** the output contains option `5. 🧹 清理 3 个 orphaned sessions`
- **AND** options 1, 2, 3, 4, and `i. 其他输入` appear in the original order and wording

#### Scenario: one orphan with remaining changes
- **GIVEN** `.rddf/state/sessions.json` contains one `orphaned` session with id `rds_9999`
- **AND** one unprocessed change exists and no active worktrees
- **WHEN** `check_remaining_work "$PROJECT_ROOT"` is called
- **THEN** the output contains the `📋 还有 ...` header
- **AND** the output contains `⚠️ 发现 1 个 orphaned rddf-sessions (rds_9999)`
- **AND** the output contains option `5. 🧹 清理 1 个 orphaned sessions`
- **AND** options 1, 2, 3, 4, and `i. 其他输入` appear in the original order and wording

#### Scenario: more than three orphans show overflow summary
- **GIVEN** `.rddf/state/sessions.json` contains five sessions with ids `rds_0001`, `rds_0002`, `rds_0003`, `rds_0004`, and `rds_0005` and `state == "orphaned"`
- **AND** zero active worktrees and zero unprocessed changes
- **WHEN** `check_remaining_work "$PROJECT_ROOT"` is called
- **THEN** the warning lists `rds_0001, rds_0002, rds_0003`
- **AND** the warning ends with `... +2 more`
- **AND** the output does not contain `rds_0004` or `rds_0005`

### Requirement: ship-done menu is unchanged when no orphans exist
When `count_orphaned_sessions` returns `0`, `check_remaining_work` SHALL produce output that is byte-for-byte identical to the pre-change implementation for the same remaining-change state. No orphan warning or option 5 SHALL appear.

#### Scenario: no orphans and no remaining changes
- **GIVEN** `.rddf/state/sessions.json` does not exist
- **AND** zero active worktrees and zero unprocessed changes
- **WHEN** `check_remaining_work "$PROJECT_ROOT"` is called
- **THEN** the output contains exactly the four options 1-4 and `i. 其他输入` in the original order and wording
- **AND** the output does not contain `orphaned`
- **AND** the output does not contain option `5.`

#### Scenario: no orphans with remaining changes
- **GIVEN** `.rddf/state/sessions.json` contains one `active` session and zero `orphaned` sessions
- **AND** one unprocessed change exists and no active worktrees
- **WHEN** `check_remaining_work "$PROJECT_ROOT"` is called
- **THEN** the output contains the `📋 还有 ...` header
- **AND** the output does not contain `orphaned`
- **AND** the output does not contain option `5.`
- **AND** options 1, 2, 3, 4, and `i. 其他输入` appear in the original order and wording

### Requirement: ship-done orphan cleanup is not automatic
Option 5 SHALL only print a menu item that tells the user how to invoke `rddf-session` cleanup. The `guide-ship` ship-done menu SHALL NOT call `abandon`, `archive-history`, or any other mutating rddf-session command automatically.

#### Scenario: option 5 is a prompt, not an action
- **GIVEN** `.rddf/state/sessions.json` contains one `orphaned` session
- **WHEN** `check_remaining_work "$PROJECT_ROOT"` is called
- **THEN** the output for option 5 contains the literal text `skill_use("rddf-session", "abandon", ...)` or `archive-history`
- **AND** `check_remaining_work` does not write to `.rddf/state/sessions.json`
- **AND** `check_remaining_work` does not invoke any rddf-session subcommand

### Requirement: line-count constraints are preserved
The total new production code SHALL not exceed 50 lines: `ship_done.sh` ≤ 30 lines and `skills/_lib/sessions_count.sh` ≤ 20 lines.

#### Scenario: source files stay within budget
- **WHEN** the implementation is complete
- **THEN** `wc -l < skills/guide-ship/scripts/ship_done.sh` is ≤ 30
- **AND** `wc -l < skills/_lib/sessions_count.sh` is ≤ 20
- **AND** the sum of the two is ≤ 50

