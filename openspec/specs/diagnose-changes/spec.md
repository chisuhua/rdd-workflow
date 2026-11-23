# diagnose-changes Specification

## Purpose
TBD - created by archiving change add-rdd-doctor-skill. Update Purpose after archive.
## Requirements
### Requirement: rdd-doctor skill

The system SHALL provide a `rdd-doctor` skill as a manual-triggered, read-only diagnostic tool that the user can invoke at any time to surface file content / schema drift across 5 categories of structured files. The skill MUST NOT modify any tracked or gitignored file other than the optional `--json` output to `.rddf/state/.doctor-report.json` (gitignored).

#### Scenario: User runs doctor on a healthy project

- GIVEN all 5 categories have no defects
- WHEN the user runs `skill_use("rdd-doctor")`
- THEN the output is a single summary line `✅ All 5 categories OK` plus exit code 0
- AND no `.rddf/state/.doctor-report.json` is written

#### Scenario: Doctor detects state JSON schema drift

- GIVEN `.rddf/state/iteration.json` is missing a required field per `_lib/schemas/iteration_schema.json`
- WHEN the user runs `skill_use("rdd-doctor")`
- THEN this finding is reported with severity CRITICAL
- AND the exit code is 2

#### Scenario: Doctor detects roadmap-meta.yaml schema drift

- GIVEN `openspec/changes/<name>/roadmap-meta.yaml` has `manual_deps` typed as a string instead of an array (violating ADR-0022 schema)
- WHEN the user runs `skill_use("rdd-doctor")`
- THEN this finding is reported with severity CRITICAL
- AND the fix hint includes the literal substring "silently ignore" so the operator understands why the finding is critical

#### Scenario: Doctor on a fresh project

- GIVEN the project has no `.rddf/state/` directory and no active changes
- WHEN the user runs `skill_use("rdd-doctor")`
- THEN each category outputs `[OK] <category>: no files to check`
- AND the overall summary is `✅ All 5 categories OK (5 empty)`
- AND the exit code is 0
- AND no error is raised

#### Scenario: Doctor with openspec CLI missing (cat-5 degraded path)

- GIVEN `openspec` is not on `$PATH`
- WHEN the user runs `skill_use("rdd-doctor")`
- THEN category 5 (`tasks-checkbox-check`) produces an INFO finding stating `openspec status unavailable, skipping cross-check`
- AND the exit code is determined by other categories, not affected by the degraded cat-5 path

### Requirement: Doctor output formats

The system SHALL support both human-readable and JSON output formats via the `--json` flag. The default mode SHALL produce grouped CRITICAL / WARNING / INFO sections with each finding containing severity, category, file path, line number, short snippet, and a suggested fix hint. The `--json` mode SHALL write a structured report to `.rddf/state/.doctor-report.json` with top-level keys `timestamp` (ISO 8601), `categories_checked` (list of 5 strings), `findings` (array of objects each with `severity`, `category`, `file`, `line`, `snippet`, `fix_hint`), and `summary` (object with `critical`, `warning`, `info` integer counts).

#### Scenario: Default human-readable output

- WHEN the user runs `skill_use("rdd-doctor")` without flags
- THEN the output is grouped into CRITICAL / WARNING / INFO sections
- AND each finding includes severity, category, file path, line number, snippet, and fix hint

#### Scenario: `--json` mode writes structured report

- WHEN the user runs `skill_use("rdd-doctor --json")`
- THEN a structured report is written to `.rddf/state/.doctor-report.json` (gitignored)
- AND the JSON contains the keys `timestamp`, `categories_checked`, `findings`, `summary`
- AND the stdout is a single line `📋 Report: .rddf/state/.doctor-report.json`

### Requirement: Doctor filtering and quiet modes

The system SHALL support `--category <name>` (run only one of 5 categories) and `--quiet` (stdout limited to at most one line containing only the most severe finding). The system SHALL support `--help` and `--version` flags.

#### Scenario: `--category` filter

- WHEN the user runs `skill_use("rdd-doctor --category state")`
- THEN only the state-schema-check category is executed
- AND the exit code reflects only that category's findings

#### Scenario: `--quiet` mode

- WHEN the user runs `skill_use("rdd-doctor --quiet")`
- THEN stdout is limited to at most one line containing only the most severe finding
- AND the exit code matches the underlying severity

### Requirement: Exit codes

The system SHALL follow the `openspec validate` exit code convention: exit code 0 when all categories are OK; exit code 1 when only INFO and/or WARNING findings are present and no CRITICAL; exit code 2 when at least one CRITICAL finding is present; exit code 3 when a checker raises an internal exception (other categories may still report normally in this case).

#### Scenario: Exit code matrix

- GIVEN various combinations of findings (none, INFO only, WARNING only, CRITICAL present, checker exception)
- WHEN the user runs `skill_use("rdd-doctor")`
- THEN the exit code matches the documented mapping (0 / 1 / 2 / 3 respectively)

### Requirement: Read-only behavior

The system SHALL NOT modify any tracked or gitignored file other than the optional `.rddf/state/.doctor-report.json` written by `--json` mode. The implementation SHALL NOT invoke `git rm`, `rm -f`, `mv`, or `sed -i` against any target file. The system SHALL NOT present any auto-fix prompt (Y/N) to the user.

#### Scenario: Read-only verification via git status

- GIVEN a clean working tree
- WHEN the user runs `skill_use("rdd-doctor")`
- THEN `git status --porcelain` output before and after the run is identical (with the documented exception of `.rddf/state/.doctor-report.json` if `--json` is used)

### Requirement: Path resolver must use real `_lib/` paths

The system SHALL resolve JSON schema paths from `_lib/schemas/` (the real file location) and MUST NOT resolve via the `skills/_lib/` shim indirection. This requirement exists because commit `c3a90fe` reduced `skills/_lib/` to a 6-line shim, and a checker that loads schema via the shim risks silently inheriting stale global state.

#### Scenario: Schema loaded from real path

- WHEN any checker loads a JSON schema
- THEN the schema is read from `${PROJECT_ROOT}/_lib/schemas/<name>_schema.json` (or equivalent absolute resolution)
- AND no `source skills/_lib/state.sh` indirection is involved in the schema lookup path

### Requirement: Smoke test registration

The system SHALL register `rdd-doctor` in `tests/smoke.bats` with a test case line referencing the skill name. The `bats tests/smoke.bats` run MUST pass and MUST include the new test case.

#### Scenario: smoke.bats includes rdd-doctor

- WHEN `grep -q "rdd-doctor" tests/smoke.bats` is run
- THEN the command exits 0
- AND `bats tests/smoke.bats` includes a test case for `rdd-doctor`

### Requirement: No auto-fix capability

The system SHALL NOT auto-fix any finding under any circumstance. The implementation MUST NOT generate `sed`/`awk`/inline Python fix commands, MUST NOT execute any such command, and MUST NOT present a Y/N prompt to apply a fix.

#### Scenario: Auto-fix is never offered

- WHEN the user runs `rdd-doctor` against any state
- THEN no fix command is generated
- AND no Y/N prompt is shown to the user
- AND no state file is modified by the tool itself

