# archive-openspec-tracked-skip-commit Specification

## Purpose
TBD - created by archiving change fix-archive-openspec-tracked-commit. Update Purpose after archive.
## Requirements
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
- **THEN** the function SHALL execute, in order: `switch_to_default_branch`, the merge-status check (`archive_premerge_check`), `openspec archive`, `cleanup_worktree_and_branch`, `mark_iteration_archived`
- **AND** SHALL NOT call `commit_archive_moves` (verifiable by inspecting the function body: the false branch contains no call to `commit_archive_moves`)
- **AND** the merge-status check SHALL be a decision only — it SHALL NOT merge anything

#### Scenario: lightweight branch sequence (fix-lightweight-branch-and-archive)

`_lib/archive.sh::archive_change()` cannot serve the lightweight mode (it requires a
worktree), so `skills/rdd-builder/scripts/phase3_archive.sh` runs the sequence inline.
Before that change the lightweight branch ran the AC gate and `openspec archive` and
nothing else — no merge judgment, no branch cleanup, no iteration sync.

- **WHEN** the builder handoff's `execution_mode_decision.mode` is `lightweight`
- **AND** `phase3_archive.sh <name>` is invoked
- **THEN** it SHALL execute, in order: `archive_gate_check`,
  `switch_to_default_branch`, the commit-ownership check
  (`lightweight_commit_ownership_check`), the merge judgment, `openspec archive`,
  `cleanup_worktree_and_branch`, `commit_archive_moves` (only when
  `openspec_tracked` is not `false`), `mark_iteration_archived` (with the real
  default-branch tip as `archive_commit_sha`), `post_archive_cleanup`
- **AND** the merge judgment SHALL reuse `archive_premerge_check` with an EMPTY
  `wt_path` (no worktree exists): its "uncommitted changes in the worktree"
  criterion SHALL NOT apply, because the main repo's dirty files may belong to
  another change
- **AND** `openspec_tracked=false` SHALL additionally refuse an unmerged
  implementation (the archive never merges on that path), while
  `openspec_tracked=true` SHALL merge the branch first (`merge_feature_branch`)
- **AND** a refusal SHALL NOT leave the main repo HEAD on the implementation
  branch

#### Scenario: lightweight commit ownership (fix-lightweight-branch-and-archive)

- **WHEN** the lightweight implementation branch carries no commit of its own
  (branch tip equals the creation point recorded by P2 as
  `execution_mode_decision.branch_base_sha`, or — for handoffs without that
  field — `git rev-list --count <default>..openspec/<name>` is 0)
- **THEN** the archive SHALL be refused, with a copy-pasteable command that
  commits on that branch
- **AND** the archive SHALL NOT auto-commit (`git add -A` would sweep unrelated
  changes into the commit)


#### Scenario: cleanup failures do not turn a successful archive into a failure

- **WHEN** `cleanup_worktree_and_branch` fails to delete the branch (it is not merged) or leaves the worktree directory behind
- **THEN** the archive SHALL still be reported as successful
- **AND** the failure SHALL be reported as a warning
- **AND** the "worktree removed" message SHALL be printed ONLY when the removal really happened

#### Scenario: false branch end state

- **WHEN** `archive_change(name)` completes in `openspec_tracked=false` mode
- **THEN** `git log --oneline` SHALL NOT contain a new commit for this archive operation
- **AND** `git status --porcelain` MAY show `openspec/changes/archive/<name>/` and `openspec/specs/<name>/` as untracked (expected, not a failure)

