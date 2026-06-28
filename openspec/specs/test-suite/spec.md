## ADDED Requirements

### Requirement: unit-test-coverage
The system SHALL provide unit tests for all v2.0 Python modules with ≥ 80% coverage.

Test files required (10):
- test_state_vector.py, test_event_log.py, test_gate.py, test_config.py
- test_loop_engine.py, test_detectors.py, test_actions.py
- test_tribunal.py, test_memory.py, test_session.py

#### Scenario: Coverage target met
- **WHEN** `pytest --cov` is run
- **THEN** coverage report shows ≥ 80%
- **AND** all tests pass with 0 failures, 0 errors

### Requirement: integration-test-suite
The system SHALL provide end-to-end integration tests for v2.0 workflows.

Test files (3-4):
- test_loop_flow.py: full scan→plan→execute→verify→adapt cycle
- test_gate_transition.py: pass/fail/force transitions
- test_phase_switch.py: arch→plan→ship transitions
- test_three_modes.py: loop/menu/hybrid mode behavior

#### Scenario: Full loop integration
- **WHEN** integration test runs
- **THEN** it exercises a complete loop cycle
- **AND** verifies state vector, event log, and gate interactions

### Requirement: test-performance
The system SHALL ensure all tests complete in < 5 minutes.

#### Scenario: Fast test execution
- **WHEN** full test suite runs
- **THEN** total execution time < 5 minutes
- **AND** no single test takes > 30 seconds
