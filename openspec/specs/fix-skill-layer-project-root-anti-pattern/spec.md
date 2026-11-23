# fix-skill-layer-project-root-anti-pattern Specification

## Purpose
TBD - created by archiving change fix-skill-layer-project-root-anti-pattern. Update Purpose after archive.
## Requirements
### Requirement: unified-project-root-resolution-in-skill-scripts

All `skills/*/scripts/*.py` skill scripts SHALL resolve `project_root` via the helper `resolve_project_root()` (imported from `_lib.cli.__main__`) instead of using `os.environ.get("...") or os.getcwd()`. The dual-track env var convention SHALL be preserved:

1. **`RDDF_PROJECT_ROOT`** (Python __main__.py:203 setdefault injection) — used by `report-issue`, `sync-hub`, `watch-hub`
2. **`PROJECT_ROOT`** (bash scripts `export` — e.g. `from_issue.sh:76`, `from_roadmap.sh:91`, `execute_step7.sh:22`) — used by `propose`

The handler resolution flow per script SHALL be:

1. **First** check the script's own env var (override for tests + caller injection)
2. **Otherwise** call `resolve_project_root()` (submodule-aware git toplevel probe per ADR-0033)
3. **Fallback** `os.getcwd()` (when not in a git repo)

This guarantees that skill scripts work correctly in:
- Direct `python3 skills/sync-hub/scripts/sync_hub.py --contract X` invocations (no `__main__.py` env injection)
- Git submodule contexts (per ADR-0033 submodule-aware resolution)
- Worktree contexts (per ADR-0033 linked worktree handling)
- Non-git directories (fallback to cwd)

#### Scenario: sync_hub resolves correctly without env injection

- **WHEN** `skills/sync-hub/scripts/sync_hub.py` is invoked directly via `python3` from a subdirectory of an rdd-workflow project (no `RDDF_PROJECT_ROOT` env injection)
- **THEN** the script SHALL call `resolve_project_root()` which returns the git toplevel
- **AND** the script SHALL find the project's `.rddf/state/` correctly

#### Scenario: sync_hub RDDF_PROJECT_ROOT override preserved

- **WHEN** `RDDF_PROJECT_ROOT` is set in the environment and `sync_hub.py` is invoked
- **THEN** the script SHALL use that path (override) instead of `resolve_project_root()`
- **AND** the override behavior SHALL be preserved for backward compatibility with `__main__.py:203` `os.environ.setdefault(...)` injection

#### Scenario: propose_quality_check uses PROJECT_ROOT env var

- **WHEN** `skills/propose/scripts/propose_quality_check.py` is invoked from a bash script that `export PROJECT_ROOT=...`
- **THEN** the script SHALL use that `PROJECT_ROOT` value
- **AND** the script SHALL NOT attempt to read `RDDF_PROJECT_ROOT` (env var name preservation per MN-SL-1)

#### Scenario: dual-track env vars do not interfere

- **WHEN** both `RDDF_PROJECT_ROOT` and `PROJECT_ROOT` are set in the environment
- **THEN** `sync_hub.py` reads only `RDDF_PROJECT_ROOT`
- **AND** `propose_quality_check.py` reads only `PROJECT_ROOT`
- **AND** neither script's resolution is influenced by the other env var

#### Scenario: non-git directory fallback

- **WHEN** a skill script is invoked from a directory that is not inside any git repository
- **THEN** `resolve_project_root()` SHALL fall back to `os.getcwd()`
- **AND** the script SHALL NOT crash

### Requirement: anti-pattern-elimination-in-skill-scripts

The 5 target skill scripts SHALL NOT contain the anti-pattern `os.environ.get("...") or os.getcwd()`. The bash scripts that `export PROJECT_ROOT=...` SHALL be preserved (they correctly use `skills/_lib/orchestrator_entry.sh:_resolve_project_root()` helper).

#### Scenario: zero anti-pattern occurrences in 5 scripts

- **WHEN** running `grep -l 'or os.getcwd()' skills/{propose,report-issue,sync-hub,watch-hub}/scripts/*.py`
- **THEN** the count of matches SHALL be zero

