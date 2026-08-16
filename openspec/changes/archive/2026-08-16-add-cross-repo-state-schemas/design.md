# add-cross-repo-state-schemas — Design

> Schema: spec-driven
> See: `proposal.md` for motivation, scope and acceptance criteria.

## Context

**ADR-0030 + 7 related proposals** introduce 6 new state files in `.rddf/state/`. The rdd-workflow project already maintains schemas in `_lib/schemas/` following ADR-0016 pattern (arch_handoff_schema.json v1 as reference template).

This design addresses:
1. Schema validation using jsonschema library (Draft-7)
2. Schema versioning strategy (v1 immutable + future v2 migration path)
3. rdd-doctor integration boundary
4. Unit test coverage

### Existing Schemas (Reference)

The project currently has 11 schemas in `_lib/schemas/`:
- `arch_handoff_schema.json` v1 — arch→plan handoff
- `design_handoff_schema.json` v1 — design→plan handoff  
- `plan_handoff_schema.json` v1 — plan→ship handoff
- `iteration_schema.json` v6 — current sprint view
- `sessions_schema.json` v1 — rddf-session lifecycle
- `deps_analysis_schema.json` v1 — deps analysis output
- `config_schema.json` v1 — rdd config
- `feature_view_schema.json` v1 — feature view
- `state_vector_schema.json` v1 — state vector
- `trigger_schema.json` v1 — trigger config
- `skill_role_schema.json` v1 — skill role definitions

The 6 new schemas follow the same patterns.

## Goals / Non-Goals

**Goals:**
- Each new schema MUST have `version` field (const integer) and `$id` unique identifier
- Each new schema MUST use `jsonschema.Draft7Validator` for validation
- Schema files MUST be ≤ 200 lines (readability)
- Unit tests MUST cover valid/invalid/missing-field scenarios for each schema
- rdd-doctor `--category state` MUST detect the 6 new schema files

**Non-Goals:**
- Implementing actual read/write logic for the 6 state files (belongs to each proposal)
- Modifying existing 11 schemas
- Integrating new schemas into gate.py plugins

## Decisions

### 1. Schema Validation Library

Use `jsonschema.Draft7Validator` from the existing project dependency.

**Rationale:** The project already uses jsonschema for iteration_schema validation. Draft-7 is the schema dialect used by all existing schemas.

**Validation pattern:**
```python
from jsonschema import Draft7Validator, ValidationError

def validate_record(record: dict, schema_name: str) -> bool:
    schema = load_schema(schema_name)
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(record))
    if errors:
        raise ValidationError(errors[0].message, path=errors[0].path)
    return True
```

### 2. Schema Versioning Strategy

**v1 (current):** Immutable once published. Contains `version: {"const": 1}`.

**v2 (future):** When breaking changes are needed:
1. Create `_lib/schemas/<name>_schema_v2.json`
2. Add `version: {"const": 2}` to new schema
3. Keep v1 for 6-month transition period
4. rdd-doctor warns if v1 files still in use after transition

**Version field location:** Top-level `version` property with `const` keyword.

### 3. rdd-doctor Integration Boundary

The rdd-doctor `--category state` command SHALL:

- Scan `.rddf/state/` for JSON files
- Match each file to its schema in `_lib/schemas/`
- Report CRITICAL if declared schema file is missing
- Report WARNING if schema exists but no corresponding state file (declared but not yet created)
- Report INFO for valid schema-file pairs

**Boundary:** rdd-doctor validates structure only. It does NOT implement read/write for specific state files.

### 4. Diff Review Against Existing Schemas

The 6 schema files already exist in `_lib/schemas/` at the project root. They are:
- `cross_repo_pending_schema.json`
- `cross_repo_audit_schema.json`
- `mcp_trace_schema.json`
- `contract_cache_schema.json`
- `cross_repo_deps_cache_schema.json`
- `hub_metrics_schema.json`

**Diff review approach:** The acceptance criteria requires verifying the schemas match the proposal specs. No schema creation is needed since files already exist.

### 5. Test Coverage Strategy

Unit tests in `tests/unit/test_cross_repo_schemas.py`:
- 6 schemas × 3 test cases = 18 test minimum
- Schema: valid record (passes validation)
- Schema: invalid field value (fails with specific error)
- Schema: missing required field (fails with required property error)

Tests use `jsonschema.Draft7Validator` directly.

## Risks / Trade-offs

**Risk:** Schema drift if proposals modify state file format without updating schemas
**Mitigation:** Schema files are in `_lib/schemas/` (centralized), and rdd-doctor detects drift

**Trade-off:** Keeping schemas ≤200 lines vs. comprehensive field documentation
**Mitigation:** Field descriptions are in `docs/schemas/cross-repo-schemas.md` (separate doc)

**Risk:** Version bump required for any schema change
**Mitigation:** Version bump is a simple JSON edit; transition period prevents breaking changes
