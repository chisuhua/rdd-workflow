## 1. Harden config_schema.json to reject unknown keys (T1)

- [ ] 1.1 **Write failing test**: Create `tests/unit/test_config_schema.py` with test `test_unknown_key_in_loop_rejected` that writes a `.rddf.json` with `{loop: {maxIterations: 50}}` and asserts `ConfigError` is raised with "maxIterations" in the message
- [ ] 1.2 **Verify fail**: Run `python3 -m pytest tests/unit/test_config_schema.py::test_unknown_key_in_loop_rejected -xvs` — confirm it fails (unknown key passes through silently)
- [ ] 1.3 **Implement**: Change `skills/_lib/schemas/config_schema.json` — set `"additionalProperties": false` for `interaction` and `loop` sections (currently `true`)
- [ ] 1.4 **Verify pass**: Re-run the test — confirm it passes (unknown key now raises `ConfigError`)
- [ ] 1.5 **Commit**: `git add skills/_lib/schemas/config_schema.json tests/unit/test_config_schema.py && git commit -m "feat(config-schema): reject unknown keys in interaction and loop sections"`

## 2. Add test: valid config passes schema validation (T2)

- [ ] 2.1 **Write failing test**: Add `test_valid_config_passes_schema` to `tests/unit/test_config_schema.py` — create a `.rddf.json` with valid `{interaction: {mode: loop}, loop: {max_iterations: 50, max_retries: 3}}` and assert `parse()` succeeds
- [ ] 2.2 **Verify fail**: Run the test — confirm it passes already (valid config is already valid)
- [ ] 2.3 **N/A** (test already passes with current code)
- [ ] 2.4 **Verify pass**: Confirm the test is stable
- [ ] 2.5 **Commit**: `git add tests/unit/test_config_schema.py && git commit -m "test: add valid config schema test"`

## 3. Add test: wrong type rejected by schema (T3)

- [ ] 3.1 **Write failing test**: Add `test_wrong_type_rejected_by_schema` — write `.rddf.json` with `{loop: {max_iterations: "abc"}}` and assert `ConfigError` with type information in the message
- [ ] 3.2 **Verify fail**: Run the test — confirm it fails (string passes through to defaults)
- [ ] 3.3 **N/A** (schema already has `"type": "integer"` for `max_iterations`, should catch this)
- [ ] 3.4 **Verify pass**: Re-run — confirm it passes
- [ ] 3.5 **Commit**: `git add tests/unit/test_config_schema.py && git commit -m "test: add wrong type schema test"`

## 4. Add test: out-of-range value rejected by schema (T4)

- [ ] 4.1 **Write failing test**: Add `test_out_of_range_rejected` — write `.rddf.json` with `{loop: {max_iterations: 0}}` and assert `ConfigError` with "minimum" in the message
- [ ] 4.2 **Verify fail**: Run — confirm it fails (0 passes `_validate` but not schema)
- [ ] 4.3 **N/A** (schema already has `"minimum": 1` for `max_iterations`)
- [ ] 4.4 **Verify pass**: Re-run — confirm it passes
- [ ] 4.5 **Commit**: `git add tests/unit/test_config_schema.py && git commit -m "test: add out-of-range schema test"`

## 5. Add test: missing schema file skips validation (T5)

- [ ] 5.1 **Write failing test**: Add `test_missing_schema_skips_validation` — temporarily rename `config_schema.json` to a backup name, parse a valid config, assert success, then restore
- [ ] 5.2 **Verify fail**: Run — should pass (backward compatibility works)
- [ ] 5.3 **N/A** (already implemented)
- [ ] 5.4 **Verify pass**: Confirm the test is stable
- [ ] 5.5 **Commit**: `git add tests/unit/test_config_schema.py && git commit -m "test: add missing schema skip test"`