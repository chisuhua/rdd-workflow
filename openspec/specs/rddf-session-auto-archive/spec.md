# rddf-session-auto-archive Specification

## Purpose
TBD - created by archiving change add-rddf-session-auto-archive-on-entry. Update Purpose after archive.
## Requirements
### Requirement: entry hook triggers best-effort auto-archive

`rddf_session_hook_entry` SHALL call `_rddf_auto_archive_if_needed` after the
main session creation flow. The call SHALL be best-effort: any failure MUST be
swallowed and MUST NOT change the hook's exit code or block the caller.

#### Scenario: archive runs when session count exceeds threshold

- **GIVEN** `.rddf/state/sessions.json` contains 20 `completed` sessions
- **AND** `RDDF_AUTO_ARCHIVE_KEEP` and `RDDF_AUTO_ARCHIVE_THRESHOLD` are unset
- **WHEN** `rddf_session_hook_entry stage_arch guide-arch arch-phase arch-done` is invoked
- **THEN** the hook exits 0
- **AND** `sessions.json` contains at most 11 sessions (10 kept + the new active session)
- **AND** `.rddf/state/sessions.archive.json` is created

#### Scenario: archive is disabled when keep is zero

- **GIVEN** `.rddf/state/sessions.json` contains 50 `completed` sessions
- **AND** `RDDF_AUTO_ARCHIVE_KEEP=0`
- **WHEN** `rddf_session_hook_entry stage_arch guide-arch arch-phase arch-done` is invoked
- **THEN** the hook exits 0
- **AND** `sessions.json` contains 51 sessions (no archive occurred)

### Requirement: close hook triggers best-effort auto-archive

`rddf_session_hook_close` SHALL call `_rddf_auto_archive_if_needed` after the
main session close flow, using the same best-effort semantics as the entry hook.

#### Scenario: close hook archives old terminal sessions

- **GIVEN** `.rddf/state/sessions.json` contains 20 `completed` sessions
- **WHEN** `rddf_session_hook_close stage_arch arch-done guide-arch` is invoked
- **THEN** the hook exits 0
- **AND** `sessions.json` contains at most 11 sessions

### Requirement: threshold helper is pure and defensive

`_rddf_should_auto_archive <total_count> <keep> <threshold>` SHALL return 0
(archive) only when `total_count >= threshold`, `keep > 0`, and `threshold > 0`.
It SHALL treat non-positive `keep` or `threshold` as disabled.

#### Scenario: default threshold equals keep plus five

- **WHEN** `_rddf_should_auto_archive 15 10 ""` is invoked
- **THEN** it returns 0

#### Scenario: keep zero disables archiving

- **WHEN** `_rddf_should_auto_archive 100 0 ""` is invoked
- **THEN** it returns 1

#### Scenario: negative values are treated as disabled

- **WHEN** `_rddf_should_auto_archive 100 -5 ""` is invoked
- **THEN** it returns 1

