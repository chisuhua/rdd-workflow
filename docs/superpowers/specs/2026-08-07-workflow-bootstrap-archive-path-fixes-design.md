# Workflow Bootstrap and Archive Path Fixes Design

**Date**: 2026-08-07
**Status**: Approved for implementation

## Goal

Make the rdd-workflow global-install path reliable for external projects by removing incorrect `_lib` fallback paths and resolving archive validation helpers through the existing shared-library resolver.

## Scope

This design contains two independent bug fixes:

1. `fix-bootstrap-fallback-paths`
   - Correct the runtime fallback from `$HOME/.agents/_lib/skill_root.sh` to `$HOME/.agents/skills/_lib/skill_root.sh`.
   - Apply the correction to all runtime shell scripts and documented `SKILL.md` examples found by the repository scan.
   - Preserve the existing local-project-first fallback order and all surrounding behavior.

2. `fix-ship-archive-resolve-lib-path`
   - Replace `ship_archive.sh`'s hardcoded `$project_root/_lib/validate_delta_targets.py` lookup with `resolve_rdd_lib_dir`.
   - Keep archive validation fail-closed when the shared library cannot be resolved.
   - Preserve both lightweight and worktree archive modes.

## Files and Boundaries

### Bootstrap fallback

Runtime scripts currently containing the incorrect fallback include:

- `skills/guide-arch/scripts/arch_done_gate.sh`
- `skills/guide-arch/scripts/write_arch_handoff.sh`
- `skills/guide-arch/scripts/arch_env_check.sh`
- `skills/guide-design/scripts/design_env_check.sh`
- `skills/guide-plan/scripts/plan_done_gate.sh`
- `skills/guide-plan/scripts/plan_intake.sh`
- `skills/guide-ship/scripts/ship_env_check.sh`
- `skills/propose/scripts/*.sh` where the scan confirms the same fallback
- `skills/rdd-env-check/scripts/env_check.sh`
- `skills/roadmap/SKILL.md`, `skills/status/SKILL.md`, `skills/deps/SKILL.md`, `skills/execute/SKILL.md`, `skills/feature/SKILL.md`, `skills/guide-arch/SKILL.md`, `skills/guide-design/SKILL.md`, `skills/guide-plan/SKILL.md`, `skills/guide-ship/SKILL.md`, and other scanned examples containing the same literal.

The implementation will update only the exact fallback literal, without changing discovery order, function names, or state semantics.

### Archive resolver

`skills/guide-ship/scripts/ship_archive.sh` will resolve the shared library once in the lightweight archive pre-flight and invoke:

```bash
local rdd_lib_dir
rdd_lib_dir="$(resolve_rdd_lib_dir)" || {
  echo "❌ Cannot resolve rdd-workflow _lib directory" >&2
  return 1
}
python3 "$rdd_lib_dir/validate_delta_targets.py" "$change_name"
```

The resolver must be available through the normal bootstrap already loaded by the archive helper. No project-local `_lib` symlink will be required.

## Tests

- Add regression coverage for an external project with no project-local `_lib`:
  - corrected fallback resolves the global skill root;
  - arch-done/design-done/plan-done helper entry points do not fail because of the old path;
  - lightweight archive resolves and runs the global `validate_delta_targets.py`.
- Preserve the existing 23-case isolated playground full-flow test.
- Run focused Bats tests first, then `./test.sh --full --regression` before archive.

## Non-Goals

- No changes to the global installation layout.
- No changes to `resolve_rdd_lib_dir` precedence.
- No refactoring of unrelated shell helpers.
- No change to OpenSpec schemas or archive semantics beyond resolving the validator path.

## Acceptance Criteria

- `grep` finds no executable/documented occurrence of `$HOME/.agents/_lib/skill_root.sh` in the supported workflow surfaces.
- An external project using only `~/.agents/skills/` can enter arch, design, plan, and ship helpers without fallback-path errors.
- Lightweight archive succeeds without `<project_root>/_lib/`.
- Focused regressions and the full regression gate pass.
- Each change is archived through the standard archive flow with no source-repo state leakage.
