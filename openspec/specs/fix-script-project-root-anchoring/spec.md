# fix-script-project-root-anchoring Specification

## Purpose
Anchor the builder's phase scripts to `PROJECT_ROOT` instead of the current working
directory, and keep a gate that rejects repository paths written relative to the
project root.
## Requirements
### Requirement: phase1-plan-reads-and-writes-under-project-root

`phase1_plan.sh` SHALL read the change's `proposal.md` from `$PROJECT_ROOT` and SHALL
write `tasks.md` and the `.rddf/plans/` directory under `$PROJECT_ROOT` — not under the
process's current working directory.

#### Scenario: the proposal is read from PROJECT_ROOT

- **WHEN** `PROJECT_ROOT` points at a project that is not the current working directory,
  and only that project holds the change's `proposal.md`
- **THEN** `phase1_plan.sh` SHALL read that proposal
- **AND** it SHALL NOT report the proposal as missing

#### Scenario: the write targets PROJECT_ROOT

- **WHEN** `phase1_plan.sh` runs with `PROJECT_ROOT` pointing elsewhere
- **THEN** the change's `tasks.md` and the `.rddf/plans/` directory SHALL be created
  under `PROJECT_ROOT`
- **AND** the current working directory SHALL stay free of the change's artefacts

### Requirement: phase1-5-reads-plan-handoff-from-project-root

`phase1_5_deps.sh` SHALL read `.rddf/state/.plan-handoff.json` from `$PROJECT_ROOT`, so
the execution mode it reports belongs to that project.

#### Scenario: the legacy plan-handoff is read from PROJECT_ROOT

- **WHEN** the working directory and `PROJECT_ROOT` hold different
  `.rddf/state/.plan-handoff.json` files with different execution modes
- **THEN** `phase1_5_deps.sh` SHALL exit 0
- **AND** the `execution_mode` it reports on stderr SHALL be the one from `PROJECT_ROOT`

### Requirement: phase2-fallback-worktree-is-created-under-project-root

When the lightweight path is forced back to a worktree, `phase2_execute.sh` SHALL create
that worktree under `$PROJECT_ROOT` rather than under the current working directory.

#### Scenario: the fallback worktree does not land in the working directory

- **WHEN** `phase2_execute.sh` falls back from lightweight mode to a worktree while the
  working directory differs from `PROJECT_ROOT`
- **THEN** the working directory's repository SHALL NOT gain a worktree for that change

### Requirement: isolation-gate-rejects-unanchored-repo-paths

The isolation gate SHALL reject a repository path written relative to the project root,
SHALL allow it when the line carries an `isolation-ok` exemption with a reason, and
SHALL judge per token — a line that mixes an unanchored token with an anchored one must
still be reported.

#### Scenario: an unanchored repository path is rejected

- **WHEN** a script contains the relative path `openspec/changes/x` without being
  anchored to the project root
- **THEN** the gate SHALL exit 1
- **AND** its output SHALL name the offending file and line

#### Scenario: an exemption with a reason lets the line pass

- **WHEN** the same line ends with an `isolation-ok` exemption carrying a reason
- **THEN** the gate SHALL exit 0
- **AND** removing that exemption SHALL make the gate report the line again

#### Scenario: a line mixing anchored and unanchored tokens is still reported

- **WHEN** one line contains both an unanchored `openspec/changes/x` and an anchored
  `$PROJECT_ROOT/openspec/changes/x`
- **THEN** the gate SHALL still report it

### Requirement: isolation-gate-passes-on-this-repository

The new isolation check SHALL pass on this repository on its own — it must not depend on
the historical exemptions elsewhere.

#### Scenario: the new check runs on this repository alone

- **WHEN** the isolation check is run with only this repository as its scan root
- **THEN** it SHALL exit 0

### Requirement: isolation-ok-exemptions-are-budgeted-at-two

The `isolation-ok` exemptions across the builder scripts SHALL number exactly two, and
each exemption SHALL carry a reason of at least ten characters.

#### Scenario: the exemption budget is exactly two

- **WHEN** the builder scripts are searched for `isolation-ok` exemptions
- **THEN** exactly two exemptions SHALL be found
- **AND** each exemption's reason SHALL be at least ten characters long

### Requirement: isolation-gate-bypass-is-audited

The isolation gate's test-pollution bypass SHALL be measurable: it SHALL announce that it
skipped the check and SHALL record the bypass in the audit log.

#### Scenario: the bypass announces itself and is audited

- **WHEN** the gate runs with the test-pollution bypass enabled
- **THEN** it SHALL print that it skipped the unanchored-path check
- **AND** it SHALL append a record to `.rddf/state/.bypass-audit.jsonl`
