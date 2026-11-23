# fix-33-handlers-project-root-anti-pattern Specification

## Purpose
TBD - created by archiving change fix-33-handlers-project-root-anti-pattern. Update Purpose after archive.
## Requirements
### Requirement: unified-project-root-resolution

All `_lib/cli/*.py` handlers SHALL resolve `project_root` via the single helper `resolve_project_root()` (re-exported from `_lib.cli.__init__`) instead of repeating the `os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()` anti-pattern. The handler resolution flow SHALL be:

1. **First** check `os.environ["RDDF_PROJECT_ROOT"]` (override for tests + `--main.py:203` setdefault injection)
2. **Otherwise** call `resolve_project_root()` (submodule-aware git toplevel probe per ADR-0033)
3. **Fallback** `os.getcwd()` (when not in a git repo)

This guarantees that handlers work correctly in:
- Direct `python3 -m _lib.cli <sub>` invocations (no `__main__.py` env injection)
- Git submodule contexts (per ADR-0033 submodule-aware resolution)
- Worktree contexts (per ADR-0033 linked worktree handling)
- Non-git directories (fallback to cwd)

#### Scenario: handler resolves correctly without env injection

- **WHEN** a handler is invoked directly via `python3 -m _lib.cli <sub>` from a subdirectory of an rdd-workflow project (no `__main__.py` env injection)
- **THEN** the handler SHALL call `resolve_project_root()` which returns the git toplevel
- **AND** the handler SHALL find `.rddf/state/` correctly

#### Scenario: RDDF_PROJECT_ROOT override preserved

- **WHEN** `RDDF_PROJECT_ROOT` is set in the environment
- **THEN** the handler SHALL use that path (override) instead of `resolve_project_root()`
- **AND** the override behavior SHALL be preserved for backward compatibility with `__main__.py:203` `os.environ.setdefault(...)` injection

#### Scenario: non-git directory fallback

- **WHEN** the handler is invoked from a directory that is not inside any git repository
- **THEN** `resolve_project_root()` SHALL fall back to `os.getcwd()`
- **AND** the handler SHALL NOT crash

### Requirement: resolve_project_root-public-api

`_lib/cli/__init__.py` SHALL re-export `resolve_project_root` (originally defined in `_lib/cli/__main__.py`) so that handlers can import it from `skills._lib.cli` without depending on the `__main__` module's side effects.

#### Scenario: handler imports resolve_project_root

- **WHEN** a handler imports `from skills._lib.cli import resolve_project_root`
- **THEN** the import SHALL succeed without ImportError
- **AND** `resolve_project_root()` SHALL be callable

### Requirement: anti-pattern-elimination

The `_lib/cli/*.py` handler files SHALL NOT contain the anti-pattern `os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()` (excluding the legitimate use site in `_lib/cli/__main__.py:203` which is the env-injection point).

#### Scenario: zero anti-pattern occurrences in handlers

- **WHEN** running `grep -rn 'RDDF_PROJECT_ROOT.*or.*os.getcwd' _lib/cli/*.py | grep -v __main__.py`
- **THEN** the count of matches SHALL be zero
- **AND** only the legitimate use site in `__main__.py:203` (env injection) SHALL remain

