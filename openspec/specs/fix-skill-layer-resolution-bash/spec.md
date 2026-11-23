# fix-skill-layer-resolution-bash Specification

## Purpose
TBD - created by archiving change fix-skill-layer-resolution-bash. Update Purpose after archive.
## Requirements
### Requirement: bash-script-uses-resolve-project-root-helper

`skills/rdd-arch/scripts/roadmap_incremental_update.sh` SHALL resolve `RDDF_PROJECT_ROOT` via the bash helper `_resolve_project_root` defined in `skills/_lib/orchestrator_entry.sh:33`, instead of manually re-implementing the env-var-or-git-probe-or-cwd logic.

The helper invocation SHALL follow the existing convention from `skills/rdd-arch/scripts/arch_env_check.sh:21` — i.e., try sourcing from the local checkout first, then fall back to the global install at `$HOME/.agents/skills/_lib/orchestrator_entry.sh`.

#### Scenario: roadmap_incremental_update.sh calls _resolve_project_root

- **WHEN** `skills/rdd-arch/scripts/roadmap_incremental_update.sh` is invoked
- **THEN** the script SHALL source `orchestrator_entry.sh` (local first, then global fallback)
- **AND** the script SHALL call `_resolve_project_root` (not manually duplicate the logic)
- **AND** the script SHALL export `RDDF_PROJECT_ROOT` after the call

#### Scenario: manual RDDF_PROJECT_ROOT env check removed

- **WHEN** inspecting `skills/rdd-arch/scripts/roadmap_incremental_update.sh` for the old manual check pattern
- **THEN** the text `"RDDF_PROJECT_ROOT is required"` SHALL NOT appear (that was the old error message)
- **AND** the script SHALL rely on `_resolve_project_root`'s own error reporting

#### Scenario: directory-not-found error preserved

- **WHEN** `_resolve_project_root` returns a non-directory path (e.g. env override points to a deleted directory)
- **THEN** the script SHALL exit with code 2 and print a clear error message
- **AND** semantics parity is preserved vs. the old manual implementation (both exit 2 on bad path)

### Requirement: bash-helper-single-source-of-truth

The bash helper `_resolve_project_root` in `skills/_lib/orchestrator_entry.sh:33` remains the single source of truth for bash-side project_root resolution. Skill-layer bash scripts SHALL use this helper instead of duplicating the git-rev-parse fallback logic.

#### Scenario: no new manual duplicate of git-rev-parse-show-toplevel

- **WHEN** scanning all `skills/*/scripts/*.sh` for the pattern `git rev-parse.*show-toplevel`
- **THEN** the only matches SHALL be the canonical helper at `orchestrator_entry.sh:33` and `arch_env_check.sh:21` (initial fallback before the helper is sourced)
  <!-- 2026-11-20 (retire-execute-skill): `select_worktree.sh` 随 execute 技能归档，示例改为仍存在的 arch_env_check.sh -->
- **AND** `roadmap_incremental_update.sh` SHALL NOT contain a manual `git rev-parse --show-toplevel` invocation

### Requirement: symmetric-bash-python-helper-usage

After this change, the bash layer SHALL mirror the Python layer's wrapper pattern:
- Bash: `skills/_lib/orchestrator_entry.sh::_resolve_project_root` + 2 calling scripts
- Python: `skills/_lib/_python_resolve_project_root.py::resolve_project_root` + 5 calling scripts

#### Scenario: 2 bash scripts use the helper

> 2026-11-20 (retire-execute-skill): `select_worktree.sh` 随 execute 技能归档，消费者从 3 减为 2。

- **WHEN** running `grep -l "_resolve_project_root" skills/*/scripts/*.sh`
- **THEN** the count SHALL be exactly 2: `arch_env_check.sh`, `roadmap_incremental_update.sh`

