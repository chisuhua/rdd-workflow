# env-bootstrap Specification

## Purpose
Give a project a one-shot environment check: detect what the project is and what it
lacks, diagnose the findings, and — with the operator's consent — fix the ones that
can be fixed automatically, leaving an auditable report behind.
## Requirements
### Requirement: env-bootstrap-skill-declares-its-boundaries-and-phases

The env-bootstrap skill's documentation SHALL declare, in its frontmatter, the paths it
owns and the paths it does not own, and its body SHALL document the four phases it
runs.

#### Scenario: the skill declares its boundaries

- **WHEN** the skill's frontmatter is read
- **THEN** it SHALL declare a role with boundary information
- **AND** that boundary SHALL declare what the skill owns and what it does not own

#### Scenario: the skill documents the four phases

- **WHEN** the skill's body is read
- **THEN** it SHALL document all four phases

### Requirement: env-bootstrap-cli-exposes-its-flags

`rddf env-bootstrap` SHALL expose its flags in its help output.

#### Scenario: the help lists the command's flags

- **WHEN** `rddf env-bootstrap --help` runs
- **THEN** the output SHALL list the command's flags
- **AND** it SHALL name the check-only, auto-fix, confirmation, target and report flags

### Requirement: env-bootstrap-check-only-runs-detection-and-diagnosis-only

`rddf env-bootstrap --check-only` SHALL run the detection and diagnosis phases only
and SHALL NOT write any file.

#### Scenario: the check-only run reports detection and diagnosis

- **WHEN** `rddf env-bootstrap --check-only` runs
- **THEN** the output SHALL contain the detection phase's result
- **AND** it SHALL contain the diagnosis phase's result

#### Scenario: the check-only run performs no guided fix

- **WHEN** `rddf env-bootstrap --check-only` runs
- **THEN** the output SHALL NOT contain a guided-fix phase's result

#### Scenario: the check-only run writes no report

- **WHEN** `rddf env-bootstrap --check-only` runs
- **THEN** no report file SHALL be written

### Requirement: env-bootstrap-runs-all-four-phases-in-the-target-directory

By default `rddf env-bootstrap` SHALL run all four phases against the directory it is
pointed at, and `--auto-fix --yes` SHALL be accepted as a non-interactive variant of
the same run.

#### Scenario: the default run produces every phase's result

- **WHEN** `rddf env-bootstrap` runs against a healthy project
- **THEN** the report it produces SHALL carry the detection, diagnosis, init-suggestion
  and guided-fix phases

#### Scenario: the target directory is the one that gets checked

- **WHEN** `rddf env-bootstrap --target <dir>` runs
- **THEN** the run SHALL inspect <dir>

#### Scenario: the non-interactive variant is accepted

- **WHEN** `rddf env-bootstrap --auto-fix --yes` runs
- **THEN** the run SHALL succeed
- **AND** it SHALL produce a report

### Requirement: env-bootstrap-exits-three-outside-an-rdd-project

`rddf env-bootstrap` SHALL exit with code 3 when the directory it inspects is not an
rdd-workflow project, and SHALL say so.

#### Scenario: a non-project directory exits 3

- **WHEN** `rddf env-bootstrap` inspects a directory that is not an rdd-workflow project
- **THEN** it SHALL exit with code 3
- **AND** its output SHALL state that the directory is not an rdd-workflow project

### Requirement: env-bootstrap-detects-the-project-environment

The detection phase SHALL detect whether the project is a git repository, what
language it is written in, and which AI configuration files it carries.

#### Scenario: a git repository is detected

- **WHEN** the detection runs in a directory that holds a `.git` directory
- **THEN** it SHALL report that the project is a git repository

#### Scenario: the project's language is detected

- **WHEN** the detection runs in a directory that holds a `pyproject.toml`
- **THEN** it SHALL report the project as a Python project

#### Scenario: the AI configuration files are detected

- **WHEN** the detection runs in a directory that holds an `AGENTS.md`
- **THEN** it SHALL report that file as an AI configuration file

### Requirement: env-bootstrap-classifies-findings-by-ownership

The diagnosis phase SHALL classify each finding by who can act on it: a finding that
an automated fix can address, and a finding that needs the operator's decision.

#### Scenario: an un-deployed AI context is classified as automatically fixable

- **WHEN** the diagnosis classifies an un-deployed AI context finding
- **THEN** it SHALL classify it as automatically fixable

#### Scenario: a missing gitignore entry is classified as needing a decision

- **WHEN** the diagnosis classifies a finding about a missing gitignore entry
- **THEN** it SHALL classify it as needing the operator's decision

### Requirement: env-bootstrap-runs-fixes-as-subprocesses-and-records-each-one

Each fix SHALL run as a subprocess, a failing fix SHALL NOT abort the run, and every
fix's outcome SHALL be recorded.

#### Scenario: a successful fix is recorded as executed

- **WHEN** a fix's command succeeds
- **THEN** the fix SHALL be recorded as executed

#### Scenario: a failing fix is recorded as failed

- **WHEN** a fix's command fails
- **THEN** the fix SHALL be recorded as failed
- **AND** the run SHALL continue

#### Scenario: every fix's outcome is collected

- **WHEN** several fixes have run
- **THEN** the report's executed-fix list SHALL carry one entry per fix

### Requirement: env-bootstrap-report-is-written-atomically-and-round-trips

The report SHALL be written atomically, and reading it back SHALL yield the same
content.

#### Scenario: the report file is created atomically

- **WHEN** the report is written
- **THEN** the report file SHALL exist
- **AND** no partially written file SHALL be left behind

#### Scenario: the report reads back unchanged

- **WHEN** a written report is loaded again
- **THEN** the loaded content SHALL equal the written content

### Requirement: env-bootstrap-report-carries-schema-version-1

The report SHALL declare schema version 1.

#### Scenario: the report declares version 1

- **WHEN** the report is written
- **THEN** its version field SHALL be 1

#### Scenario: the versioned schema loads

- **WHEN** the report schema is loaded
- **THEN** it SHALL declare version 1

### Requirement: env-bootstrap-report-carries-all-required-fields

The report SHALL carry every phase's result and the run's exit code, and a report
missing one of those fields SHALL be rejected.

#### Scenario: every required field is present

- **WHEN** a report is built
- **THEN** it SHALL carry the detection, diagnosis, init-suggestion and guided-fix
  results
- **AND** it SHALL carry the exit code

#### Scenario: a report missing a required field is rejected

- **WHEN** a report without one of the required fields is validated
- **THEN** it SHALL be rejected

### Requirement: env-bootstrap-exits-zero-when-everything-is-healthy

`rddf env-bootstrap` SHALL exit with code 0 when the project has nothing to report.

#### Scenario: a healthy project exits 0

- **WHEN** `rddf env-bootstrap` runs against a project with no findings
- **THEN** it SHALL exit with code 0
