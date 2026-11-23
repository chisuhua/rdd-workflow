# gitignore-hard-protection Specification

## Purpose
TBD - created by archiving change add-gitignore-hard-protection. Update Purpose after archive.
## Requirements
### Requirement: env-check-gitignore-guard-consistency

The `_lib/env_checks.sh::_check_gitignore()` function SHALL read `.rddf/project.yaml` `git.openspec_tracked` and, when set to `false`, verify `.gitignore` contains an `openspec/` entry. The check SHALL be non-blocking (never returns non-zero to abort phase entry) and SHALL NOT alter the 15-field env-cache JSON contract.

#### Scenario: false mode without gitignore entry warns

- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: false}`
- **AND** `.gitignore` does not contain an `openspec/` line
- **THEN** `_check_gitignore` SHALL print a warning containing "gitignore guard missing"
- **AND** SHALL set `_GITIGNORE_PROTECTED=no`
- **AND** SHALL return 0 (non-blocking)

#### Scenario: false mode with gitignore entry is silent

- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: false}`
- **AND** `.gitignore` contains an `openspec/` line
- **THEN** `_check_gitignore` SHALL NOT print a warning
- **AND** SHALL set `_GITIGNORE_PROTECTED=yes`

#### Scenario: reverse inconsistency warns when tracking enabled but ignored

- **WHEN** `git.openspec_tracked` is `true` or absent
- **AND** `.gitignore` contains an `openspec/` line
- **THEN** `_check_gitignore` SHALL print a warning containing "reverse inconsistency"

#### Scenario: default project without gitignore protection is silent

- **WHEN** `.rddf/project.yaml` does not exist or does not set `git.openspec_tracked`
- **AND** `.gitignore` does not contain `openspec/`
- **THEN** `_check_gitignore` SHALL NOT print any warning

#### Scenario: opt-in auto-fix appends idempotently

- **WHEN** `RDDF_ENV_FIX_GITIGNORE=yes` is set
- **AND** `git.openspec_tracked` is `false` and `.gitignore` lacks `openspec/`
- **THEN** `_check_gitignore` SHALL append `openspec/` to `.gitignore`
- **AND** a second invocation SHALL NOT duplicate the entry

### Requirement: doctor-gitignore-category

The `rdd-doctor` skill SHALL expose a read-only `gitignore` category (checker `checks/gitignore_check.py`, registered in `doctor_main.py::_CHECKERS`) reporting consistency between `.rddf/project.yaml` `git.openspec_tracked` and `.gitignore` protection, with severities and fix hints, without modifying any file.

#### Scenario: doctor warns on missing guard

- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: false}`
- **AND** `.gitignore` lacks `openspec/`
- **AND** the user runs `rdd-doctor --category gitignore`
- **THEN** the report SHALL contain a WARNING finding with a fix_hint mentioning adding `openspec/` to `.gitignore`
- **AND** exit code SHALL be non-zero per WARNING severity semantics

#### Scenario: doctor silent on healthy state

- **WHEN** `git.openspec_tracked: false` and `.gitignore` contains `openspec/`
- **THEN** `--category gitignore` SHALL produce no findings and exit 0

#### Scenario: doctor warns on reverse inconsistency

- **WHEN** `git.openspec_tracked` is true/absent and `.gitignore` contains `openspec/`
- **THEN** the report SHALL contain a WARNING finding describing the reverse inconsistency

#### Scenario: doctor remains read-only

- **WHEN** `--category gitignore` runs in any scenario
- **THEN** no file under the project root SHALL be modified by the checker

