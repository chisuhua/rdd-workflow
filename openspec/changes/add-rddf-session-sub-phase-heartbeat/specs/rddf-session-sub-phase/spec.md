# rddf-session-sub-phase — Capability Spec

## ADDED Requirements

### Requirement: rddf-session Tracks Sub-Phase via Heartbeat

The rddf-session schema (v2) SHALL record an optional `sub_phase` string on each session, set by the heartbeat hook when callers provide `RDDF_SUB_PHASE` env var. The field defaults to null when omitted.

#### Scenario: Caller sets RDDF_SUB_PHASE on heartbeat

- GIVEN a fresh sessions.json with version=2
- WHEN `rddf_session_hook_heartbeat` is invoked with `RDDF_SUB_PHASE=phase_3_archive_demo`
- THEN the active session record has `sub_phase="phase_3_archive_demo"`

#### Scenario: Caller omits RDDF_SUB_PHASE

- GIVEN a fresh sessions.json with version=2
- WHEN `rddf_session_hook_heartbeat` is invoked without `RDDF_SUB_PHASE`
- THEN the active session record has no `sub_phase` key (or null)

### Requirement: Schema Backward-Compatible (v1 Reads OK on v2)

The schema bump to v2 SHALL keep v1 sessions valid (loadable without error) by making `sub_phase` and `workflow_group` optional fields.

#### Scenario: v1 session validates under v2 schema

- GIVEN a session record with only the v1 required fields (session_id, kind, owner_opencode_session_id, state, started_at, last_heartbeat)
- WHEN validated against sessions_schema.json v2
- THEN validation succeeds