# scan-state-clean-return Specification

## Purpose
TBD - created by archiving change fix-scan-state-recursion. Update Purpose after archive.
## Requirements
### Requirement: `check_stale_workflow_state` MUST terminate (not recurse)

The `check_stale_workflow_state()` function MUST end with `return 0`
(or fall through to the natural function end) after the optional
warning emission. It MUST NOT call itself recursively.

#### Scenario: Function terminates when workflow-state.md is absent

- **GIVEN** no `workflow-state.md` at project root
- **WHEN** `check_stale_workflow_state <project_root>` is called
- **THEN** the function returns within <100ms with exit status 0
- **AND** no warning is printed to stdout

#### Scenario: Function terminates when workflow-state.md is present

- **GIVEN** `workflow-state.md` exists at project root
- **WHEN** `check_stale_workflow_state <project_root>` is called
- **THEN** the warning is printed to stdout
- **AND** the function returns within <100ms with exit status 0

### Requirement: `scan_state` MUST return within 1 second on clean repo

The `scan_state` function MUST populate `$RECOMMEND` and `$REASON`
globals and MUST return within 1 second when invoked on a repository
with no active openspec changes, no `.rddf/state/*.json` handoff files,
and no roadmap artifacts (i.e., the clean post-ship state).

#### Scenario: scan_state on clean repo produces RECOMMEND

- **GIVEN** a git repo with `openspec/changes/` only containing `archive/`
- **AND** no `.rddf/state/.arch-handoff.json`
- **AND** no `.rddf/state/.plan-handoff.json`
- **WHEN** `scan_state <repo_root>` is called
- **THEN** the function returns within 1 second
- **AND** `$RECOMMEND` is non-empty
- **AND** `$REASON` is non-empty

