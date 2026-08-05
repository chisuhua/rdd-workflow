# worktree-commit-flow

## ADDED Requirements

### Requirement: Worktree commit flow

Worktree-internal modifications MUST be committed in worktree before archive; archive MUST handle merge + openspec archive + cleanup.

#### Scenario: Worktree with uncommitted changes

When worktree has working-tree changes, archive phase MUST refuse to merge until worktree-internal commit is created.
Given a change with hooks triggering on comments matching `worktree-archive-workflow` patterns
When the change is committed via `git commit`
Then no false-positive hook warning is emitted.

#### Scenario: Magic-number annotation

When a comment annotates a numeric threshold with explanation (e.g. "100ms threshold tuned for hardware X")
And the comment is in the same file as the threshold
Then the hook MUST NOT emit a lint warning on the threshold.
