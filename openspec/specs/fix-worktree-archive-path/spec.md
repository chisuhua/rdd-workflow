# fix-worktree-archive-path Specification

## Purpose
Make the builder's archive phase archive in the **main** repository instead of inside the
worktree: the phase hands the work over to the shared `archive_change` helper, which owns
the gate, the cleanup and the iteration sync, so that the tracked and untracked paths
share one implementation.
## Requirements
### Requirement: phase3-worktree-mode-delegates-to-archive-change

The archive phase SHALL NOT run `openspec archive` itself in worktree mode. It SHALL hand
the archive over to `archive_change`, which runs it against the main repository.

#### Scenario: the phase no longer invokes openspec archive itself

- **WHEN** the source of `phase3_archive.sh` is inspected
- **THEN** the worktree branch SHALL NOT contain a direct `openspec archive` invocation

#### Scenario: the phase delegates to archive_change in worktree mode

- **WHEN** the archive phase runs in worktree mode
- **THEN** it SHALL call `archive_change`
- **AND** the archive SHALL NOT run inside the worktree

### Requirement: phase3-no-longer-runs-post-archive-cleanup-itself

The archive phase SHALL NOT run the post-archive cleanup itself — `archive_change` owns
it, and running it twice was the reason the phase stopped doing so.

#### Scenario: the phase no longer invokes the post-archive cleanup

- **WHEN** the source of `phase3_archive.sh` is inspected
- **THEN** it SHALL NOT contain a `post_archive_cleanup` invocation

### Requirement: worktree-archive-runs-in-the-main-repository

When `openspec` is not tracked by git, the archive SHALL run in the main repository, so
the archived change directory and the archived spec land there rather than inside the
worktree.

#### Scenario: the archive runs in the main repository

- **WHEN** the archive phase archives a change while `openspec` is untracked
- **THEN** the archive SHALL run with the main repository as its working directory

### Requirement: worktree-directory-and-branch-are-cleaned-up

After the delegated archive succeeds, the change's worktree directory and its
`openspec/<name>` branch SHALL both be removed.

#### Scenario: the worktree is cleaned up after the delegated archive

- **WHEN** the archive phase archives a change in worktree mode
- **THEN** the change's worktree directory SHALL no longer exist
- **AND** its `openspec/<name>` branch SHALL no longer exist

### Requirement: tracked-openspec-archive-merges-back-into-the-main-repository

When `openspec` **is** tracked by git, the delegated archive SHALL merge the change back
into the main repository and keep the existing merge path intact.

#### Scenario: the tracked path still merges the branch back

- **WHEN** the archive phase archives a change while `openspec` is tracked
- **THEN** the change's branch SHALL be merged into the main repository
- **AND** the worktree directory SHALL be removed

### Requirement: phase3-maps-gate-refusal-to-exit-7

When the archive gate refuses the archive, the phase SHALL exit 7 and SHALL surface the
gate's own message.

#### Scenario: a gate refusal becomes exit 7

- **WHEN** `archive_change` exits 3 because the archive gate refused
- **THEN** the archive phase SHALL exit 7
- **AND** the gate's refusal message SHALL be passed through
