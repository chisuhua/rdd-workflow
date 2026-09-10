## ADDED Requirements

### Requirement: archive-openspec-tracked-skip-commit-guard

The `_lib/archive.sh::commit_archive_moves(name, main_root)` function SHALL honor `.rddf/project.yaml` `git.openspec_tracked` field. When set to `false`, the function SHALL exit early without executing `git add` or `git commit`, returning 0 and printing a skip notice. This guard is defense-in-depth: any caller that invokes `commit_archive_moves` in a project with `openspec_tracked: false` will be safe even if the caller's own logic forgets to skip.

#### Scenario: openspec_tracked=false skips commit_archive_moves

- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: false}`
- **AND** `commit_archive_moves(name, main_root)` is invoked directly (not via `archive_change`)
- **THEN** the function SHALL return 0
- **AND** SHALL NOT execute `git add` for any `openspec/` path
- **AND** SHALL NOT execute `git commit`
- **AND** SHALL print a message containing "SKIPPED" and "openspec_tracked=false"

#### Scenario: openspec_tracked=true (default) preserves commit_archive_moves behavior

- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: true}` OR does not exist
- **AND** `commit_archive_moves(name, main_root)` is invoked directly
- **THEN** the function SHALL execute the standard 3-path `git add` and `git commit` sequence (existing behavior)
- **AND** SHALL create exactly one commit with subject `archive(<name>): archive completed`

#### Scenario: SKIP_ARCHIVE_AUTO_COMMIT env var continues to work

- **WHEN** `SKIP_ARCHIVE_AUTO_COMMIT=yes` is set
- **AND** `commit_archive_moves(name, main_root)` is invoked
- **THEN** the function SHALL return 0 without git activity (env var override, takes precedence over project.yaml)

### Requirement: archive-openspec-tracked-false-branch-cleanup

The `_lib/archive.sh::archive_change()` `openspec_tracked=false` branch SHALL NOT call `commit_archive_moves`. After `openspec archive --yes` and `cleanup_worktree_and_branch`, the branch SHALL proceed directly to `mark_iteration_archived` (and any other side-effect-free bookkeeping). This closes the spec-implementation gap in [ADR-0036](docs/adr/ADR-0036-rddf-project-yaml-config.md) M3.

#### Scenario: false branch sequence (post-fix)

- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: false}`
- **AND** `archive_change(name)` is invoked
- **THEN** the function SHALL execute, in order: `switch_to_default_branch`, `openspec archive`, `cleanup_worktree_and_branch`, `mark_iteration_archived`
- **AND** SHALL NOT call `commit_archive_moves` (verifiable by inspecting the function body: the false branch contains no call to `commit_archive_moves`)

#### Scenario: false branch end state

- **WHEN** `archive_change(name)` completes in `openspec_tracked=false` mode
- **THEN** `git log --oneline` SHALL NOT contain a new commit for this archive operation
- **AND** `git status --porcelain` MAY show `openspec/changes/archive/<name>/` and `openspec/specs/<name>/` as untracked (expected, not a failure)