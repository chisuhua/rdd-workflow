# ship-archive-resolver Specification

## Purpose
TBD - created by archiving change fix-ship-archive-resolve-lib-path. Update Purpose after archive.
## Requirements
### Requirement: Lightweight archive resolves the shared validator globally
The archive helper SHALL resolve `validate_delta_targets.py` through `resolve_rdd_lib_dir` instead of requiring a project-local `_lib` directory.

#### Scenario: External project has only the global installation
- GIVEN an active change in an external project
- AND the project has no `_lib/validate_delta_targets.py`
- AND the global shared library is available
- WHEN lightweight archive pre-flight runs
- THEN the global validator is invoked and archive can continue

#### Scenario: Shared library cannot be resolved
- GIVEN lightweight archive cannot resolve the shared `_lib`
- WHEN archive pre-flight runs
- THEN it prints a clear diagnostic and returns non-zero

