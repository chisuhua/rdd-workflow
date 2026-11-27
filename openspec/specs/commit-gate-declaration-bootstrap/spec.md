# commit-gate-declaration-bootstrap Specification

## Purpose
TBD - created by archiving change add-commit-gate-declaration-bootstrap. Update Purpose after archive.

## Requirements

### Requirement: A project SHALL be able to generate a non-trivial commit-gate declaration

`rddf commit-gate init` SHALL write `.rddf/commit-gate.json` whose `verify_commands` are argv arrays pointing at entry points that **already exist** in the repository; when no such entry point is found it SHALL refuse and explain (never guess), the result SHALL be non-trivial (a single `true` / `echo` / `:` / `exit 0` command is not a declaration), and the command SHALL NOT `git add` or commit anything on the caller's behalf.

#### Scenario: A project with a test entry point gets a declaration

- **WHEN** a repository has `./test.sh` and no declaration, and `rddf commit-gate init` runs
- **THEN** `.rddf/commit-gate.json` is written with a `verify_commands` entry pointing at `./test.sh`, and nothing is staged or committed

### Requirement: rdd doctor SHALL report unusable commit-gate declarations

`rddf doctor --category commit-gate` SHALL report a WARNING for each of three faces: a declaration that is a **shell** (a single `true` / `echo` / `:` / `exit 0` command), a declaration that is **not git-tracked** (so a worktree has no gate), and a repository with **no declaration at all** (the gate is silently absent). Shell and untracked declarations SHALL name the file; a missing declaration SHALL name the expected path.

#### Scenario: A shell declaration is reported

- **WHEN** `.rddf/commit-gate.json` declares a single `true` command and `rddf doctor --category commit-gate` runs
- **THEN** a WARNING names the file and calls the declaration a shell
