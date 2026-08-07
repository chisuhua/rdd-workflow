# fix-ship-archive-resolve-lib-path

## Why

Lightweight archive pre-flight directly invokes `$project_root/_lib/validate_delta_targets.py`. External projects commonly have no project-local `_lib`; the validator is provided by the global installation and must be resolved through `resolve_rdd_lib_dir`.

## What Changes

- Resolve the shared library directory through the existing `resolve_rdd_lib_dir` function before invoking `validate_delta_targets.py`.
- Fail closed with a clear diagnostic when the shared library cannot be resolved.
- Preserve validator arguments, return-code behavior, and lightweight/worktree archive semantics.
- Add an external-project regression test without a project-local `_lib` directory.

## Capabilities

### Modified Capabilities

- Lightweight archive validation uses the global shared-library resolver.

## Impact

- `skills/guide-ship/scripts/ship_archive.sh` and its archive integration tests.
- No changes to delta target rules or installation layout.

## Acceptance

- Archive no longer requires `$project_root/_lib/validate_delta_targets.py`.
- External-project lightweight archive reaches the global validator without a local `_lib` symlink.
- Missing shared library produces a non-zero result and clear diagnostic.
- Focused and full regression tests pass.
