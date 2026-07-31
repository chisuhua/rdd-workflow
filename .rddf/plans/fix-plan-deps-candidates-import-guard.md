# fix-plan-deps-candidates-import-guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `plan_deps_candidates_env.py` 动态导入无 None-guard 崩溃，以及 `plan_done_gate.py` 执行模式决策不过滤已归档 change 的缺陷。

**Architecture:** 两处防御性修复：(1) 在 `spec_from_file_location()` 返回后立即检查 `None`，抛出带目标路径的 `ImportError`；(2) `_load_execution_mode_decisions()` 读取 `deps-analysis.json` 后，以 `openspec/changes/` 活跃目录（非 archive）为白名单过滤 change 名。均不改变正常路径行为。

**Tech Stack:** Python 3.11+, pytest, openspec CLI

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-plan/scripts/plan_deps_candidates_env.py` | 动态加载 plan_deps_candidates 模块的入口脚本，添加 None-guard |
| `skills/guide-plan/scripts/plan_done_gate.py` | plan-done handoff 写入，过滤已归档 change 的执行模式决策 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_plan_deps_candidates_env.py` | 覆盖 spec_from_file_location 返回 None 的 guard 逻辑 |
| `tests/unit/test_plan_done_gate.py` | 覆盖 execution_mode_decisions 过滤已归档 change |

---

### Task 1: plan_deps_candidates_env.py None-guard

**Files:**
- Modify: `skills/guide-plan/scripts/plan_deps_candidates_env.py:18-24`
- Test: `tests/unit/test_plan_deps_candidates_env.py`（新建）

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_plan_deps_candidates_env.py
import importlib.util
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from skills.guide_plan.scripts import plan_deps_candidates_env  # noqa: E402


def test_spec_none_raises_import_error(monkeypatch, tmp_path):
    """When spec_from_file_location returns None, raise ImportError with target path."""
    calls = {}

    def fake_spec_from_file_location(name, path):
        calls["path"] = path
        return None  # simulate load failure

    monkeypatch.setattr(
        importlib.util, "spec_from_file_location", fake_spec_from_file_location
    )
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    with pytest.raises(ImportError) as excinfo:
        plan_deps_candidates_env.main()

    assert "plan_deps_candidates" in str(excinfo.value)
    assert "skills" in str(excinfo.value)  # includes target path


def test_spec_ok_executes_generate(monkeypatch, tmp_path):
    """When spec loads successfully, generate_deps_candidates is invoked."""
    called = {}

    class FakeLoader:
        def exec_module(self, mod):
            mod.generate_deps_candidates = lambda root: called.update(root=root)

    class FakeSpec:
        loader = FakeLoader()

    def fake_spec_from_file_location(name, path):
        return FakeSpec()

    monkeypatch.setattr(
        importlib.util, "spec_from_file_location", fake_spec_from_file_location
    )
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    plan_deps_candidates_env.main()

    assert called.get("root") == str(tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow/.rddf/wt/fix-plan-deps-candidates-import-guard && python3 -m pytest tests/unit/test_plan_deps_candidates_env.py -v --tb=short`
Expected: FAIL — `AttributeError: 'NoneType' object has no attribute 'loader'` (当前无 guard)

- [ ] **Step 3: Write minimal implementation**

```python
# skills/guide-plan/scripts/plan_deps_candidates_env.py
import importlib.util
import os
import sys


def _load_plan_deps_candidates(project_root):
    """Load plan_deps_candidates module via spec, raising ImportError on failure."""
    target = os.path.join(project_root, "skills", "guide-plan", "scripts", "plan_deps_candidates.py")
    spec = importlib.util.spec_from_file_location("plan_deps_candidates", target)
    if spec is None:
        raise ImportError(
            "Cannot load plan_deps_candidates from {}: spec_from_file_location returned None (file missing or unsupported)".format(target)
        )
    pdc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pdc)
    return pdc


def main():
    project_root = os.environ.get("PROJECT_ROOT")
    if not project_root:
        print("ERROR: PROJECT_ROOT env var not set", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, project_root)
    pdc = _load_plan_deps_candidates(project_root)
    pdc.generate_deps_candidates(project_root)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_plan_deps_candidates_env.py -v --tb=short`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add skills/guide-plan/scripts/plan_deps_candidates_env.py tests/unit/test_plan_deps_candidates_env.py
git commit -m "fix: add None-guard to plan_deps_candidates_env dynamic import"
```

---

### Task 2: plan_done_gate.py 过滤已归档 change

**Files:**
- Modify: `skills/guide-plan/scripts/plan_done_gate.py:63-77`
- Test: `tests/unit/test_plan_done_gate.py`（新建）

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_plan_done_gate.py
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from skills.guide_plan.scripts import plan_done_gate  # noqa: E402


def _write_deps_analysis(project_root, recommendations):
    state_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, "deps-analysis.json"), "w") as f:
        json.dump({"execution_mode_recommendations": recommendations}, f)


def test_filters_archived_changes(tmp_path):
    """Only active (non-archive) changes remain in execution_mode_decisions."""
    # Active change dir + archived change dir
    (tmp_path / "openspec" / "changes" / "fix-active").mkdir(parents=True)
    (tmp_path / "openspec" / "changes" / "archive" / "2026-07-31-old-archived").mkdir(parents=True)

    _write_deps_analysis(tmp_path, {
        "fix-active": {"mode": "lightweight", "reason": "ok"},
        "old-archived": {"mode": "worktree", "reason": "stale"},
    })

    decisions = plan_done_gate._load_execution_mode_decisions(str(tmp_path))

    assert "fix-active" in decisions
    assert "old-archived" not in decisions


def test_missing_deps_file_returns_empty(tmp_path):
    """Missing deps-analysis.json yields empty dict (unchanged behavior)."""
    assert plan_done_gate._load_execution_mode_decisions(str(tmp_path)) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_plan_done_gate.py -v --tb=short`
Expected: FAIL — `old-archived` 仍在 decisions 中（当前不过滤）

- [ ] **Step 3: Write minimal implementation**

```python
# skills/guide-plan/scripts/plan_done_gate.py (replace _load_execution_mode_decisions)

def _load_execution_mode_decisions(project_root: str) -> dict:
    """Load execution_mode_recommendations from deps-analysis.json.

    Only keeps entries whose change has an active (non-archive) directory
    under openspec/changes/, filtering stale decisions for archived changes.

    Returns empty dict if deps-analysis.json missing or malformed.
    """
    deps_path = os.path.join(project_root, ".rddf", "state", "deps-analysis.json")
    if not os.path.isfile(deps_path):
        return {}

    try:
        with open(deps_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    recommendations = data.get("execution_mode_recommendations", {})
    if not recommendations:
        return {}

    active_dir = os.path.join(project_root, "openspec", "changes")
    active_names = set()
    if os.path.isdir(active_dir):
        for entry in os.listdir(active_dir):
            entry_path = os.path.join(active_dir, entry)
            if os.path.isdir(entry_path) and entry != "archive":
                active_names.add(entry)

    return {
        name: rec
        for name, rec in recommendations.items()
        if name in active_names
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_plan_done_gate.py -v --tb=short`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add skills/guide-plan/scripts/plan_done_gate.py tests/unit/test_plan_done_gate.py
git commit -m "fix: filter archived changes in execution_mode_decisions"
```

---

### Task 3: 全量回归验证

**Files:**
- Test: `tests/unit/`（全量）

- [ ] **Step 1: Run full unit test suite**

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: 全部通过（或仅有文档说明的预存在失败，且与本 change 无关）

- [ ] **Step 2: Verify no pre-existing failure introduced**

Run: `git stash && python3 -m pytest tests/unit/ -q --tb=short && git stash pop`
Expected: 与修改前基线一致，无新增失败

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: verify full regression for import-guard fixes" || echo "无新改动,跳过"
```

---

## Self-Review

**Spec 覆盖:**
- ✅ proposal.md Why#1 (None-guard) → Task 1
- ✅ proposal.md Why#2 (execution_mode_decisions 过滤) → Task 2
- ✅ tasks.md 1.1/1.2 → Task 1; 2.1/2.2 → Task 2; 3.1/3.2/3.3 → Task 3
- ✅ 验收标准: env.py 打印错误退出 1 → Task 1; handoff 只含活跃 change → Task 2; pytest 全通过 → Task 3

**占位符扫描:** 无 TBD/TODO/占位内容，所有步骤含实际代码。

**类型一致性:** `_load_plan_deps_candidates(project_root)` 在 main 中调用一致；`_load_execution_mode_decisions(project_root)` 签名不变，handoff 构建处调用不变。
