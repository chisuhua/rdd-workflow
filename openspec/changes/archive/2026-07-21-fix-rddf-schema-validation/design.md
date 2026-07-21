# fix-rddf-schema-validation Design

## Problem

`skills/_lib/rddf_session.py` persists workflow session state, but its schema validation path is effectively disabled. The schema path constant points at a nonexistent directory, and `_read_unlocked()` does not enable validation when reading `sessions.json`. As a result, malformed session payloads can be loaded without rejection.

## Goals

- Point session schema lookup at the checked-in schema file under `skills/_lib/schemas/sessions_schema.json`.
- Enable JSON schema validation when reading the persisted session store.
- Lock behavior with regression tests for malformed data, missing required fields, and a valid payload.

## Non-goals

- Do not change the session data model.
- Do not change the schema contents.
- Do not add new persistence formats or migration logic.

## Implementation approach

1. Fix the schema path constant so validation resolves against the existing schema file.
2. Ensure `_read_unlocked()` passes `validate=True` into the schema-aware read path.
3. Add three focused tests that exercise the persistence reader against malformed and valid `sessions.json` content.

## Files in scope

- `skills/_lib/rddf_session.py` — production fix for schema path and validation flag.
- `tests/unit/test_rddf_session.py` — regression coverage for schema validation behavior.
- `openspec/changes/fix-rddf-schema-validation/tasks.md` — execution checklist.
