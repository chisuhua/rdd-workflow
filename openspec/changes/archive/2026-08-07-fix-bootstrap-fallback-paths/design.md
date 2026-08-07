# Design: bootstrap fallback paths

## Context

The global installer creates `~/.agents/skills/_lib/skill_root.sh` and exposes the shared resolver from that location. Several extracted helpers and SKILL.md examples still reference the obsolete `~/.agents/_lib/` path. This is especially visible when Bats' ERR trap treats the failed fallback source as a test failure.

## Decision

Perform a literal-only migration of the fallback path:

```bash
$HOME/.agents/_lib/skill_root.sh
```

to:

```bash
$HOME/.agents/skills/_lib/skill_root.sh
```

Apply it consistently to all runtime shell scripts and documentation examples found by the repository scan. Do not alter the preceding project-local fallback or introduce a second resolver implementation.

## Verification

Add focused structural/runtime regression coverage for an isolated external project. The test must assert the corrected literal is present, the obsolete literal is absent from supported surfaces, and the global resolver can be sourced without a project-local `_lib`.

## Risks and Mitigations

- **Risk**: A surface is missed during migration. **Mitigation**: repository-wide scan and structural grep assertion.
- **Risk**: Project-local resolution changes accidentally. **Mitigation**: exact literal replacement only and existing integration suite.
