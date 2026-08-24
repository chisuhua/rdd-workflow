## ADDED Requirements

### Requirement: clean-stale-plan-handoff-on-ship-done
The system SHALL clean stale plan-handoff state on ship-done, setting `current_change` to None when the archived change matches and `ship_started_at` to None when all changes are archived.

#### Scenario: single change archive matches current_change
- **GIVEN** plan-handoff.json contains `{active_changes: 1, current_change: "fix-foo"}`
- **WHEN** `cleanup_plan_handoff("fix-foo")` executes after archive
- **THEN** current_change is set to None and active_changes becomes 0

#### Scenario: all changes archived clears ship_started_at
- **GIVEN** plan-handoff.json has `active_changes: 0` after archive of last change
- **WHEN** cleanup runs
- **THEN** `ship_started_at` is set to None and final state is consistent

#### Scenario: idempotent when plan-handoff missing
- **GIVEN** no plan-handoff.json exists
- **WHEN** `cleanup_plan_handoff("fix-foo")` is invoked
- **THEN** no error raised; function exits silently (idempotent)