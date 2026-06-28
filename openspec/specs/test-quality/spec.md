# test-quality Specification

## Purpose
TBD - created by archiving change v2-post-release-audit. Update Purpose after archive.
## Requirements
### Requirement: test-lock-no-tautology
The system SHALL fix the tautological assertion `assert not os.path.exists(lock_path) or True` in `tests/unit/test_lock.py` to a meaningful assertion based on lock.py's actual release behavior.

#### Scenario: lock test asserts meaningful behavior
- **WHEN** `pytest tests/unit/test_lock.py -v` is run
- **THEN** all assertions SHALL be non-tautological (no `or True`, no `assert True`)
- **AND** the assertion SHALL match lock.py's actual file-unlink behavior

### Requirement: event-context-unit-tests
The system SHALL add unit tests for `skills/_lib/event_context.py`.

#### Scenario: event_context tests exist
- **WHEN** `pytest tests/unit/test_event_context.py -v` is run
- **THEN** at least 1 test SHALL pass verifying `current_context()` returns a dict

### Requirement: defaults-unit-tests
The system SHALL add unit tests for `skills/_lib/defaults.py`.

#### Scenario: defaults tests exist
- **WHEN** `pytest tests/unit/test_defaults.py -v` is run
- **THEN** at least 2 tests SHALL pass verifying DEFAULT_CONFIG and DEFAULT_SAFETY structure

### Requirement: event-types-unit-tests
The system SHALL add unit tests for `skills/_lib/event_types.py`.

#### Scenario: event_types tests exist
- **WHEN** `pytest tests/unit/test_event_types.py -v` is run
- **THEN** tests SHALL verify: unique EventType values, ordered Severity levels, Event dataclass creation

### Requirement: state-sh-unit-tests
The system SHALL add bats tests for `skills/_lib/state.sh`.

#### Scenario: state.sh tests exist
- **WHEN** `bats tests/_lib/test_state.bats` is run
- **THEN** at least 2 tests SHALL pass verifying: file loads without error, functions are defined

### Requirement: ci-assertion-quality-gate
The system SHALL add a CI workflow (`.github/workflows/test.yml`) that includes an assertion quality gate to catch tautological patterns.

#### Scenario: CI blocks tautological assertions
- **WHEN** a commit introduces `assert ... or True` or `assert True` in `tests/`
- **THEN** the CI quality gate SHALL fail with specific file references
- **AND** the CI SHALL also run `pytest tests/unit/` and `bats tests/smoke.bats`

