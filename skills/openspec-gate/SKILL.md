---
name: openspec-gate
description: Use when staged source files may not be linked to an active OpenSpec change and you need to warn or block the commit.
license: MIT
compatibility: Requires rdd-workflow v3+ and git 2.25+
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "new skill for add-openspec-gate change"
  user-invocable: true
---

# OpenSpec Gate

## Overview

`openspec-gate` is a pre-commit guard that detects staged source files which are not linked to any active OpenSpec change. It prevents backfill-style commits by forcing every code change to be associated with a change artifact.

## When to Use

- Before committing source code in `include/`, `src/`, `plugins/`, or `drivers/`
- When you want to enforce that every code change belongs to an `openspec/changes/<name>` directory
- In pre-commit hooks or CI gates

Do not use for documentation-only changes, files under `openspec/`, or paths outside the default gate scopes.

## Usage

```bash
skill_use("openspec-gate")
# or run the script directly
bash skills/openspec-gate/scripts/openspec-gate.sh
```

Default behavior is `warn` (exit 0, print warning). Set `OPENSPEC_GATE_MODE=block` to exit 1 and block the commit.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENSPEC_GATE_MODE` | `warn` | `warn` or `block` |
| `OPENSPEC_GATE_PATHS` | `include/ src/ plugins/ drivers/` | Space-separated path prefixes to check |
| `OPENSPEC_GATE_EXTENSIONS` | `.cpp .h .hpp .c .py .ts` | Space-separated file extensions to check |

## How It Works

1. Lists staged files (`git diff --cached --name-only`).
2. Skips anything under `openspec/`.
3. Filters to configured paths and extensions.
4. Checks whether the remaining file paths contain an active change name (`openspec/changes/<name>` basename).
5. Reports any unlinked files; exits 1 only when `OPENSPEC_GATE_MODE=block`.

## Common Mistakes

- **Expecting blocking by default**: the default mode is `warn`. Set `OPENSPEC_GATE_MODE=block` for CI hard gates.
- **Forgetting to create the change first**: run `skill_use("guide-plan")` or `propose` before committing code.
- **Active change name does not match path**: the gate links by change name substring, so organize files under a directory matching the change name.
