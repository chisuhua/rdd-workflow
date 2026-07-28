# guide-plan-noninteractive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 为 guide-plan 添加 `--non-interactive` 模式（CLI flag + env var 双检测）和 propose 的 `--batch-create` 批量创建能力，让 AI 编排器可自动执行完整 plan 流程。

**Architecture:** 在 guide-plan.md 入口添加 Phase 3 菜单跳闸逻辑（非交互模式自动选中所有待创建建议），在 propose.md Phase 4 添加 `--batch-create` 循环骨架创建，在 propose_change.py 添加 `batch_create_pending()` 函数。所有变更均为可选的 additive 路径，100% 向后兼容。

**Tech Stack:** bash (SKILL.md), Python 3.11+ (propose_change.py), bats (integration tests), pytest (unit tests)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-plan/SKILL.md` | 入口添加 `--non-interactive`/`SKIP_GUIDE_PLAN_MENU` 检测；Phase 3 菜单替换为 auto-select 逻辑 |
| `skills/propose/SKILL.md` | Phase 4 添加 `--batch-create` 标志解析和循环创建逻辑 |
| `skills/propose/scripts/propose_change.py` | 新增 `batch_create_pending()` 函数 |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_guide_plan.bats` | 新增 3 个集成测试用例：env var 模式、CLI flag 模式、向后兼容性 |
| `tests/integration/test_propose_skill.bats` | 新增 1 个集成测试用例：`--batch-create` 批量创建 |
| `tests/unit/test_propose_change.py` | 新增 2 个单元测试：`batch_create_pending` 迭代 pending、空列表处理 |

---

### Task 1: Add `--non-interactive` / `SKIP_GUIDE_PLAN_MENU` detection to guide-plan.md entry

**Files:**
- Modify: `skills/guide-plan/SKILL.md` (after Phase -1, before Phase 1 entry)
- Create: `tests/integration/test_guide_plan.bats`

- [x] **Step 1: Write the failing test**

Create `tests/integration/test_guide_plan.bats`:

```bash
#!/usr/bin/env bats
# tests/integration/test_guide_plan.bats
#
# Tests for guide-plan non-interactive mode (--non-interactive, SKIP_GUIDE_PLAN_MENU).
# Run: bats tests/integration/test_guide_plan.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "guide_plan_noninteractive: SKIP_GUIDE_PLAN_MENU=yes bypasses Phase 3 interactive menu" {
  # Verify that when SKIP_GUIDE_PLAN_MENU=yes is set, the NON_INTERACTIVE variable
  # is set to true (detected by grep for the env var detection pattern)
  grep -q 'SKIP_GUIDE_PLAN_MENU' "$f"
}

@test "guide_plan_noninteractive: --non-interactive CLI flag is detected" {
  # Verify that --non-interactive is listed in the arg parsing loop
  grep -q '\-\-non-interactive' "$f"
}

@test "guide_plan_noninteractive: non-interactive mode skips Question tool (Phase 3 menu)" {
  # Verify there is a conditional branch that skips interactive code when NON_INTERACTIVE=true
  grep -q 'NON_INTERACTIVE.*true.*auto.*select.*all.*pending' "$f" || \
  grep -q 'SKIP_GUIDE_PLAN_MENU.*yes.*auto.*select' "$f" || \
  grep -q 'NON_INTERACTIVE.*true.*echo.*Non-interactive' "$f"
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_guide_plan.bats`
Expected: FAIL with "SKIP_GUIDE_PLAN_MENU not found" or similar

- [x] **Step 3: Write minimal implementation**

At the top of `skills/guide-plan/SKILL.md`, after the frontmatter and before `## Architecture:` section, add the detection block:

```bash
# --- Non-interactive mode detection ---
# Supports both CLI flag (--non-interactive) and env var (SKIP_GUIDE_PLAN_MENU=yes).
# When active, Phase 3 interactive menu is skipped and all pending suggestions are auto-selected.
NON_INTERACTIVE=false
for arg in "$@"; do
  case "$arg" in
    --non-interactive) NON_INTERACTIVE=true ;;
  esac
done
[ -n "${SKIP_GUIDE_PLAN_MENU:-}" ] && NON_INTERACTIVE=true
```

Add this right after the `---` closing frontmatter delimiter (line 11), before line 12 `# OpenSpec 工作流 — Plan-Side Guide`.

- [x] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_guide_plan.bats`
Expected: PASS (all 3 tests)

- [x] **Step 5: Commit**

```bash
git add skills/guide-plan/SKILL.md tests/integration/test_guide_plan.bats
git commit -m "feat(guide-plan): add non-interactive mode detection (--non-interactive flag + SKIP_GUIDE_PLAN_MENU env var)"
```

---

### Task 2: Replace Phase 3 menu with auto-select in non-interactive mode

**Files:**
- Modify: `skills/guide-plan/SKILL.md` (Phase 3 / Phase 2 menu area, around line 242-280)

- [x] **Step 1: Write the failing test**

Append to `tests/integration/test_guide_plan.bats`:

```bash
@test "guide_plan_noninteractive: auto-selects all pending suggestions in non-interactive mode" {
  # Verify the Phase 2/3 menu has a conditional that auto-selects when NON_INTERACTIVE=true
  grep -q 'if.*\[.*\"\$NON_INTERACTIVE\".*=.*true' "$f" || \
  grep -q 'if.*\[.*NON_INTERACTIVE.*=.*true' "$f"
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_guide_plan.bats`
Expected: The new test fails (no conditional yet around Phase 2 menu)

- [x] **Step 3: Write minimal implementation**

In `skills/guide-plan/SKILL.md`, find the Phase 2 menu section (around line 242-280). Replace the menu display with a conditional:

Find the code block that starts with the menu display (around line 242: `请选择操作:`). The menu is embedded in a bash code block. Before the "创建 change" handler, add a guard:

```bash
# --- Non-interactive mode: skip menu, auto-select all pending ---
if [ "$NON_INTERACTIVE" = true ]; then
    echo "🔇 Non-interactive mode: 自动选择所有待创建建议"
    # Auto-select: iterate proposal-approved.md and create all pending changes
    SELECTED_NAMES=($(python3 -c "
import re, sys
try:
    with open('proposal-approved.md') as f:
        content = f.read()
    section = re.split(r'## 已实施', content)[0]
    rows = re.findall(r'\[\s*([^\]]+)\]\s*\(improvements/([^)]+)\)', section)
    for name, _ in rows:
        print(name)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
"))
    for name in "${SELECTED_NAMES[@]}"; do
        echo "  → 创建 change: $name"
        skill_use("propose", "--create", "$name")
    done
    # After all auto-creations, skip to deps phase
    choice="6"  # "完成变更生成"
else
    # ... existing interactive menu code (unchanged) ...
fi
```

The key is wrapping the interactive menu display and user input reading inside the `else` branch. The exact insertion point depends on the file structure. Let me be precise:

The menu display (lines 222-250) is followed by a `case` handler (lines 252-280). The `read -r target_name` at line 258 and subsequent `if` at line 261 are the interactive part. The approach is:

1. Before the Phase 2 menu display (line 220), add the non-interactive guard
2. In non-interactive mode, parse `proposal-approved.md`, get all names, call `skill_use("propose", "--create", "$name")` for each, then set `choice=6` to proceed to deps
3. In interactive mode, show the existing menu unchanged

- [x] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_guide_plan.bats`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add skills/guide-plan/SKILL.md
git commit -m "feat(guide-plan): skip Phase 3 interactive menu in non-interactive mode, auto-select all pending suggestions"
```

---

### Task 3: Add `--batch-create` CLI flag to propose.md Phase 4

**Files:**
- Modify: `skills/propose/SKILL.md` (Phase 4, around line 420-430)
- Modify: `tests/integration/test_propose_skill.bats`

- [x] **Step 1: Write the failing test**

Append to `tests/integration/test_propose_skill.bats`:

```bash
@test "propose_skill: --batch-create flag is parsed in Phase 4" {
  grep -q '\-\-batch-create' "$f"
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_propose_skill.bats`
Expected: The new test fails (no --batch-create in propose.md)

- [x] **Step 3: Write minimal implementation**

In `skills/propose/SKILL.md`, in the Phase 4 section (around line 420-430), the existing arg parsing loop is:

```bash
for arg in "$@"; do
  case "$arg" in
    --skeleton|--skeleton-only) SKELETON_MODE=true ;;
  esac
done
```

Add `--batch-create` detection:

```bash
for arg in "$@"; do
  case "$arg" in
    --skeleton|--skeleton-only) SKELETON_MODE=true ;;
    --batch-create) BATCH_CREATE=true ;;
  esac
done
BATCH_CREATE="${BATCH_CREATE:-false}"
```

Then, after the existing `SKELETON_MODE` block (after line 473 `continue`), add the batch-create branch:

```bash
# Step 4a-batch: Batch-create mode — iterate all pending suggestions
if [ "$BATCH_CREATE" = "true" ]; then
    echo "📦 Batch-create mode: 为所有待创建建议创建骨架 change"
    source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/propose_change.sh"
    source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/state.sh"
    entries=$(read_suggestions "$PROJECT_ROOT")
    count=0
    for entry in $(echo "$entries" | python3 -c "
import json, sys
entries = json.load(sys.stdin)
for e in entries:
    if e.get('status') == '待创建':
        print(f\"{e['name']}|{e.get('phase','default')}|{e.get('category','general')}|{e.get('priority','P2')}\")
"); do
        IFS='|' read -r name phase category priority <<< "$entry"
        echo "  → 创建骨架 change: $name"
        propose_create_change "$name" --skeleton "$phase" "$category" "$priority"
        count=$((count + 1))
    done
    echo "✅ Batch-create 完成: 创建了 $count 个骨架 change"
    continue
fi
```

- [x] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_propose_skill.bats`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add skills/propose/SKILL.md tests/integration/test_propose_skill.bats
git commit -m "feat(propose): add --batch-create mode for mass skeleton creation"
```

---

### Task 4: Add `batch_create_pending()` function + unit test

**Files:**
- Modify: `skills/propose/scripts/propose_change.py`
- Modify: `tests/unit/test_propose_change.py`

- [x] **Step 1: Write the failing test**

Add to `tests/unit/test_propose_change.py`:

```python
class TestBatchCreatePending:
    def test_batch_create_pending_iterates_all(self, tmp_path):
        """Create a temp proposal-suggestions.md with 3 pending + 1 completed,
        call batch_create_pending(), assert 3 skeleton changes created."""
        suggestions = [
            {"name": "c1", "status": "待创建", "phase": "phase-1", "category": "general", "priority": "P1"},
            {"name": "c2", "status": "待创建", "phase": "phase-1", "category": "general", "priority": "P2"},
            {"name": "c3", "status": "待创建", "phase": "phase-2", "category": "refactor", "priority": "P1"},
            {"name": "c4", "status": "completed", "phase": "phase-1", "category": "general", "priority": "P2"},
        ]
        (tmp_path / "proposal-suggestions.md").write_text(json.dumps(suggestions, indent=2) + "\n")
        result = pc.batch_create_pending(str(tmp_path))
        assert result == 3
        # Verify skeleton changes were created
        for name in ["c1", "c2", "c3"]:
            proposal = tmp_path / "openspec" / "changes" / name / "proposal.md"
            assert proposal.exists(), f"{name} proposal.md not created"
        # Verify completed entry was not created
        c4_dir = tmp_path / "openspec" / "changes" / "c4"
        assert not c4_dir.exists(), "c4 should not have been created"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestBatchCreatePending::test_batch_create_pending_iterates_all -xvs`
Expected: FAIL with `AttributeError: module has no attribute 'batch_create_pending'`

- [x] **Step 3: Write minimal implementation**

Add to `skills/propose/scripts/propose_change.py` (after the last function, before any trailing newline):

```python
def batch_create_pending(project_root: str) -> int:
    """Create skeleton changes for all pending suggestions in proposal-suggestions.md.
    
    Reads proposal-suggestions.md, filters entries with status='待创建',
    and calls create_skeleton_change() for each. Returns the count of
    successfully created skeleton changes.
    
    Skips entries where create_skeleton_change returns False.
    Uses entry's phase/category/priority fields, with fallback defaults.
    """
    import os
    import json
    
    suggestions_path = os.path.join(project_root, "proposal-suggestions.md")
    if not os.path.exists(suggestions_path):
        return 0
    
    with open(suggestions_path) as f:
        entries = json.load(f)
    
    count = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "待创建":
            continue
        
        ok = create_skeleton_change(
            project_root=project_root,
            name=entry["name"],
            current_phase=entry.get("phase", "default"),
            category=entry.get("category", "general"),
            priority=entry.get("priority", "P2"),
        )
        if ok:
            count += 1
    
    return count
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestBatchCreatePending::test_batch_create_pending_iterates_all -xvs`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add skills/propose/scripts/propose_change.py tests/unit/test_propose_change.py
git commit -m "feat(propose): add batch_create_pending() function"
```

---

### Task 5: Add unit test for `batch_create_pending()` with empty list

**Files:**
- Modify: `tests/unit/test_propose_change.py`

- [x] **Step 1: Write the failing test**

Add to `TestBatchCreatePending` class in `tests/unit/test_propose_change.py`:

```python
    def test_batch_create_pending_empty_list(self, tmp_path):
        """Create a temp proposal-suggestions.md with 0 pending entries,
        call batch_create_pending(), assert returns 0 and no changes created."""
        suggestions = [
            {"name": "c1", "status": "completed", "phase": "phase-1", "category": "general", "priority": "P1"},
            {"name": "c2", "status": "skeleton", "phase": "phase-1", "category": "general", "priority": "P2"},
        ]
        (tmp_path / "proposal-suggestions.md").write_text(json.dumps(suggestions, indent=2) + "\n")
        result = pc.batch_create_pending(str(tmp_path))
        assert result == 0
        # Verify no skeleton directories were created
        for name in ["c1", "c2"]:
            change_dir = tmp_path / "openspec" / "changes" / name
            assert not change_dir.exists(), f"{name} should not have been created"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestBatchCreatePending::test_batch_create_pending_empty_list -xvs`
Expected: If `batch_create_pending()` already handles empty lists correctly, this should pass immediately. If not, it will fail.

- [x] **Step 3: N/A** (if `batch_create_pending()` already handles empty list correctly, test should pass — confirm)

- [x] **Step 4: Verify pass**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestBatchCreatePending::test_batch_create_pending_empty_list -xvs`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add tests/unit/test_propose_change.py
git commit -m "test: add batch_create_pending empty list unit test"
```

---

### Task 6: Add backward compatibility integration test

**Files:**
- Modify: `tests/integration/test_guide_plan.bats`

- [x] **Step 1: Write the failing test**

Append to `tests/integration/test_guide_plan.bats`:

```bash
@test "guide_plan_noninteractive: backward compatible — no flag preserves interactive menu" {
  # Verify that the file still contains the interactive menu code (Question tool, read, etc.)
  grep -q 'Question\|read -r\|请选择操作' "$f"
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_guide_plan.bats`
Expected: This test should pass immediately (interactive menu code is unchanged). If it fails, something is wrong.

- [x] **Step 3: N/A** (existing interactive code is unchanged — test should pass immediately)

- [x] **Step 4: Verify pass**

Run: `bats tests/integration/test_guide_plan.bats`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add tests/integration/test_guide_plan.bats
git commit -m "test: add backward compatibility integration test for guide-plan non-interactive mode"
```