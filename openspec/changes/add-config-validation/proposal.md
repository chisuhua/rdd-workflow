## Why

Root `config.yaml` / `.rddf.json` / `loop.yaml` are user-editable entry points consumed by `config.py::ConfigParser`. A user typo — e.g., `max_iterations` → `maxIterations` — causes `ConfigParser` to silently fall back to the default value (100 for `max_iterations`). This is a silent degradation, not an error. The user has no way to know their configuration was ignored.

Oracle code review 2026-07-19 #8 identified this as a real, user-triggerable problem: any misnamed key, wrong type, or out-of-range value in the config files silently produces default behavior with zero feedback.

## What Changes

- **Add** `validate()` method to `ConfigParser` (called at the end of `parse()`) that validates the merged config against JSON Schema
- **Add** `skills/_lib/schemas/config_schema.json` — JSON Schema with `required` keys, type constraints, and numeric bounds for `interaction`, `loop`, and `triggers` sections
- **Add** schema validation logic that raises `ConfigError(...)` with a clear message on failure, instead of silent fallback
- **Add** backward-compatibility: missing schema file → skip validation (older installations continue to work)
- **Add** unit tests: valid config passes, invalid config raises `ConfigError`, missing schema skips

## Capabilities

### New Capabilities
- `config-validation`: JSON Schema-backed validation of merged configuration at parse time, with clear error messages on misnamed keys, wrong types, or out-of-range values

### Modified Capabilities
- `configuration`: The existing `ConfigParser` now validates the merged config against a schema, catching user errors early

## Impact

- **New code**: ~50 lines (config_schema.json) + ~40 lines (validate method) + ~60 lines (unit tests) = ~150 lines
- **Dependencies**: `jsonschema` (already used by the project for other schemas)
- **Compatibility**: 100% backward compatible — missing schema file skips validation; all existing configs pass validation
- **Risk**: Low — additive change; validation can be skipped by removing the schema file
- **Source**: Oracle 代码审查 2026-07-19 #8, improvement `add-config-validation`