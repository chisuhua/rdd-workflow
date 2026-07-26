## Context

`ConfigParser.parse()` (in `skills/_lib/config.py`) merges config from multiple sources (defaults → `.rddf.json` → env vars → `loop.yaml` → runtime overrides) and calls `_validate()` for basic checks (mode enum, numeric bounds). However, `_validate()` only checks a hardcoded set of fields. Any misnamed key, extra unknown key, or wrong type in a non-checked field passes through silently, causing the Loop engine to use default values without warning.

The project already uses `jsonschema` for validating other artifacts (state vector, session, etc.). The `_validate_schema()` function and `config_schema.json` already exist as a foundation, but the schema uses `additionalProperties: true` which allows unknown keys to pass through.

## Goals / Non-Goals

**Goals:**
- Provide JSON Schema validation of the merged config at parse time
- Catch misnamed keys (e.g., `maxIterations` → `max_iterations`), wrong types, and out-of-range values
- Raise `ConfigError` with a clear message on failure
- Generate unit tests covering valid, invalid, and missing-schema scenarios

**Non-Goals:**
- Changing the config file format (`.rddf.json`, `loop.yaml`)
- Changing the priority-merge logic
- Validating `phase_templates.yaml` (out of scope per improvement)
- Modifying the `LoopEngine` config consumption logic

## Decisions

### Decision 1: Schema validation runs at the end of `parse()`, after all merges

- **Why**: The merged config is the final authority. Validating individual sources before merge would produce false positives (e.g., a field in `.rddf.json` that gets overridden by `loop.yaml`).
- **Alternative**: Validate after each source merge
- **Rejected**: Would produce transient errors for fields that are intentionally overridden by higher-priority sources

### Decision 2: Schema uses `additionalProperties: false` for `loop` and `interaction` sections

- **Why**: The primary use case is catching misnamed keys. `additionalProperties: false` ensures any unrecognized key produces a clear error like `Additional properties are not allowed ('maxIterations' was unexpected)`.
- **Alternative**: `additionalProperties: true` with custom validation
- **Rejected**: Custom validation would duplicate what jsonschema already provides for free

### Decision 3: Missing schema file → skip validation (backward compatibility)

- **Why**: Older installations or partial checkouts may not have the schema file. The validation is an enhancement, not a hard requirement.
- **Alternative**: Fail with an error if schema is missing
- **Rejected**: Would break existing installations

### Decision 4: Unit tests cover three scenarios: valid, invalid, and missing schema

- **Why**: These three scenarios cover the full risk surface:
  - Valid config: regression guard — ensure validation doesn't break working configs
  - Invalid config: the primary feature — ensure misnamed keys are caught
  - Missing schema: backward compatibility — ensure older installations work

## Schema Design

```
config_schema.json (Draft 7):
  - interaction:
      mode: string, enum [loop, menu, hybrid]
      additionalProperties: false
  - loop:
      max_iterations: integer, minimum 1
      max_retries: integer, minimum 0
      oscillation_window: integer, minimum 1
      oscillation_distinct_threshold: integer, minimum 1
      circuit_breaker_threshold: integer, minimum 1
      action_timeout_seconds: number, minimum 1
      additionalProperties: false
  - triggers:
      enabled: boolean
      webhook_port: integer
      fs_watch_interval: number
      git_poll_interval: number
      safety: object (with nested properties)
      additionalProperties: true  # triggers has more optional fields
```

## API

```python
class ConfigParser:
    def parse(self, ...) -> dict:
        ...
        _validate(config)          # existing: mode enum, numeric bounds
        _validate_schema(config)   # new: jsonschema validation
        return config

def _validate_schema(config: dict, project_root: str | None = None) -> None:
    """Validate merged config against config_schema.json.
    Raises ConfigError if validation fails.
    Silently skips if schema file is missing.
    """
```

## Test Plan

| Test | Input | Expected |
|------|-------|----------|
| Valid config passes | `{interaction: {mode: loop}}` | parse() succeeds |
| Config with misnamed key fails | `{loop: {maxIterations: 50}}` | ConfigError with "maxIterations" in message |
| Config with wrong type fails | `{loop: {max_iterations: "abc"}}` | ConfigError with type info |
| Config with out-of-range value fails | `{loop: {max_iterations: 0}}` | ConfigError with "minimum" |
| Missing schema file skips | No config_schema.json | parse() succeeds, no error |
| Mode enum violation | `{interaction: {mode: invalid}}` | ConfigError |