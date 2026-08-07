# fix-bootstrap-fallback-paths

## Why

External projects using the global rdd-workflow install fail in phase helpers because the fallback path points to `$HOME/.agents/_lib/skill_root.sh`, while the installed shared library is at `$HOME/.agents/skills/_lib/skill_root.sh`.

## What Changes

- Correct the fallback literal in all runtime shell scripts and documented SKILL.md examples discovered by the repository scan.
- Preserve local-project-first resolution, global fallback ordering, function signatures, and state semantics.
- Add regression coverage proving an external project without local `_lib` resolves the global skill root without a fallback-path error.

## Capabilities

### New Capabilities

- Reliable global bootstrap fallback for external projects.

### Modified Capabilities

- Phase helper entry points use the actual global-install layout.

## Impact

- Runtime scripts under `skills/` and their documented bootstrap examples.
- No changes to global installation layout or resolver precedence.

## Acceptance

- No supported runtime/documentation surface contains `$HOME/.agents/_lib/skill_root.sh`.
- External-project bootstrap regression passes.
- Existing focused and full regression tests pass.
