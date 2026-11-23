# add-skill-layer-resolve-project-root-helper Specification

## Purpose
TBD - created by archiving change add-skill-layer-resolve-project-root-helper. Update Purpose after archive.
## Requirements
### Requirement: skill-layer-python-wrapper

`skills/_lib/_python_resolve_project_root.py` SHALL expose a single `resolve_project_root()` function that mirrors the bash helper `skills/_lib/orchestrator_entry.sh::_resolve_project_root` (per add-skill-layer-resolve-project-root-helper). Resolution flow:

1. **First** check `os.environ["RDDF_PROJECT_ROOT"]` (override for tests + caller injection)
2. **Otherwise** call `_lib.cli.__main__.resolve_project_root()` (submodule-aware git probe per ADR-0033)
3. **Fallback** `os.getcwd()` (when not in a git repo)

#### Scenario: wrapper resolves correctly without env injection

- **WHEN** a skill script imports `from skills._lib._python_resolve_project_root import resolve_project_root` and invokes it from a project subdirectory (no `RDDF_PROJECT_ROOT` env var)
- **THEN** the wrapper SHALL call `_lib.cli.__main__.resolve_project_root()` which returns the git toplevel
- **AND** the wrapper SHALL return the git toplevel as the project root

#### Scenario: wrapper honors RDDF_PROJECT_ROOT override

- **WHEN** `RDDF_PROJECT_ROOT` is set in the environment
- **THEN** the wrapper SHALL return that path (override) instead of calling `_lib.cli.__main__.resolve_project_root()`
- **AND** the override behavior SHALL be preserved for backward compatibility with `_lib.cli.__main__.py:203` `os.environ.setdefault(...)` injection

#### Scenario: wrapper does not trigger circular import

- **WHEN** a skill script imports `from skills._lib._python_resolve_project_root import resolve_project_root`
- **THEN** the import SHALL succeed without triggering `_lib.cli.__main__` module load (lazy import via function call, not at module load)
- **AND** subsequent invocation SHALL resolve to the correct project root

### Requirement: no-direct-dispatcher-import

The 5 skill scripts that previously used `from _lib.cli.__main__ import resolve_project_root` SHALL instead use `from skills._lib._python_resolve_project_root import resolve_project_root` — restoring the skill layer's self-contained convention (per `skills/_lib/iteration/__init__.py:3-10`).

#### Scenario: zero direct dispatcher imports in skill scripts

- **WHEN** running `grep -rn 'from _lib.cli' skills/{propose,report-issue,sync-hub,watch-hub}/scripts/*.py`
- **THEN** the count of matches SHALL be zero
- **AND** all 5 target scripts SHALL import `from skills._lib._python_resolve_project_root import resolve_project_root` instead

### Requirement: behavior-parity-with-dispatcher

The skill-layer wrapper SHALL produce identical results to `_lib.cli.__main__.resolve_project_root()` in all cases where the env var is unset, and SHALL respect the env var override when set.

#### Scenario: parity with dispatcher resolver

- **WHEN** comparing `skills._lib._python_resolve_project_root.resolve_project_root()` and `_lib.cli.__main__.resolve_project_root()` outputs under identical conditions (same env, same cwd, same git state)
- **THEN** the two functions SHALL return identical strings
- **AND** existing `tests/unit/test_skill_layer_project_root_resolution.py::test_zero_anti_pattern_in_skill_scripts` SHALL continue to pass

