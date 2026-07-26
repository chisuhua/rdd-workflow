## Context

`guide-plan.md` is a state machine with 5 phases:
- Phase -1: Roadmap detection
- Phase 0: Check existing changes
- Phase 1: Scan project docs & code
- Phase 2: Merge, classify, write suggestions
- Phase 3: Interactive user selection (THE BLOCKER)
- Phase 4: Serial create each propose
- Phase 5: Update suggestions + summary

Phase 3 is the only interactive step — it uses `Question` tool to ask user which proposals to create. For AI orchestrators, this step cannot proceed without human intervention.

`propose.md` Phase 4 already has a `--skeleton` mode (creates minimal artifacts via `propose_create_change`). The `propose_change.sh` helper already supports reading from `proposal-suggestions.md` via `read_suggestions()`.

The existing `count_pending_suggestions()` in `skills/_lib/state.sh` can be used to detect whether there are pending items to batch-create.

## Goals / Non-Goals

**Goals:**
- Add `--non-interactive` CLI flag and `SKIP_GUIDE_PLAN_MENU=yes` env var detection to `guide-plan.md`
- In non-interactive mode: skip Phase 3 menu, auto-execute default flow (scan → propose → deps → plan-done)
- Add `--batch-create` to `propose.md`: iterate all pending suggestions, create skeleton changes for each
- Add bats integration tests: 4 cases
- Add unit tests: 2 cases

**Non-Goals:**
- Modifying the interactive Phase 3 menu (backward compatible)
- Modifying guide-ship (out of scope per improvement)
- Adding `--batch-create` with full artifact creation (skeleton-only, consistent with existing `--skeleton` mode)
- Removing or refactoring any existing interactive code paths

## Decisions

### Decision 1: CLI flag + env var dual detection

- **Why**: AI orchestrators set env vars; CLI `--non-interactive` is for direct invocation. Dual detection covers both use cases.
- **How**: At the top of `guide-plan.md`, after Phase -1, check:
  ```bash
  NON_INTERACTIVE=false
  for arg in "$@"; do
    case "$arg" in
      --non-interactive) NON_INTERACTIVE=true ;;
    esac
  done
  [ -n "${SKIP_GUIDE_PLAN_MENU:-}" ] && NON_INTERACTIVE=true
  ```
  When `NON_INTERACTIVE=true`, Phase 3 is replaced with auto-select all pending suggestions.
- **Alternative**: Only env var
- **Rejected**: CLI flag is more discoverable and testable

### Decision 2: Non-interactive mode skips Phase 3, auto-selects all pending

- **Why**: In non-interactive mode, the orchestrator wants "do everything." Auto-selecting all pending suggestions is the correct default.
- **How**: Replace the Phase 3 `Question` tool block with:
  ```bash
  if [ "$NON_INTERACTIVE" = true ]; then
      echo "🔇 Non-interactive mode: 自动选择所有待创建建议"
      SELECTED_NAMES=($(python3 -c "
  import json
  with open('proposal-suggestions.md') as f:
      entries = json.load(f)
  for e in entries:
      if e.get('status') == '待创建':
          print(e['name'])
  "))
  else
      # ... existing interactive menu ...
  fi
  ```
- **Alternative**: Skip propose entirely
- **Rejected**: The orchestrator expects the full plan flow

### Decision 3: `--batch-create` reuses existing `--skeleton` mode

- **Why**: `propose_change.sh` already has `propose_create_change <name> --skeleton <phase> <category> <priority>`. Batch-create just wraps this in a loop over pending suggestions.
- **How**: In `propose.md` Phase 4, when `--batch-create` is passed:
  ```bash
  if [ "$BATCH_CREATE" = true ]; then
      source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/propose_change.sh"
      source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/state.sh"
      entries=$(read_suggestions "$PROJECT_ROOT")
      for entry in $(echo "$entries" | python3 -c "
  import json, sys
  entries = json.load(sys.stdin)
  for e in entries:
      if e.get('status') == '待创建':
          print(f\"{e['name']}|{e.get('phase','default')}|{e.get('category','general')}|{e.get('priority','P2')}\")
  "); do
          IFS='|' read -r name phase category priority <<< "$entry"
          propose_create_change "$name" --skeleton "$phase" "$category" "$priority"
      done
  fi
  ```
- **Alternative**: Full artifact creation (not just skeleton)
- **Rejected**: Skeleton-only is consistent with existing `--skeleton` mode; full artifacts are created during guide-ship plan generation

## API

### guide-plan non-interactive mode

```bash
# Via env var (recommended for AI orchestrators)
SKIP_GUIDE_PLAN_MENU=yes skill_use("guide-plan")

# Via CLI flag
skill_use("guide-plan", "--non-interactive")
```

### propose batch-create

```bash
# Via CLI flag
skill_use("propose", "--batch-create")
```

## Test Plan

### Integration tests (4 cases, in `tests/integration/test_guide_plan.bats`)

| Test | Input | Expected |
|------|-------|----------|
| `SKIP_GUIDE_PLAN_MENU=yes` env var | `SKIP_GUIDE_PLAN_MENU=yes bash -c 'source guide-plan.md ...'` | Phase 3 skipped, auto-select all pending |
| `--non-interactive` CLI flag | `skill_use("guide-plan", "--non-interactive")` | Same as above |
| `--batch-create` | `skill_use("propose", "--batch-create")` | All pending suggestions get skeleton changes |
| No flag (backward compatible) | `skill_use("guide-plan")` | Interactive Phase 3 menu appears (Question tool) |

### Unit tests (2 cases, in `tests/unit/test_propose_change.py`)

| Test | Input | Expected |
|------|-------|----------|
| `--batch-create` iterates pending | `proposal-suggestions.md` with 3 pending, 1 completed | 3 skeleton changes created, remaining 1 unchanged |
| `--batch-create` with empty list | `proposal-suggestions.md` with 0 pending | No changes created, info message printed |