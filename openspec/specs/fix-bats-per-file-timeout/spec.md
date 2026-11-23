# fix-bats-per-file-timeout Specification

## Purpose
Make the bats regression collection fail loudly and attribute failures precisely: a
collector that dies must not be mistaken for a clean run, a per-test hang must not hide
the other tests in the same file, and the report's denominator must not depend on how far
the collection got.
## Requirements
### Requirement: regression-collector-validates-its-thresholds

The collector SHALL validate its threshold environment variables before doing any work
and SHALL exit 2 on an invalid value rather than silently falling back to a default.

#### Scenario: an invalid BATS_TIMEOUT is rejected

- **WHEN** `BATS_TIMEOUT` is set to a non-positive or non-numeric value
- **THEN** the collector SHALL exit 2
- **AND** it SHALL NOT silently treat the value as "no limit"

#### Scenario: a retry budget below the timeout is rejected

- **WHEN** `BATS_TIMEOUT_RETRY` is lower than `BATS_TIMEOUT`
- **THEN** the collector SHALL exit 2

#### Scenario: an invalid retry budget is rejected

- **WHEN** `BATS_RETRY_BUDGET` holds an invalid value
- **THEN** the collector SHALL exit 2

### Requirement: regression-collector-classifies-exit-codes

The collector SHALL classify the exit code of a bats run: a clean run contributes no
failures, a run with `not ok` contributes failures, an infrastructure error is reported
as such, and a run that made no TAP progress is treated as a hang.

#### Scenario: a clean run contributes no failures

- **WHEN** a collected bats run exits 0
- **THEN** the collector SHALL record no failure for it

#### Scenario: a run with not ok contributes a failure

- **WHEN** a collected bats run exits 1 with a `not ok` line
- **THEN** the collector SHALL record that failure

#### Scenario: an infrastructure error is not treated as success

- **WHEN** a collected bats run exits 125
- **THEN** the collector SHALL exit 2 with an infrastructure error
- **AND** it SHALL NOT report the run as passing

#### Scenario: a hang is distinguished from a slow run

- **WHEN** a collected bats run makes no TAP progress
- **THEN** the collector SHALL classify it as a hang
- **AND** a run that did make progress SHALL be classified as slow instead

### Requirement: regression-collector-attributes-per-test-timeouts

A test that hangs inside a file SHALL be attributed to that test, and the file's other
tests SHALL still be evaluated.

#### Scenario: a hung test is attributed by name

- **WHEN** one test in a file hangs while the file's other tests complete
- **THEN** the collector SHALL attribute the hang to that test
- **AND** the file's remaining tests SHALL still be evaluated

### Requirement: regression-collector-uses-the-retry-result

When a file is retried, the collector SHALL use the retry's output as the authoritative
result; the first attempt's partial output SHALL NOT be merged into the failure set.

#### Scenario: the retry's output wins

- **WHEN** a file fails on the first attempt and times out on the retry
- **THEN** the collector SHALL not merge the first attempt's partial output into the
  failure set

### Requirement: regression-thresholds-are-overridable-through-the-environment

The collector's thresholds SHALL be overridable through the environment, and the retry
budget SHALL reach the per-file retry.

#### Scenario: the retry budget reaches the per-file retry

- **WHEN** the collector runs with a retry budget in the environment
- **THEN** the per-file retry SHALL use that budget

### Requirement: regression-collector-is-safe-under-concurrency

Two collectors running at the same time SHALL NOT truncate each other's failure sets,
and a collector SHALL refuse to run recursively.

#### Scenario: concurrent collectors do not truncate each other

- **WHEN** two collectors run at the same time
- **THEN** neither SHALL lose failures the other recorded

#### Scenario: a collector refuses to run recursively

- **WHEN** a collector is started while another one is already active
- **THEN** it SHALL exit 2

### Requirement: regression-report-fails-when-the-collector-dies

The report SHALL fail — not report a clean run — when the collector dies: either it
exits non-zero, or its summary is missing.

#### Scenario: a missing collector summary fails the report

- **WHEN** the collector produced no summary
- **THEN** the report SHALL exit 2
- **AND** it SHALL NOT print a clean summary

#### Scenario: a collector infrastructure error fails the report

- **WHEN** the collector itself failed with an infrastructure error
- **THEN** the report SHALL exit 2
- **AND** it SHALL NOT print a clean summary

### Requirement: regression-report-states-its-scope

The report SHALL name the scope it collected — the integration test directory — and
state that the repository's other bats files are not part of that gate.

#### Scenario: the report states the collected scope

- **WHEN** the report runs
- **THEN** its output SHALL name `tests/integration/` as the collected scope
- **AND** it SHALL state that the repository's other bats files are not in scope

### Requirement: regression-report-denominator-is-independent-of-the-run

The report's denominator SHALL be computed from the file list before the collection loop
starts, so it does not depend on how far the collection got.

#### Scenario: the denominator is computed before the loop

- **WHEN** the report computes how many files it will evaluate
- **THEN** that number SHALL be computed before the collection loop
- **AND** it SHALL match the number of files in scope

### Requirement: regression-report-fails-on-unlisted-unevaluated-files

A file that was not evaluated and is not listed in the known-unevaluated baseline SHALL
fail the gate, and the report SHALL NOT print a clean summary in that case.

#### Scenario: an unlisted unevaluated file fails the gate

- **WHEN** a file in scope was not evaluated and is not in the known-unevaluated baseline
- **THEN** the gate SHALL fail
- **AND** the report SHALL NOT print a clean summary

#### Scenario: a listed unevaluated file is reported but does not fail

- **WHEN** a file in scope was not evaluated and IS in the known-unevaluated baseline
- **THEN** the report SHALL print it
- **AND** the gate SHALL NOT fail because of it

### Requirement: known-failures-baseline-may-only-shrink

The known-failures baseline SHALL be allowed to shrink and SHALL NOT be allowed to grow.

#### Scenario: a shrunken baseline passes

- **WHEN** the known-failures baseline has fewer entries than before
- **THEN** the gate SHALL pass

#### Scenario: a grown baseline fails

- **WHEN** the known-failures baseline has more entries than before
- **THEN** the gate SHALL fail
