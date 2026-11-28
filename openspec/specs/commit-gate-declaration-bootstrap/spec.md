# commit-gate-declaration-bootstrap Specification

## Purpose
TBD - created by archiving change add-commit-gate-declaration-bootstrap. Update Purpose after archive.

## Requirements

### Requirement: A project SHALL be able to generate a non-trivial commit-gate declaration

`rddf commit-gate init` SHALL only auto-derive verification commands that are statically known to run tests, and SHALL refuse — with a copy-pasteable explicit-argv template and a dedicated exit code — when it cannot; a refusal MUST NOT write, stage or commit anything.

#### Scenario: A project with a test entry point gets a declaration

- **WHEN** a repository has a `test.sh` whose argument-less run prints help and exits 0, carries no declaration, and `rddf commit-gate init` runs
- **THEN** the command exits with the dedicated refusal code, `.rddf/commit-gate.json` is not written, and the output contains the explicit-argv template

#### Scenario: A toolchain entry point without test files is refused

- **WHEN** a repository has `go.mod` / `Cargo.toml` / `pyproject.toml` but no test files for that tool
- **THEN** the command refuses with the same dedicated exit code and does not write a declaration

#### Scenario: An existing valid declaration is reused

- **WHEN** `.rddf/commit-gate.json` already declares a non-shell `verify_commands` and `rddf commit-gate init --force` runs
- **THEN** the declaration keeps that argv verbatim and the output states that it was not re-derived

### Requirement: rdd doctor SHALL report unusable commit-gate declarations

`rddf doctor --category commit-gate` SHALL report a WARNING for each of three faces: a declaration that is a **shell** (a single `true` / `echo` / `:` / `exit 0` command), a declaration that is **not git-tracked** (so a worktree has no gate), and a repository with **no declaration at all** (the gate is silently absent). Shell and untracked declarations SHALL name the file; a missing declaration SHALL name the expected path.

#### Scenario: A shell declaration is reported

- **WHEN** `.rddf/commit-gate.json` declares a single `true` command and `rddf doctor --category commit-gate` runs
- **THEN** a WARNING names the file and calls the declaration a shell
