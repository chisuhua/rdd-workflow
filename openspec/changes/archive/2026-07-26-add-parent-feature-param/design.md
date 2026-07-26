## Context

`iteration_schema.json` L99-102 defines `parent_feature` as a `["string", "null"]` field. The Python backend (`propose_change.py`) already supports `parent_feature` in all 3 consumer functions:

- `create_skeleton_change()` (L68): accepts `parent_feature: Optional[str]` → writes to `roadmap-meta.yaml` + `iteration.json`
- `update_roadmap_meta()` (L171): accepts `parent_feature: Optional[str]` → writes to `roadmap-meta.yaml`
- `update_iteration_proposed()` (L319): accepts `parent_feature: Optional[str]` → writes to `iteration.json`

The bash wrapper (`propose_change.sh`) already reads `PARENT_FEATURE` env var and passes it through. However, the parameter is only accessible via env var — there is no `--parent-feature` CLI argument, no interactive Phase 3 menu integration, and no tests.

The `__ungrouped__` rejection is already implemented in Python (L92-96, L335-338).

## Goals / Non-Goals

**Goals:**
- Add `--parent-feature <name>` CLI argument to `propose_create_change` and `propose_finalize_change` bash functions
- Add Phase 3 interactive menu: optional "归属 feature" input when user selects a propose
- Add unit tests: 4 cases covering `--parent-feature` flow, rejection, env-var fallback, backward compatibility
- Add bats integration tests: 2 cases covering CLI parsing and iteration.json output

**Non-Goals:**
- Modifying the Python backend (already complete)
- Adding `feature create` command (out of scope per improvement)
- Auto-deriving feature from name prefix (out of scope per improvement)
- Modifying `feature_view.py` or `feature_cli.py` (feature view is pure derived, auto-works)

## Decisions

### Decision 1: Bash-level `--parent-feature` argument parsing in `propose_change.sh`

- **Why**: The bash wrapper is the interface consumed by `propose.md` Phase 4. Adding CLI argument parsing there makes the parameter discoverable and testable, rather than relying on env var documentation.
- **How**: Add optional `--parent-feature <name>` argument to both `propose_create_change` and `propose_finalize_change`. Parse with a simple case statement. When provided, set `PARENT_FEATURE` env var before calling Python.
- **Alternative**: Keep env-var-only approach
- **Rejected**: Env vars are invisible to users and harder to test

### Decision 2: Phase 3 menu integration

- **Why**: The improvement states "交互式菜单: 可选 '归属 feature' 输入". When user selects a propose, the AI should ask "是否需要将此 change 归属到某个 feature 组？(可选，输入 feature 名称或留空)"
- **How**: Add a prompt after user selection, before entering Phase 4. Store result in `PARENT_FEATURE` env var for the Phase 4 loop.
- **Alternative**: Skip interactive and only support CLI
- **Rejected**: Interactive mode is the primary UX for propose skill

### Decision 3: `propose_create_change` positional args remain unchanged

- **Why**: Changing positional argument order would break existing callers. `--parent-feature` is parsed as an optional named argument before positional processing.
- **How**: The function signature stays `propose_create_change <name> --skeleton <phase> <category> <priority>`. `--parent-feature <name>` is parsed before `--skeleton` and sets `PARENT_FEATURE` env var.
- **Alternative**: Add as positional arg `$6`
- **Rejected**: Positional args are less readable and harder to make optional

## API

### `propose_create_change` (bash)

```bash
propose_create_change <name> --skeleton <phase> <category> <priority> [--parent-feature <name>]
```

### `propose_finalize_change` (bash)

```bash
propose_finalize_change <name> <phase> <category> <priority> <valid_categories> [--parent-feature <name>]
```

**Note**: Both functions already accept `PARENT_FEATURE` env var as fallback. CLI `--parent-feature` takes precedence over env var.

## Test Plan

### Unit tests (4 cases, in `tests/unit/test_propose_change.py`)

| Test | Input | Expected |
|------|-------|----------|
| `--parent-feature` in skeleton call | `create_skeleton_change` with `parent_feature="feature-rddf"` | `roadmap-meta.yaml` contains `parent_feature: "feature-rddf"`, `iteration.json` contains `parent_feature` field |
| `__ungrouped__` rejection | `create_skeleton_change` with `parent_feature="__ungrouped__"` | `ValueError` raised with "reserved" in message |
| No parent_feature (backward compatible) | `create_skeleton_change` without `parent_feature` | `roadmap-meta.yaml` has `parent_feature: null` |
| `parent_feature` in finalize call | `update_roadmap_meta` with `parent_feature="feature-stream"` | `roadmap-meta.yaml` contains `parent_feature: "feature-stream"` |

### Integration tests (2 cases, in `tests/integration/test_propose_skill.bats`)

| Test | Input | Expected |
|------|-------|----------|
| CLI `--parent-feature` parsed | `propose_create_change test --skeleton phase1 core P0 --parent-feature feature-rddf` | `PARENT_FEATURE` env var set before Python call |
| Feature summary grouping | iteration.json change with `parent_feature="feature-rddf"` | `feature summary` shows change under `feature-rddf` group |

**Note**: The existing `test_parent_feature_rejected` and `test_parent_feature` tests at lines 168-214 of `test_propose_change.py` already cover the Python backend. The new tests focus on the bash wrapper and interactive integration.