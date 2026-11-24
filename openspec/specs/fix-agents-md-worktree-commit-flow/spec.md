# fix-agents-md-worktree-commit-flow Specification

## Purpose
Define the repository-level contract for documenting the worktree commit flow, for making the archive gate discoverable from the narrative docs, and for keeping the known-failure baseline in sync with assertions that have turned green.

## Requirements

### Requirement: AGENTS.md MUST document the worktree commit flow

`AGENTS.md` MUST carry an H3 section titled `Worktree Commit Flow` that states three things: the Phase 2 execute boundary (tasks are not committed individually; a single aggregate worktree-internal commit is made once all Phase 2 tasks pass), the conventional commit types accepted in that commit, and the Phase 3 archive boundary (the branch is merged, the change archived, and the worktree cleaned up).

The section MUST NOT hardcode drift-prone composition counts (for example a count of files or modules), because any such count is invalidated the moment files are added or removed.

#### Scenario: The aggregate-commit rule is stated with a discriminating boundary

- **WHEN** `AGENTS.md` is searched for the literal text `execute 阶段不逐任务 commit`
- **THEN** the matching line MUST itself contain `worktree-internal commit`
- **AND** the two lines following it MUST cross-reference the `Worktree Commit Flow` section

#### Scenario: The commit types are listed in the documented form

- **WHEN** `AGENTS.md` is searched for the H3 heading `Worktree Commit Flow`
- **THEN** the section MUST contain one list entry per conventional commit type, each written as a backtick-wrapped `<type>(<scope>):` prefix

### Requirement: The archive gate MUST be discoverable from the narrative docs

`AGENTS.md` MUST carry an H3 section titled `归档流程` whose body, within eight lines of the heading, names `check_worktree_commits` — the function that refuses to archive a worktree branch that carries no new commit relative to the default branch.

Every ADR identifier referenced by these sections MUST resolve to a file that exists under `docs/adr/`; a dangling identifier makes the reference a lie that no assertion would catch.

#### Scenario: The archive-gate section names the gate function

- **WHEN** `AGENTS.md` is searched for the H3 heading `归档流程` and the following eight lines are inspected
- **THEN** those lines MUST contain `check_worktree_commits`

### Requirement: The known-failure baseline MUST track assertions that turned green

`tests/KNOWN_FAILURES.txt` MUST be refreshed whenever previously registered assertions turn green. The refresh MUST be selective: it removes only the entries whose test no longer fails, and MUST NOT absorb newly failing tests into the baseline.

The regression comparison MUST be executed BEFORE the refresh. Refreshing first would launder any regression introduced inside the implementation window, because the refresh would then list it as a known failure.

#### Scenario: The baseline shrinks without absorbing new failures

- **WHEN** the regression comparison reports zero new failures and six previously registered entries no longer fail
- **THEN** the refreshed baseline MUST contain four entries
- **AND** the diff against the previous baseline MUST contain only removals plus a summary comment, with no added line that is not a comment

#### Scenario: The comparison precedes the refresh

- **WHEN** the known-failure baseline is refreshed
- **THEN** the regression comparison result MUST have been obtained before the refresh ran

