# add-config-validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden config_schema.json to reject unknown keys in interaction and loop sections, catching user typos like `maxIterations` instead of `max_iterations` at parse time.

**Architecture:** Change `additionalProperties` from `true` to `false` for the `interaction` and `loop` sections in `config_schema.json`. Before doing so, add the two existing default keys (`interaction.menu_items`, `loop.retry_backoff_seconds`) to the schema's `properties` so that valid configs continue to pass. Add unit tests covering unknown-key rejection, valid-config-passes, wrong-type rejection, out-of-range rejection, and missing-schema backward compatibility.

**Tech Stack:** Python 3.11+, jsonschema (Draft 7), pytest

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/schemas/config_schema.json` | JSON Schema for config validation; add missing properties, flip additionalProperties to false for interaction and loop |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_config_schema.py` | New test file: unknown-key rejection, valid-config-passes, wrong-type rejection, out-of-range rejection, missing-schema backward compat |

---

### Task 1: Write failing test for unknown key in loop rejected

**Files:**
- Create: `tests/unit/test_config_schema.py`
- Test: `tests/unit/test_config_schema.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for config schema validation - unknown key rejection and schema hardening."""
import json
import os
import pytest
from skills._lib.config import ConfigParser, ConfigError


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all RDDF_* env vars for the test."""
    for k in list(os.environ):
        if k.startswith("RDDF_"):
            monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_unknown_key_in_loop_rejected(tmp_path, clean_env):
    """A misnamed key like 'maxIterations' (should be 'max_iterations') must raise ConfigError."""
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({"loop": {"maxIterations": 50}}))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError, match="maxIterations"):
        parser.parse()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_config_schema.py::test_unknown_key_in_loop_rejected -xvs`
Expected: FAIL - the test expects ConfigError but parse() succeeds (unknown key passes through silently because `additionalProperties` is currently `true`)

- [ ] **Step 3: Write minimal implementation**

Edit `skills/_lib/schemas/config_schema.json`:
1. Add `menu_items` to `interaction.properties` (array of strings) - it's in defaults.py but missing from schema
2. Add `retry_backoff_seconds` to `loop.properties` (number, minimum 0) - it's in defaults.py but missing from schema
3. Change `"additionalProperties": true` to `"additionalProperties": false` in the `interaction` section
4. Change `"additionalProperties": true` to `"additionalProperties": false` in the `loop` section

The full `interaction` section should become:
```json
"interaction": {
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "mode": {
      "type": "string",
      "enum": ["loop", "menu", "hybrid"],
      "description": "Interaction mode: loop (autonomous), menu (manual), hybrid (mixed)"
    },
    "menu_items": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Menu items available in menu/hybrid mode"
    }
  }
}
```

The `loop` section should add `retry_backoff_seconds`:
```json
"retry_backoff_seconds": {
  "type": "number",
  "minimum": 0,
  "description": "Backoff delay in seconds between retries (must be >= 0)"
}
```
And change `"additionalProperties": true` to `"additionalProperties": false`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_config_schema.py::test_unknown_key_in_loop_rejected -xvs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/schemas/config_schema.json tests/unit/test_config_schema.py
git commit -m "feat(config-schema): reject unknown keys in interaction and loop sections"
```

---

### Task 2: Add test for valid config passing schema validation

**Files:**
- Modify: `tests/unit/test_config_schema.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_config_schema.py`:

```python
def test_valid_config_passes_schema(tmp_path, clean_env):
    """A valid config with known keys in interaction and loop sections must parse successfully."""
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({
        "interaction": {"mode": "loop", "menu_items": ["propose", "execute"]},
        "loop": {"max_iterations": 50, "max_retries": 3, "retry_backoff_seconds": 5}
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["interaction"]["mode"] == "loop"
    assert config["loop"]["max_iterations"] == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_config_schema.py::test_valid_config_passes_schema -xvs`
Expected: PASS (this is a regression guard - valid config should already pass with the hardened schema from Task 1). If it passes, that's the expected outcome for a regression guard test.

- [ ] **Step 3: Write minimal implementation**

No implementation needed - this is a regression guard. The schema from Task 1 already allows valid keys.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_config_schema.py::test_valid_config_passes_schema -xvs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_config_schema.py
git commit -m "test: add valid config schema regression test"
```

---

### Task 3: Add test for wrong type rejected by schema

**Files:**
- Modify: `tests/unit/test_config_schema.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_config_schema.py`:

```python
def test_wrong_type_rejected_by_schema(tmp_path, clean_env):
    """A wrong type for max_iterations (string instead of integer) must raise ConfigError."""
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({"loop": {"max_iterations": "abc"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError, match="max_iterations"):
        parser.parse()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_config_schema.py::test_wrong_type_rejected_by_schema -xvs`
Expected: PASS (the schema already has `"type": "integer"` for `max_iterations`, and `_validate()` also checks this). This is a regression guard test.

- [ ] **Step 3: Write minimal implementation**

No implementation needed - the schema already has type constraints. The existing `_validate()` also catches this with a different message, but the schema provides a second layer.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_config_schema.py::test_wrong_type_rejected_by_schema -xvs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_config_schema.py
git commit -m "test: add wrong type schema rejection test"
```

---

### Task 4: Add test for out-of-range value rejected by schema

**Files:**
- Modify: `tests/unit/test_config_schema.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_config_schema.py`:

```python
def test_out_of_range_rejected(tmp_path, clean_env):
    """An out-of-range value (max_iterations: 0) must raise ConfigError with minimum info."""
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({"loop": {"max_iterations": 0}}))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError, match="max_iterations"):
        parser.parse()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_config_schema.py::test_out_of_range_rejected -xvs`
Expected: PASS (the schema has `"minimum": 1` for `max_iterations`, and `_validate()` also checks this). This is a regression guard test.

- [ ] **Step 3: Write minimal implementation**

No implementation needed - the schema already has `"minimum": 1` for `max_iterations`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_config_schema.py::test_out_of_range_rejected -xvs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_config_schema.py
git commit -m "test: add out-of-range value schema rejection test"
```

---

### Task 5: Add test for missing schema file skipping validation

**Files:**
- Modify: `tests/unit/test_config_schema.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_config_schema.py`:

```python
def test_missing_schema_skips_validation(tmp_path, clean_env, monkeypatch):
    """If the schema file is missing, validation is skipped (backward compatibility)."""
    # Simulate missing schema by patching the path to point to a non-existent file
    import skills._lib.config as config_module
    original_path = config_module._CONFIG_SCHEMA_PATH
    monkeypatch.setattr(config_module, "_CONFIG_SCHEMA_PATH", "/nonexistent/schema.json")
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({"interaction": {"mode": "loop"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()  # should NOT raise
    assert config["interaction"]["mode"] == "loop"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_config_schema.py::test_missing_schema_skips_validation -xvs`
Expected: PASS (the `_validate_schema()` function already checks `if not os.path.isfile(_CONFIG_SCHEMA_PATH): return`). This is a regression guard test.

- [ ] **Step 3: Write minimal implementation**

No implementation needed - the `_validate_schema()` function already has the missing-file guard.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_config_schema.py::test_missing_schema_skips_validation -xvs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_config_schema.py
git commit -m "test: add missing schema backward compatibility test"
```

---

## Self-Review

### 1. Spec Coverage

| Spec Requirement (from proposal.md/design.md) | Task |
|---|---|
| Add `additionalProperties: false` for `interaction` section | Task 1 Step 3 |
| Add `additionalProperties: false` for `loop` section | Task 1 Step 3 |
| Raise `ConfigError` on misnamed keys | Task 1 (test) + Task 1 Step 3 (implementation) |
| Missing schema file -> skip validation | Task 5 (test, already implemented) |
| Unit test: valid config passes | Task 2 |
| Unit test: invalid config raises ConfigError | Task 1, 3, 4 |
| Unit test: missing schema skips | Task 5 |
| Backward compatible (existing configs pass) | Task 1 adds missing properties first, Task 2 verifies |

No gaps identified.

### 2. Placeholder Scan

No TBD, TODO, or placeholder patterns. All steps contain actual code.

### 3. Type Consistency

- `ConfigError` is imported from `skills._lib.config` in all tasks - consistent
- `ConfigParser` constructor takes `project_root=str` - consistent across all tests
- `_CONFIG_SCHEMA_PATH` is a module-level attribute in `config.py`, patched via `monkeypatch.setattr` in Task 5 - consistent with the module's import path `skills._lib.config`
- Schema property names match defaults.py exactly: `menu_items`, `retry_backoff_seconds`

### 4. Critical Note: Missing Properties Added Before additionalProperties: false

The defaults.py defines `interaction.menu_items` and `loop.retry_backoff_seconds` which are NOT in the current schema properties. If we flip `additionalProperties: false` without adding these, ALL existing config parsing would break because the merged config always includes defaults. Task 1 Step 3 addresses this by adding both properties before flipping the flag.
