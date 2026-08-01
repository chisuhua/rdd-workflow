## ADDED Requirements

### Requirement: orphaned sessions are terminal
`skills/rddf-session/scripts/rddf_session_pkg/_types.py` SHALL define `_TERMINAL_STATES` as a set containing `completed`, `failed`, `abandoned`, and `orphaned`.

#### Scenario: orphaned state is terminal
- **WHEN** inspecting `_TERMINAL_STATES`
- **THEN** it contains exactly `completed`, `failed`, `abandoned`, and `orphaned`

### Requirement: archive_history archives orphaned sessions
`RddfSessionCoordinator.archive_history(keep=0)` SHALL move all sessions whose state is in `_TERMINAL_STATES`, including `orphaned`, from `sessions.json` to `.archive.json`.

#### Scenario: orphaned sessions are archived
- **GIVEN** `sessions.json` contains one active session and two orphaned sessions
- **WHEN** `archive_history(keep=0)` is called
- **THEN** the two orphaned sessions are moved to `.archive.json` and the active session remains in `sessions.json`

#### Scenario: mixed terminal states archived while active is kept
- **GIVEN** `sessions.json` contains one completed, one failed, one abandoned, one orphaned, and one active session
- **WHEN** `archive_history(keep=10)` is called
- **THEN** the four terminal sessions remain in `sessions.json` and the active session remains in `sessions.json`

#### Scenario: orphaned session cannot transition to another terminal state
- **GIVEN** a session is in state `orphaned`
- **WHEN** `update_session_status` is called to transition it to `abandoned`
- **THEN** `RddfSessionError` is raised because orphaned is terminal

### Requirement: existing terminal states are unchanged
Adding `orphaned` to `_TERMINAL_STATES` SHALL NOT remove `completed`, `failed`, or `abandoned`.

#### Scenario: existing terminal states preserved
- **WHEN** inspecting `_TERMINAL_STATES`
- **THEN** it contains `completed`, `failed`, and `abandoned`
