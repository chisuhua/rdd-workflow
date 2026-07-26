## 1. Add `--non-interactive` / `SKIP_GUIDE_PLAN_MENU` detection to guide-plan.md entry (T1)

- [ ] 1.1 **Write failing test**: Create bats test in `tests/integration/test_guide_plan.bats` — set `SKIP_GUIDE_PLAN_MENU=yes`, invoke guide-plan flow, assert Phase 3 is skipped (no Question tool call) and auto-select all pending suggestions
- [ ] 1.2 **Verify fail**: Run `bats tests/integration/test_guide_plan.bats` — confirm the test fails (no detection yet)
- [ ] 1.3 **Implement**: Add dual detection (CLI flag + env var) at the top of `skills/guide-plan/SKILL.md`, after Phase -1:
  ```bash
  NON_INTERACTIVE=false
  for arg in "$@"; do
    case "$arg" in
      --non-interactive) NON_INTERACTIVE=true ;;
    esac
  done
  [ -n "${SKIP_GUIDE_PLAN_MENU:-}" ] && NON_INTERACTIVE=true
  ```
- [ ] 1.4 **Verify pass**: Re-run the bats test — confirm it passes
- [ ] 1.5 **Commit**: `git add skills/guide-plan/SKILL.md tests/integration/test_guide_plan.bats && git commit -m "feat(guide-plan): add non-interactive mode detection"`

## 2. Replace Phase 3 menu with auto-select in non-interactive mode (T2)

- [ ] 2.1 **Write failing test**: Add bats test — invoke guide-plan with `SKIP_GUIDE_PLAN_MENU=yes`, assert that all pending suggestions are selected and Phase 4 is invoked for each
- [ ] 2.2 **Verify fail**: Run the test — confirm it fails (Phase 3 still shows interactive menu)
- [ ] 2.3 **Implement**: Replace the Phase 3 `Question` tool block with a conditional:
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
      # ... existing interactive menu code (unchanged) ...
  fi
  ```
- [ ] 2.4 **Verify pass**: Re-run — confirm it passes
- [ ] 2.5 **Commit**: `git add skills/guide-plan/SKILL.md && git commit -m "feat(guide-plan): skip Phase 3 menu in non-interactive mode"`

## 3. Add `--batch-create` CLI flag to propose.md Phase 4 (T3)

- [ ] 3.1 **Write failing test**: Add bats test in `tests/integration/test_propose_skill.bats` — invoke `propose.md` with `--batch-create`, assert all pending suggestions in `proposal-suggestions.md` get skeleton changes created
- [ ] 3.2 **Verify fail**: Run `bats tests/integration/test_propose_skill.bats` — confirm test fails (no batch-create yet)
- [ ] 3.3 **Implement**: Add `--batch-create` CLI flag parsing at the top of `propose.md` Phase 4:
  ```bash
  BATCH_CREATE=false
  for arg in "$@"; do
    case "$arg" in
      --batch-create) BATCH_CREATE=true ;;
    esac
  done
  ```
  When `BATCH_CREATE=true`, iterate all pending suggestions from `proposal-suggestions.md` and call `propose_create_change <name> --skeleton <phase> <category> <priority>` for each.
- [ ] 3.4 **Verify pass**: Re-run — confirm it passes
- [ ] 3.5 **Commit**: `git add skills/propose/SKILL.md tests/integration/test_propose_skill.bats && git commit -m "feat(propose): add --batch-create mode"`

## 4. Add unit test: `--batch-create` iterates pending suggestions (T4)

- [ ] 4.1 **Write failing test**: Add to `tests/unit/test_propose_change.py` — create a temp `proposal-suggestions.md` with 3 pending + 1 completed entry, call `batch_create_pending()`, assert 3 skeleton changes created, assert the completed entry is unchanged
- [ ] 4.2 **Verify fail**: Run `python3 -m pytest tests/unit/test_propose_change.py::test_batch_create_pending -xvs` — confirm it fails
- [ ] 4.3 **Implement**: Add `batch_create_pending()` function in `skills/propose/scripts/propose_change.py`:
  ```python
  def batch_create_pending(project_root: str) -> int:
      """Create skeleton changes for all pending suggestions. Returns count."""
      suggestions_path = os.path.join(project_root, "proposal-suggestions.md")
      with open(suggestions_path) as f:
          entries = json.load(f)
      count = 0
      for entry in entries:
          if entry.get("status") == "待创建":
              create_skeleton_change(
                  name=entry["name"],
                  phase=entry.get("phase", "default"),
                  category=entry.get("category", "general"),
                  priority=entry.get("priority", "P2"),
              )
              count += 1
      return count
  ```
- [ ] 4.4 **Verify pass**: Run — confirm it passes
- [ ] 4.5 **Commit**: `git add skills/propose/scripts/propose_change.py tests/unit/test_propose_change.py && git commit -m "feat(propose): add batch_create_pending() function"`

## 5. Add unit test: `--batch-create` with empty list (T5)

- [ ] 5.1 **Write failing test**: Add to `tests/unit/test_propose_change.py` — create a temp `proposal-suggestions.md` with 0 pending entries, call `batch_create_pending()`, assert returns 0 and no changes created
- [ ] 5.2 **Verify fail**: Run the test — confirm it fails
- [ ] 5.3 **N/A** (if `batch_create_pending()` already handles empty list correctly, test should pass — confirm)
- [ ] 5.4 **Verify pass**: Run — confirm it passes
- [ ] 5.5 **Commit**: `git add tests/unit/test_propose_change.py && git commit -m "test: add batch_create_pending empty list test"`

## 6. Add integration test: backward compatibility (T6)

- [ ] 6.1 **Write failing test**: Add bats test — invoke `guide-plan` without any flags/env vars, assert Phase 3 interactive menu is displayed (Question tool called)
- [ ] 6.2 **Verify fail**: Run the test — confirm it fails (or passes if no regression)
- [ ] 6.3 **N/A** (existing interactive code is unchanged — test should pass immediately)
- [ ] 6.4 **Verify pass**: Run — confirm it passes
- [ ] 6.5 **Commit**: `git add tests/integration/test_guide_plan.bats && git commit -m "test: add backward compatibility integration test"`