# archive-auto-commit Specification

## Purpose
Auto-commit `openspec archive` file moves (deleted active change dir → `archive/<date>-<name>/`, new spec → main specs/) via `archive.sh::commit_archive_moves` helper. Eliminates the post-archive dirty-working-tree gap; fires from `guide-ship` skill entry point (worktree `archive_change` + lightweight Phase 3). Honors `SKIP_ARCHIVE_AUTO_COMMIT=yes` opt-out; idempotent on clean tree.
## Requirements
### Requirement: `archive.sh::commit_archive_moves <name> <main_root>` MUST stage + commit the archive paths

The `skills/_lib/archive.sh` library MUST expose a function
`commit_archive_moves <name> <main_root>` that:
- Stages exactly 3 paths derived from the `openspec archive <name>` output:
  - `openspec/changes/<name>/` (the deleted active change dir)
  - `openspec/changes/archive/` (the new archive dir, contains `<date>-<name>/`)
  - `openspec/specs/` (the new main spec dir, e.g., `<new-cap>/spec.md`)
- Creates exactly 1 git commit with message `archive(<name>): archive completed`
- Runs after `openspec archive` succeeds, before any subsequent git operations
- Returns 0 on success

#### Scenario: Normal path — helper produces archive commit

- **GIVEN** working tree has uncommitted changes from `openspec archive`
- **AND** `SKIP_ARCHIVE_AUTO_COMMIT` is unset
- **WHEN** `commit_archive_moves "my-change" /repo` is called
- **THEN** exactly 1 new commit is created with message `archive(my-change): archive completed`
- **AND** working tree becomes clean afterwards

#### Scenario: Idempotent — clean working tree is a no-op

- **GIVEN** working tree is already clean (archive already committed, or never had pending moves)
- **WHEN** `commit_archive_moves "my-change" /repo` is called
- **THEN** no commit is created
- **AND** function returns 0

#### Scenario: Opt-out via env var SKIP_ARCHIVE_AUTO_COMMIT=yes

- **GIVEN** working tree has uncommitted changes from `openspec archive`
- **AND** `SKIP_ARCHIVE_AUTO_COMMIT=yes` is exported
- **WHEN** `commit_archive_moves "my-change" /repo` is called
- **THEN** no commit is created
- **AND** no `git add` is run (working tree remains dirty for human review)
- **AND** function returns 0

### Requirement: `commit_archive_moves` MUST rollback `git add` on commit failure

The helper MUST run `git reset HEAD` to un-stage the paths it added whenever
`git commit` fails (e.g., pre-commit hook rejection, GPG signing failure,
index corruption), preventing index pollution.

#### Scenario: git commit fails → index rolled back

- **GIVEN** working tree has archive paths staged by the helper
- **WHEN** `git commit` exits non-zero
- **THEN** helper runs `git reset HEAD` to un-stage
- **AND** returns 1 (or whatever error propagation the script uses)
- **AND** human can retry commit manually

### Requirement: Commit message MUST match repo convention

The auto-commit message MUST be exactly `archive(<name>): archive completed`,
matching the existing repo convention established by commit `0d6ba45`
(`archive(status-guide-revision): archive completed — 56 tasks, 12 work-units, 50 bats green`).

#### Scenario: Commit subject line readable

- **WHEN** helper commits
- **THEN** `git log -1 --format=%s` outputs `archive(<name>): archive completed`
- **AND** the literal `<name>` is replaced with the actual change name (not escaped)

### Requirement: `archive_change` MUST call helper after `openspec archive`

The `skills/_lib/archive.sh::archive_change <name>` function MUST call
`commit_archive_moves "$name" "$main_root"` after the `openspec
archive "$name" --yes` call succeeds and before the `cleanup_worktree_and_branch` call.

The helper call MUST be tolerant to failure (use `|| true`): the file
moves are still in the working tree, so the human can review/retry
without aborting the ship flow.

#### Scenario: archive_change ships cleanly

- **GIVEN** an active change `my-change` with archive-ready state
- **WHEN** `archive_change "my-change"` is invoked
- **THEN** merge succeeds + `openspec archive` succeeds + helper commits + worktree cleaned
- **AND** working tree is clean at end of function

### Requirement: `guide-ship.md` Phase 3 lightweight mode MUST also call helper

The helper MUST be invoked from the Phase 3 lightweight archive section
in `skills/guide-ship.md` (the inline `openspec archive "$CHANGE_NAME"
--yes` block) after the openspec call. The helper source MUST be loaded
if not already sourced.

#### Scenario: Lightweight archive produces auto-commit

- **GIVEN** user is on the change branch with `openspec/` already merged to default
- **WHEN** lightweight archive runs (no worktree, direct merge + inline openspec archive)
- **THEN** `commit_archive_moves` is called after `openspec archive`
- **AND** working tree becomes clean (auto-committed)

