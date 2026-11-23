# cross-container-event-bus Specification

## Purpose
TBD - created by archiving change feat-guide-orchestrator-session-event-bus. Update Purpose after archive.
## Requirements
### Requirement: stage-guide-kind

> **RETIRED (2026-11-20, retire-spec-musts-pointing-at-retired-objects)** —— `stage_guide` 长会话类型已随 ADR-0063 退役，无等价 kind。保留原文与 Scenario 作为历史记录。


The system SHALL support a new rddf-session kind `stage_guide` that represents the long-lived main orchestrator session owned by the user's guide OpenCode window.

#### Scenario: Create stage_guide session on guide launch

- GIVEN user runs `skill_use("guide")` in an OpenCode window
- AND no active `stage_guide` session exists for this owner
- WHEN guide initialization completes
- THEN a new rddf-session with `kind="stage_guide"`, `goal.intent="guide-orchestrator"`, `goal.last_seen_offset=0` is created
- AND its `parent_session_id` is `null` (root of the session tree)

#### Scenario: Stage-guide does not block other stage creation

- GIVEN an active `stage_guide` session exists for owner A
- WHEN user in OpenCode window B calls `rdd-builder` which creates `stage_plan` session
- THEN the `stage_plan` creation succeeds without ConflictError
- AND both sessions coexist with the stage_plan's `parent_session_id` pointing to the stage_guide

#### Scenario: Stage-guide extended heartbeat timeout

- GIVEN an active `stage_guide` session
- WHEN 30 minutes pass without heartbeat refresh
- THEN the session remains `active` (NOT orphaned)
- AND additionally, the session becomes `orphaned` only after 8 hours without heartbeat

#### Scenario: Stage-guide single-writer-per-owner invariant

- GIVEN an active `stage_guide` session owned by OpenCode window A
- AND another `stage_guide` session is attempted by the SAME owner A
- WHEN guide re-initialization triggers `create_session(kind="stage_guide", owner=A)`
- THEN the existing session is returned (no duplicate created)

### Requirement: events-jsonl

The system SHALL write workflow lifecycle events to `.rddf/state/events.jsonl` as append-only JSONL, with fcntl.flock protection, 50MB size cap, and automatic archival to `.archive.jsonl`.

#### Scenario: Hook entry writes phase_started event

- GIVEN `rddf_session_hook_entry` is called with `kind="stage_arch"`, `session_id="rds_xxx"`, `parent_session_id="rds_yyy"`
- WHEN the hook creates the rddf-session
- THEN an event row is appended to `events.jsonl` with `event_type="phase_started"`, `context.session_id="rds_xxx"`, `context.kind="stage_arch"`, `context.parent_session_id="rds_yyy"`, `context.owner_opencode_session_id=<owner>`
- AND the JSON is well-formed and parseable

#### Scenario: Hook close writes phase_completed event

- GIVEN `rddf_session_hook_close` is called with `kind="stage_arch"` and `end_reason="plan-done"`
- WHEN the hook transitions the rddf-session to `completed`
- THEN an event row is appended with `event_type="phase_completed"` and the corresponding `end_reason` in `message`

#### Scenario: Hook error writes phase_failed event

- GIVEN `rddf_session_hook_close` is called with an exception during execution
- WHEN the hook transitions the rddf-session to `failed`
- THEN an event row is appended with `event_type="phase_failed"` and error details in `message`

#### Scenario: Archive events moves old rows

- GIVEN events.jsonl exceeds 50MB
- WHEN `archive_events(keep=1000)` is called
- THEN the oldest rows beyond the most recent 1000 are moved to `events.archive.jsonl`
- AND events.jsonl size drops below 50MB
- AND no rows are deleted from the canonical timeline

### Requirement: guide-polling-contract

The `guide` skill SHALL observe events from `events.jsonl` on each menu render, using a polling contract that minimizes IO and respects per-owner progress.

#### Scenario: Guide with no active children skips event read

- GIVEN guide starts in OpenCode window A
- AND no other owner has an active rddf-session
- WHEN guide renders the menu
- THEN `events.jsonl` is NOT read (zero IO)
- AND the menu does not display a "cross-container" section

#### Scenario: Guide with active children reads incrementally

- GIVEN guide starts in OpenCode window A
- AND OpenCode window B has an active `stage_plan` session owned by B
- WHEN guide renders the menu
- THEN `events.jsonl` is read from line `(goal.last_seen_offset + 1)` onwards
- AND events are rendered to the menu (e.g., "rdd-builder 完成了 3/5 tasks")

#### Scenario: Guide updates last_seen_offset post-render

- GIVEN guide rendered 5 new events from line 100 onwards
- AND the last new event is at line 104
- WHEN render completes
- THEN `goal.last_seen_offset` is updated to 104 for this owner's `stage_guide` session
- AND a subsequent guide render with no new events skips line 0-104

#### Scenario: Two owners independent progress

- GIVEN OpenCode window A and window B both have `stage_guide` sessions (different owners)
- AND events.jsonl contains events at lines 100-110
- WHEN window A renders (last_seen_offset = 105)
- THEN A renders only events at lines 106-110
- AND B's last_seen_offset (e.g., 100) is unchanged

### Requirement: parent-kind-map-extension

The `rddf_session_hooks.sh` parent_kind_map SHALL include the `stage_arch → stage_guide` mapping, and parent lookup SHALL be owner-scoped (not "newest of kind").

#### Scenario: Stage_arch parent when guide exists

- GIVEN OpenCode window A has an active `stage_guide` session
- AND `rddf_session_hook_entry` is called with `kind="stage_arch"`, owner=A
- WHEN the hook resolves the parent
- THEN the created `stage_arch` session has `parent_session_id` pointing to A's `stage_guide` session

#### Scenario: Stage_arch parent when no guide

- GIVEN no active `stage_guide` session exists for owner A
- AND `rddf_session_hook_entry` is called with `kind="stage_arch"`, owner=A
- WHEN the hook resolves the parent
- THEN the created `stage_arch` session has `parent_session_id=null` (向后兼容；no error)

#### Scenario: Owner-scoped parent lookup with multiple arch sessions

- GIVEN owner A has a completed `stage_arch` session from yesterday
- AND owner A has NO active `stage_arch` today
- AND owner A's `stage_guide` is active
- WHEN `rddf_session_hook_entry` is called with `kind="stage_design"`, owner=A
- THEN parent resolves to the active `stage_guide` (NOT the yesterday's completed `stage_arch`)

### Requirement: backward-compatibility

All changes SHALL maintain backward compatibility with existing sessions.json v1/v2 data, existing event consumers, and existing skill behavior.

#### Scenario: Old sessions.json still loads

- GIVEN a sessions.json file at version 1 (no `stage_guide`, no `goal.last_seen_offset`)
- WHEN any rddf-session operation reads the file
- THEN validation passes (schema `version` field has `minimum: 1`)
- AND missing fields are read as null/default via `.get()`

#### Scenario: Old event consumers still work

- GIVEN existing `_lib/cli/monitor_cmd.py` reads events
- WHEN it reads events.jsonl that contains new `phase_started` event types
- THEN the consumer does not crash
- AND unknown event types are rendered with a fallback message (not silenced)

#### Scenario: Feature flags disable new behavior

- GIVEN `RDDF_GUIDE_SESSION_ENABLED=false` is set
- WHEN `rddf guide` is invoked（v3 时期为 `skill_use("guide")`）
- THEN no `stage_guide` session is created
- AND existing guide behavior is preserved

- GIVEN `RDDF_EVENTS_LOG_ENABLED=false` is set
- WHEN hooks are triggered
- THEN no events are written to events.jsonl
- AND existing rddf-session behavior is preserved

### Requirement: rddf-session-kind-enumeration

The `_VALID_KINDS` enumeration in `skills/rddf-session/scripts/rddf_session_pkg/_types.py` SHALL include `stage_guide` as a valid kind, in addition to the existing `stage_arch / stage_design / stage_plan / stage_ship`.

#### Scenario: stage_guide accepted by create_session

- GIVEN `_VALID_KINDS` contains `"stage_guide"`
- WHEN `RddfSessionCoordinator.create_session(kind="stage_guide", ...)` is called
- THEN validation passes (line 49 `_VALID_KINDS` check accepts it)
- AND the session is persisted with `kind="stage_guide"`

#### Scenario: Both stage_guide and guide-orchestrator are valid

- GIVEN `_VALID_KINDS` contains both `"stage_guide"` and `"guide-orchestrator"` (belt-and-suspenders pattern)
- WHEN `create_session(kind="stage_guide", ...)` or `create_session(kind="guide-orchestrator", ...)` is called
- THEN both calls succeed
- AND both result in a session with normalized `kind="stage_guide"` in sessions.json

### Requirement: rddf-session-goal-intent

The `goal.intent` field enumeration in `_lib/schemas/sessions_schema.json` SHALL include `guide-orchestrator` as a valid intent value, in addition to the existing `guide-arch / guide-design / guide-plan / guide-ship`.
<!-- v4-residue:allow=enum -->

#### Scenario: guide-orchestrator intent in sessions.json schema

- GIVEN schema is v3 with intent enum `["guide-arch", "guide-design", "guide-plan", "guide-ship", "guide-orchestrator"]`
<!-- v4-residue:allow=enum -->
- WHEN a `stage_guide` session is created with `goal.intent="guide-orchestrator"`
- THEN schema validation accepts it
- AND `goal.intent` is persisted unchanged

#### Scenario: Backward compat for sessions.json without guide-orchestrator

- GIVEN an existing sessions.json v2 file with `goal.intent` values that are NOT `guide-orchestrator`
- WHEN the schema v3 is loaded and the file is read
- THEN validation passes (existing intent values are still valid)
- AND no migration is needed

### Requirement: rddf-session-goal-fields

The `goal` object SHALL support an optional `last_seen_offset` field (integer) used by `stage_guide` sessions to track per-owner events.jsonl read progress. Default value is 0 if not present.

#### Scenario: Default last_seen_offset when missing

- GIVEN an existing sessions.json v2 file where sessions have no `goal.last_seen_offset`
- WHEN a guide reads `goal.last_seen_offset` via `.get("goal", {}).get("last_seen_offset", 0)`
- THEN the value defaults to `0`
- AND guide renders all events from line 0 (one-time initialization)

#### Scenario: last_seen_offset updated after render

- GIVEN guide renders events from line 0 to line 99
- WHEN the render completes successfully
- THEN `goal.last_seen_offset` is updated to `99` for the active `stage_guide` session
- AND a subsequent render with no new events skips lines 0-99

#### Scenario: last_seen_offset reset after archive

- GIVEN guide's `goal.last_seen_offset=500` referencing a line in events.jsonl
- WHEN `archive_events(keep=1000)` moves lines 0-999 to events.archive.jsonl
- THEN all active `stage_guide` sessions have `goal.last_seen_offset` reset to `0`
- AND a subsequent render re-reads remaining events from line 0 (one-time re-read, acceptable)

