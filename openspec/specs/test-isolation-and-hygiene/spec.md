# test-isolation-and-hygiene Specification

## Purpose
TBD - created by archiving change fix-test-isolation-and-hygiene. Update Purpose after archive.

## Requirements

### Requirement: tests-do-not-write-into-project-state

A test that exercises a caching or state-writing command MUST direct that command's state output to a temporary directory, and MUST assert that the project's real state directory is untouched.

This requirement applies to the commands whose state paths are corrected by the change that introduces it; it does not restate a project-wide guarantee for every state-writing script.

#### Scenario: cache is written to the temporary directory

- GIVEN a test that invokes the cross-repo dependency command with a spokes list
- WHEN the command runs with an explicit cache path inside the temporary directory
- THEN the cache file exists in the temporary directory
- AND the project's `.rddf/state/` directory contains no cache file afterwards

#### Scenario: an existing project cache is not modified

- GIVEN the project's state directory already contains a cache file
- WHEN the same test runs
- THEN the content of that file is byte-identical to its content before the run

### Requirement: state-file-default-paths-resolve-under-the-project-root

A command that writes a state file by default MUST resolve that path against the resolved project root, not against the current working directory.

This requirement applies to the commands whose default state path is corrected by the change that introduces it.

#### Scenario: default cache path is absolute and inside the project

- GIVEN the cross-repo dependency command is invoked without an explicit cache path
- WHEN the default path is computed
- THEN it is an absolute path
- AND it resides under `<project root>/.rddf/state/`

### Requirement: project-root-resolution-uses-the-canonical-resolver

Scripts MUST derive the project root through the canonical resolver. They MUST NOT derive it by counting parent directories or by searching for a directory that happens to be named `_lib`.

The canonical resolver MUST be owned by the canonical library layer, and the previous import location MUST remain available as an identity-merge shim.

#### Scenario: a sibling `_lib` directory does not mislead the resolver

- GIVEN a repository that contains a `skills/_lib/` directory next to the canonical `_lib/` directory
- WHEN the quick-history appender computes the project root
- THEN the resolved root is the repository root
- AND the history file path is `<repository root>/.rddf/state/.quick-history.jsonl`

#### Scenario: the walk-up heuristic is gone

- GIVEN the quick-history appender source
- WHEN it is inspected for a parent-directory search loop
- THEN no such loop is present

#### Scenario: the resolver import path still works

- GIVEN a module that imports the resolver from its previous location
- WHEN the module is imported
- THEN the import succeeds
- AND the previous-location module and the canonical module are the same object

### Requirement: project-root-resolution-is-anchored-at-the-script

The resolver's directory probe MUST be anchored at the location of the script that calls it, not at the caller's working directory.

#### Scenario: resolution does not depend on the current working directory

- GIVEN a process whose current working directory is outside any repository
- WHEN the quick-history appender resolves the project root
- THEN the resolved root is the repository that contains the appender
- AND the history file path is under that repository's state directory

### Requirement: misplaced-state-is-ignored-and-removed

A state directory created at a location other than the project's state directory MUST be removed, and the project MUST ignore that location so it cannot be committed accidentally.

#### Scenario: the misplaced state directory is gone

- GIVEN a `skills/.rddf/` directory containing a history file
- WHEN the cleanup completes
- THEN the directory no longer exists
- AND the ignore rules match that path

### Requirement: stale-runtime-artifacts-are-removed

Corrupt-state snapshots that are no longer under investigation, orphaned worktree copies that are not registered with git and do not correspond to an active change, and zero-byte files at the repository root MUST be removed.

Removal MUST be preceded by an explicit check that the artifact is not a registered git worktree and not an active change.

#### Scenario: corrupt snapshots are removed

- GIVEN the project state directory contains corrupt-iteration snapshots
- WHEN the cleanup completes
- THEN no corrupt snapshot remains
- AND the mechanism that produces such snapshots is unchanged

#### Scenario: an orphaned worktree copy is removed

- GIVEN a worktree copy that is not listed by git and whose change is archived
- WHEN the cleanup completes
- THEN the copy is gone
- AND the registered worktree list is unchanged

#### Scenario: root-level zero-byte files are removed

- GIVEN zero-byte files at the repository root that nothing references
- WHEN the cleanup completes
- THEN those files no longer exist

### Requirement: doctor-plan-checks-target-active-changes

The doctor's plan-structure check MUST report findings for plans that belong to changes which are not archived.

For plans that do not belong to an active change, the check MUST skip plans whose last commit is older than 30 days, and MUST check plans that were added recently even if their change was never registered.

The check MUST NOT raise when the iteration state is missing or unreadable. When the age of a plan cannot be determined, the plan MUST be checked.

#### Scenario: an active change's plan is checked

- GIVEN a plan file whose change is not archived
- WHEN the doctor's plan check runs
- THEN a finding is produced for that plan when it lacks the canonical step markers

#### Scenario: a historical plan is skipped

- GIVEN a plan file that was last committed long ago and does not belong to an active change
- WHEN the doctor's plan check runs
- THEN no finding is produced for that plan

#### Scenario: a recently added unregistered plan is checked

- GIVEN a plan file that was committed recently and whose change was never registered
- WHEN the doctor's plan check runs
- THEN a finding is produced for that plan when it lacks the canonical step markers

#### Scenario: unreadable iteration state does not raise

- GIVEN the iteration state file is missing or cannot be parsed
- WHEN the doctor's plan check runs
- THEN the check completes without raising
