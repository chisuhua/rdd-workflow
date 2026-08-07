# Design: ship archive shared-library resolution

## Context

The archive helper is usable from both the source repository and external projects. Its lightweight pre-flight currently assumes `_lib/validate_delta_targets.py` is under the current project root. That assumption is invalid for global installs.

## Decision

Keep the existing bootstrap at archive-helper entry, then resolve the shared library once at the validation call site:

```bash
local rdd_lib_dir
rdd_lib_dir="$(resolve_rdd_lib_dir)" || {
  echo "❌ Cannot resolve rdd-workflow _lib directory" >&2
  return 1
}
python3 "$rdd_lib_dir/validate_delta_targets.py" "$change_name"
```

Use the resolved path for both the quiet pre-flight invocation and the diagnostic retry. Do not create a project-local symlink and do not weaken validation.

## Verification

Use an isolated external project with a valid active change, no local `_lib`, and the global shared library available. Assert the archive pre-flight invokes the global validator. Add a missing-resolver case that returns non-zero.

## Risks and Mitigations

- **Risk**: Resolver is unavailable in malformed installations. **Mitigation**: explicit fail-closed diagnostic.
- **Risk**: One invocation still uses the old path. **Mitigation**: structural grep plus both pre-flight and diagnostic-path assertions.
