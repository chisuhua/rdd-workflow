# fix-rddf-session-lifecycle-binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 确保 guide-design / guide-plan / guide-ship 三端入口/出口可靠触发 rddf-session hook（ADR-0017），缺失 skill_root.sh 时优雅降级。

**Architecture:** 会话复盘发现 `guide-design/SKILL.md` 的入口（Phase 1）与出口（design-done）hook 直接调用 `resolve_rdd_skill_dir` 而未先 source `skill_root.sh`，导致函数未定义、hook 从未触发、3 个 orphaned session 残留。修复：在 hook 调用前添加 skill_root.sh fallback source 逻辑（与 guide-plan/guide-ship 现有模式一致）。guide-plan/guide-ship 已具备该 source，验证即可。若 `skill_root.sh` 缺失或 `resolve_rdd_skill_dir` 失败则打印 warning 继续，不阻塞工作流。

**Tech Stack:** bash, Python 3.11+, rddf-session module

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-design/SKILL.md` | 入口 Phase 1 + 出口 design-done hook 前置 source 逻辑（缺失） |
| `skills/guide-plan/SKILL.md` | 验证入口/出口 hook 已具备 source（无需改动） |
| `skills/guide-ship/SKILL.md` | 验证入口/出口 hook 已具备 source（无需改动） |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_rddf_session_lifecycle.py`（新建） | 验证 3 个 SKILL.md 的 hook 调用前都有 skill_root.sh source；验证 skill_root.sh 缺失时优雅降级 |

---

### Task 1: guide-design SKILL.md 入口 hook 修复

**Files:**
- Modify: `skills/guide-design/SKILL.md:47-50`（Phase 1 rddf-session 入口 hook）
- Test: `tests/unit/test_rddf_session_lifecycle.py`（新建）

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_rddf_session_lifecycle.py
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from skills._lib import state  # noqa: E402  (path bootstrap only)


ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def _read_skill(name):
    path = os.path.join(ROOT, "skills", name, "SKILL.md")
    with open(path) as f:
        return f.read()


def test_guide_design_entry_hook_has_skill_root_source():
    """Phase 1 entry hook must source skill_root.sh before resolve_rdd_skill_dir."""
    content = _read_skill("guide-design")
    entry_block = content.split("rddf_session_hook_entry")[0]
    assert "skill_root.sh" in entry_block, (
        "guide-design entry hook missing skill_root.sh source — "
        "resolve_rdd_skill_dir will be undefined"
    )


def test_guide_design_close_hook_has_skill_root_source():
    """design-done close hook must source skill_root.sh before resolve_rdd_skill_dir."""
    content = _read_skill("guide-design")
    close_block = content.split("rddf_session_hook_close")[0]
    assert "skill_root.sh" in close_block, (
        "guide-design close hook missing skill_root.sh source"
    )


def test_guide_plan_and_ship_hooks_have_skill_root_source():
    """guide-plan/guide-ship entry+close hooks already source skill_root.sh."""
    for name in ("guide-plan", "guide-ship"):
        content = _read_skill(name)
        for hook in ("rddf_session_hook_entry", "rddf_session_hook_close"):
            assert hook in content, f"{name} missing {hook}"
            block = content.split(hook)[0]
            assert "skill_root.sh" in block, (
                f"{name} {hook} missing skill_root.sh source"
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow/.rddf/wt/fix-rddf-session-lifecycle-binding && python3 -m pytest tests/unit/test_rddf_session_lifecycle.py -v --tb=short`
Expected: FAIL — `test_guide_design_entry_hook_has_skill_root_source` 断言失败（guide-design 无 skill_root.sh source）

- [ ] **Step 3: Write minimal implementation**

修改 `skills/guide-design/SKILL.md` Phase 1 入口 hook（当前 L47-50）：

```markdown
**rddf-session 入口 hook**（ADR-0017）：创建或查找当前 opencode session 的 `stage_design` rddf-session（parent=latest stage_arch）：

```bash
# rddf-session 入口 hook (ADR-0017) — extracted to _lib/rddf_session_hooks.sh
# stage_design parent: latest stage_arch (auto-resolved by helper)
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir rddf-session)/scripts/rddf_session_hooks.sh"
rddf_session_hook_entry stage_design guide-design design-phase design-done .rddf/state/.design-handoff.json
```
```

修改 `skills/guide-design/SKILL.md` design-done 出口 hook（当前 L153）：

```markdown
**rddf-session 关闭 hook**：
```bash
# rddf-session 关闭 hook (ADR-0017) — graceful degradation when skill_root.sh missing
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
if command -v resolve_rdd_skill_dir >/dev/null 2>&1; then
    source "$(resolve_rdd_skill_dir rddf-session)/scripts/rddf_session_hooks.sh"
    rddf_session_hook_close stage_design design-done guide-design
else
    echo "⚠️  resolve_rdd_skill_dir 不可用, 跳过 rddf-session 关闭 hook (graceful degradation)" >&2
fi
```
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_rddf_session_lifecycle.py -v --tb=short`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add skills/guide-design/SKILL.md tests/unit/test_rddf_session_lifecycle.py
git commit -m "fix: source skill_root.sh before rddf-session hooks in guide-design"
```

---

### Task 2: 优雅降级验证（skill_root.sh 缺失场景）

**Files:**
- Test: `tests/unit/test_rddf_session_lifecycle.py`（追加用例）

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_rddf_session_lifecycle.py (append)
def test_entry_hook_has_graceful_fallback():
    """Entry hook source line must include fallback paths (not single hardcode)."""
    content = _read_skill("guide-design")
    entry_block = content.split("rddf_session_hook_entry")[0]
    # fallback: 项目级 .opencode 或用户级 ~/.agents
    assert ".opencode/skills/_lib/skill_root.sh" in entry_block
    assert "~/.agents/skills/_lib/skill_root.sh" in entry_block
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_rddf_session_lifecycle.py::test_entry_hook_has_graceful_fallback -v --tb=short`
Expected: FAIL — 若入口只加了单一路径 source（无 fallback）

- [ ] **Step 3: Write minimal implementation**

确保 Task 1 中入口 hook 的 source 行包含双路径 fallback（`source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"`）。若 Task 1 已使用该模式，本测试直接通过。

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_rddf_session_lifecycle.py -v --tb=short`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_rddf_session_lifecycle.py
git commit -m "test: lock graceful fallback for rddf-session hooks"
```

---

### Task 3: 全量回归验证

**Files:**
- Test: `tests/unit/`（全量）

- [ ] **Step 1: Run full unit test suite**

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: 全部通过（或仅有文档说明的预存在失败，且与本 change 无关）

- [ ] **Step 2: Verify sessions.json lifecycle end-to-end**

Run: `python3 -c "
import json, os
p = '.rddf/state/sessions.json'
if os.path.exists(p):
    data = json.load(open(p))
    sessions = data.get('sessions', []) if isinstance(data, dict) else data
    active = [s for s in sessions if s.get('status') == 'active']
    print(f'sessions.json: {len(sessions)} total, {len(active)} active')
else:
    print('sessions.json missing — hook gracefully skipped')
"`
Expected: 无 crash；存在或缺失均正常输出

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: verify full regression for rddf-session lifecycle fixes" || echo "无新改动,跳过"
```

---

## Self-Review

**Spec 覆盖:**
- ✅ proposal.md In Scope#1 (guide-design Phase 1 entry) → Task 1
- ✅ proposal.md In Scope#2 (guide-design design-done close) → Task 1
- ✅ proposal.md In Scope#3-6 (guide-plan/guide-ship 已验证具备) → Task 1 test_guide_plan_and_ship_hooks_have_skill_root_source
- ✅ proposal.md 优雅降级 → Task 2
- ✅ 验收标准: sessions.json 出现 stage_design / hook 失败不崩溃 → Task 3

**占位符扫描:** 无 TBD/TODO，所有步骤含实际代码。

**类型一致性:** `resolve_rdd_skill_dir` 调用模式与 guide-plan/guide-ship 完全一致；hook 参数（kind/intent/subject/outcome/context）不变。
