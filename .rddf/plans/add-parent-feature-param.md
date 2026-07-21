# add-parent-feature-param Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 激活 iteration.json 中已定义但从未被写入的 `parent_feature` 字段，让 change 可显式归入 feature 组而无需 `feature-` 命名前缀。

**Architecture:** 与 ADR-0022 manual_deps 完全对称的 "roadmap-meta.yaml 字段 → iteration.json 同步" 模式。propose_change.py 三个入口函数（create_skeleton_change, update_roadmap_meta, update_iteration_proposed）加可选 `parent_feature` 参数；bash wrapper 通过 `PARENT_FEATURE` env var 传递；保留字 `__ungrouped__` 被拒绝。Schema 零变更（字段已存在 L99-102）。消费端（derive_feature_name, feature_view, ship_archive）已就绪，无需修改。

**Tech Stack:** Python 3.11 (typing.Optional, jsonschema 已有), bash (env-var passing per Oracle C1 安全模式), bats-core (集成测试), pytest (单元测试)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/propose/scripts/propose_change.py` | 3 个函数加 `parent_feature` 参数 + `__ungrouped__` 拒绝 + roadmap-meta.yaml/iteration.json 写入 |
| `skills/propose/scripts/propose_change.sh` | bash wrapper 读取 `PARENT_FEATURE` env var 传给 Python |
| `skills/propose/SKILL.md` | Phase 4 文档加 `PARENT_FEATURE` 设置说明 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_propose_change.py` | 4 个新单元测试（parent_feature 传入 + 拒绝 + grouping） |
| `tests/integration/test_propose_parent_feature.bats` | 2 个新 bats 集成测试（bash wrapper env-var 传递） |

---

### Task 1: create_skeleton_change 加 parent_feature 参数

**Files:**
- Modify: `skills/propose/scripts/propose_change.py:45-129` (create_skeleton_change 函数)
- Test: `tests/unit/test_propose_change.py` (TestCreateSkeletonChange class)

- [ ] **Step 1: Write the failing test**

追加到 `tests/unit/test_propose_change.py` 的 `TestCreateSkeletonChange` 类末尾：

```python
    def test_writes_parent_feature_to_iteration_json(self, tmp_path):
        """parent_feature 参数应写入 iteration.json 的 change 条目。"""
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        pc.create_skeleton_change(
            str(tmp_path), "c1", "phase-1", "general", "P2",
            parent_feature="feature-rddf",
        )
        loaded = it.load(str(tmp_path))
        match = next(c for c in loaded["changes"] if c["name"] == "c1")
        assert match["parent_feature"] == "feature-rddf"

    def test_writes_parent_feature_to_roadmap_meta_yaml(self, tmp_path):
        """parent_feature 参数应写入 roadmap-meta.yaml。"""
        pc.create_skeleton_change(
            str(tmp_path), "c1", "phase-1", "general", "P2",
            parent_feature="feature-rddf",
        )
        yaml_path = tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml"
        content = yaml_path.read_text()
        assert 'parent_feature: "feature-rddf"' in content

    def test_rejects_ungrouped_parent_feature(self, tmp_path):
        """parent_feature='__ungrouped__' 必须被拒绝（保留字）。"""
        with pytest.raises(ValueError, match="__ungrouped__"):
            pc.create_skeleton_change(
                str(tmp_path), "c1", "phase-1", "general", "P2",
                parent_feature="__ungrouped__",
            )
        # 无文件写入
        assert not (tmp_path / "openspec" / "changes" / "c1").exists()

    def test_without_parent_feature_backward_compatible(self, tmp_path):
        """不传 parent_feature 时行为不变（无该字段写入）。"""
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        pc.create_skeleton_change(str(tmp_path), "c1", "phase-1", "general", "P2")
        loaded = it.load(str(tmp_path))
        match = next(c for c in loaded["changes"] if c["name"] == "c1")
        # parent_feature 字段不存在或为 None
        assert match.get("parent_feature") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestCreateSkeletonChange::test_writes_parent_feature_to_iteration_json tests/unit/test_propose_change.py::TestCreateSkeletonChange::test_rejects_ungrouped_parent_feature -v`
Expected: FAIL with "TypeError: create_skeleton_change() got an unexpected keyword argument 'parent_feature'"

- [ ] **Step 3: Write minimal implementation**

修改 `skills/propose/scripts/propose_change.py` 的 `create_skeleton_change` 函数（L45-129）：

1. 签名改为：
```python
def create_skeleton_change(
    project_root: str,
    name: str,
    current_phase: str,
    category: str,
    priority: str,
    parent_feature: Optional[str] = None,
) -> bool:
```

2. 在 docstring 后追加保留字校验（紧跟函数体第一行 `import os` 之前）：
```python
    # Reject reserved synthetic feature name (feature_view.py::UNGROUPED)
    if parent_feature == "__ungrouped__":
        raise ValueError(
            "parent_feature='__ungrouped__' is reserved (synthetic feature key); "
            "use a real feature name or omit parent_feature"
        )
```

3. roadmap-meta.yaml 写入块（L94-105 之间，`manual_blocks: []` 行后）追加：
```python
            f.write(f'  parent_feature: {repr(parent_feature) if parent_feature else "null"}\n')
```
（注：`repr` 用于安全引用字符串；Python None 写为 null。但 YAML 中 `repr(None)` 是 `None` 不是 `null`，需用条件表达式）
实际写入：
```python
            pf_yaml = f'"{parent_feature}"' if parent_feature else "null"
            f.write(f'  parent_feature: {pf_yaml}\n')
```

4. `it_mod.add_or_update_change` 调用（L113-120）改为条件传入：
```python
        kwargs = {
            "name": name,
            "status": "planned",
            "phase": None,
            "category": None,
            "priority": None,
        }
        if parent_feature is not None:
            kwargs["parent_feature"] = parent_feature
        data = it_mod.add_or_update_change(data, **kwargs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestCreateSkeletonChange -v`
Expected: PASS (含 4 个新测试 + 4 个原有测试共 8 个)

- [ ] **Step 5: Commit**

```bash
git add skills/propose/scripts/propose_change.py tests/unit/test_propose_change.py
git commit -m "feat(propose): add parent_feature param to create_skeleton_change

- Optional parent_feature: Optional[str] = None (backward compatible)
- Reject reserved '__ungrouped__' synthetic key with ValueError
- Write parent_feature to both roadmap-meta.yaml and iteration.json
- 4 new unit tests covering write path, rejection, backward compat"
```

---

### Task 2: update_roadmap_meta 加 parent_feature 参数

**Files:**
- Modify: `skills/propose/scripts/propose_change.py:131-205` (update_roadmap_meta 函数)
- Test: `tests/unit/test_propose_change.py` (TestUpdateRoadmapMeta class)

- [ ] **Step 1: Write the failing test**

追加到 `tests/unit/test_propose_change.py` 的 `TestUpdateRoadmapMeta` 类末尾：

```python
    def test_writes_parent_feature_to_yaml(self, tmp_path):
        """parent_feature 参数应写入 roadmap-meta.yaml。"""
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        result = pc.update_roadmap_meta(
            str(tmp_path), "c1",
            current_phase="phase-1",
            change_category="core-impl",
            priority="P2",
            valid_categories="core-impl:Core",
            parent_feature="feature-stream",
        )
        assert result is True
        yaml_path = tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml"
        content = yaml_path.read_text()
        assert 'parent_feature: "feature-stream"' in content

    def test_parent_feature_null_when_not_provided(self, tmp_path):
        """不传 parent_feature 时 yaml 写入 null。"""
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        pc.update_roadmap_meta(
            str(tmp_path), "c1",
            current_phase="phase-1",
            change_category="core-impl",
            priority="P2",
            valid_categories="core-impl:Core",
        )
        yaml_path = tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml"
        content = yaml_path.read_text()
        assert "parent_feature: null" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestUpdateRoadmapMeta::test_writes_parent_feature_to_yaml -v`
Expected: FAIL with "TypeError: update_roadmap_meta() got an unexpected keyword argument 'parent_feature'"

- [ ] **Step 3: Write minimal implementation**

修改 `skills/propose/scripts/propose_change.py` 的 `update_roadmap_meta` 函数（L131-205）：

1. 签名加参数：
```python
def update_roadmap_meta(
    project_root: str,
    name: str,
    current_phase: str,
    change_category: str,
    priority: str,
    valid_categories: str,
    parent_feature: Optional[str] = None,
) -> bool:
```

2. yaml 写入块（L189-200 之间，`reason: ""` 行后）追加：
```python
            pf_yaml = f'"{parent_feature}"' if parent_feature else "null"
            f.write(f'  parent_feature: {pf_yaml}\n')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestUpdateRoadmapMeta -v`
Expected: PASS (含 2 个新测试 + 5 个原有测试共 7 个)

- [ ] **Step 5: Commit**

```bash
git add skills/propose/scripts/propose_change.py tests/unit/test_propose_change.py
git commit -m "feat(propose): add parent_feature param to update_roadmap_meta

- Optional parent_feature: Optional[str] = None (backward compatible)
- Write parent_feature to roadmap-meta.yaml (null when not provided)
- 2 new unit tests"
```

---

### Task 3: update_iteration_proposed 加 parent_feature 参数

**Files:**
- Modify: `skills/propose/scripts/propose_change.py:267-306` (update_iteration_proposed 函数)
- Test: `tests/unit/test_propose_change.py` (TestUpdateIterationProposed class)

- [ ] **Step 1: Write the failing test**

追加到 `tests/unit/test_propose_change.py` 的 `TestUpdateIterationProposed` 类末尾：

```python
    def test_writes_parent_feature_to_iteration(self, tmp_path):
        """parent_feature 参数应写入 iteration.json。"""
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        pc.update_iteration_proposed(
            str(tmp_path), "c1",
            phase="phase-1", category="core-impl", priority="P2",
            parent_feature="feature-stream",
        )
        loaded = it.load(str(tmp_path))
        match = next(c for c in loaded["changes"] if c["name"] == "c1")
        assert match["parent_feature"] == "feature-stream"

    def test_rejects_ungrouped_parent_feature(self, tmp_path):
        """parent_feature='__ungrouped__' 必须被拒绝。"""
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        with pytest.raises(ValueError, match="__ungrouped__"):
            pc.update_iteration_proposed(
                str(tmp_path), "c1",
                phase="phase-1", category="core-impl", priority="P2",
                parent_feature="__ungrouped__",
            )
        # iteration.json 未被修改
        loaded = it.load(str(tmp_path))
        assert all(c.get("name") != "c1" for c in loaded["changes"])

    def test_without_parent_feature_backward_compatible(self, tmp_path):
        """不传 parent_feature 时 iteration.json 无该字段（向后兼容）。"""
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        pc.update_iteration_proposed(
            str(tmp_path), "c1",
            phase="phase-1", category="core-impl", priority="P2",
        )
        loaded = it.load(str(tmp_path))
        match = next(c for c in loaded["changes"] if c["name"] == "c1")
        assert match.get("parent_feature") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestUpdateIterationProposed::test_writes_parent_feature_to_iteration -v`
Expected: FAIL with "TypeError: update_iteration_proposed() got an unexpected keyword argument 'parent_feature'"

- [ ] **Step 3: Write minimal implementation**

修改 `skills/propose/scripts/propose_change.py` 的 `update_iteration_proposed` 函数（L267-306）：

1. 签名加参数：
```python
def update_iteration_proposed(
    project_root: str,
    name: str,
    phase: str,
    category: str,
    priority: str,
    parent_feature: Optional[str] = None,
) -> Optional[bool]:
```

2. 在 docstring 后、`import sys` 前追加保留字校验：
```python
    # Reject reserved synthetic feature name (feature_view.py::UNGROUPED)
    if parent_feature == "__ungrouped__":
        raise ValueError(
            "parent_feature='__ungrouped__' is reserved (synthetic feature key); "
            "use a real feature name or omit parent_feature"
        )
```

3. `it_mod.add_or_update_change` 调用（L290-297）改为条件传入：
```python
        kwargs = {
            "name": name,
            "status": "proposed",
            "phase": phase,
            "category": category,
            "priority": priority,
        }
        if parent_feature is not None:
            kwargs["parent_feature"] = parent_feature
        data = it_mod.add_or_update_change(data, **kwargs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestUpdateIterationProposed -v`
Expected: PASS (含 3 个新测试 + 2 个原有测试共 5 个)

- [ ] **Step 5: Commit**

```bash
git add skills/propose/scripts/propose_change.py tests/unit/test_propose_change.py
git commit -m "feat(propose): add parent_feature param to update_iteration_proposed

- Optional parent_feature: Optional[str] = None (backward compatible)
- Reject reserved '__ungrouped__' synthetic key with ValueError
- Write parent_feature to iteration.json (only when explicitly provided)
- 3 new unit tests"
```

---

### Task 4: bash wrapper 传递 PARENT_FEATURE env var

**Files:**
- Modify: `skills/propose/scripts/propose_change.sh:27-95` (两个 wrapper 函数)
- Test: `tests/integration/test_propose_parent_feature.bats` (新文件)

- [ ] **Step 1: Write the failing test**

创建 `tests/integration/test_propose_parent_feature.bats`：

```bash
load test_helper

@test "propose: bash wrapper passes PARENT_FEATURE to create_skeleton_change" {
  # Setup: tmp project root
  tmp_proj="$BATS_TMPDIR/pf-test-$$"
  mkdir -p "$tmp_proj"
  # Minimal proposal-suggestions.md
  echo "[]" > "$tmp_proj/proposal-suggestions.md"

  # Source the wrapper
  source "$REPO_ROOT/skills/propose/scripts/propose_change.sh"

  # Invoke with env var
  PROJECT_ROOT="$tmp_proj" PARENT_FEATURE="feature-x" \
    propose_create_change "test-change" "--skeleton" "phase-1" "general" "P2"

  # Verify iteration.json contains parent_feature
  python3 -c "
import json, os
with open(os.path.join('$tmp_proj', '.rddf', 'state', 'iteration.json')) as f:
    data = json.load(f)
match = next((c for c in data['changes'] if c['name'] == 'test-change'), None)
assert match is not None, 'change not found in iteration.json'
assert match.get('parent_feature') == 'feature-x', f'parent_feature mismatch: {match}'
"

  # Verify roadmap-meta.yaml contains parent_feature
  yaml_path="$tmp_proj/openspec/changes/test-change/roadmap-meta.yaml"
  [ -f "$yaml_path" ]
  grep -q 'parent_feature: "feature-x"' "$yaml_path"
}

@test "propose: bash wrapper passes PARENT_FEATURE to finalize_change" {
  tmp_proj="$BATS_TMPDIR/pf-finalize-$$"
  mkdir -p "$tmp_proj/openspec/changes/c1"
  echo "[]" > "$tmp_proj/proposal-suggestions.md"
  # Pre-create iteration.json so update_iteration_proposed can load
  mkdir -p "$tmp_proj/.rddf/state"
  python3 -c "
import json, os
data = {'version': 4, 'updated_at': '2026-07-21T00:00:00+00:00', 'current_phase': 'phase-1', 'changes': []}
with open(os.path.join('$tmp_proj', '.rddf', 'state', 'iteration.json'), 'w') as f:
    json.dump(data, f)
"

  source "$REPO_ROOT/skills/propose/scripts/propose_change.sh"

  PROJECT_ROOT="$tmp_proj" PARENT_FEATURE="feature-y" \
    propose_finalize_change "c1" "phase-1" "core-impl" "P2" "core-impl:Core"

  # Verify iteration.json
  python3 -c "
import json, os
with open(os.path.join('$tmp_proj', '.rddf', 'state', 'iteration.json')) as f:
    data = json.load(f)
match = next((c for c in data['changes'] if c['name'] == 'c1'), None)
assert match is not None
assert match.get('parent_feature') == 'feature-y', f'expected feature-y, got {match.get(\"parent_feature\")}'
"

  # Verify roadmap-meta.yaml
  yaml_path="$tmp_proj/openspec/changes/c1/roadmap-meta.yaml"
  grep -q 'parent_feature: "feature-y"' "$yaml_path"
}

@test "propose: bash wrapper without PARENT_FEATURE is backward compatible" {
  tmp_proj="$BATS_TMPDIR/pf-noenv-$$"
  mkdir -p "$tmp_proj"
  echo "[]" > "$tmp_proj/proposal-suggestions.md"

  source "$REPO_ROOT/skills/propose/scripts/propose_change.sh"

  # No PARENT_FEATURE env var - should not crash
  PROJECT_ROOT="$tmp_proj" \
    propose_create_change "test-change" "--skeleton" "phase-1" "general" "P2"

  # iteration.json should not have parent_feature field (or it should be absent)
  python3 -c "
import json, os
with open(os.path.join('$tmp_proj', '.rddf', 'state', 'iteration.json')) as f:
    data = json.load(f)
match = next((c for c in data['changes'] if c['name'] == 'test-change'), None)
assert match is not None
assert match.get('parent_feature') is None, f'expected None, got {match.get(\"parent_feature\")}'
"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_propose_parent_feature.bats`
Expected: FAIL - "parent_feature mismatch" or "TypeError: got unexpected keyword argument"

- [ ] **Step 3: Write minimal implementation**

修改 `skills/propose/scripts/propose_change.sh`：

1. `propose_create_change` (L27-52) - 在 python heredoc 内读取 env var 并传给 Python：
```bash
propose_create_change() {
  local name="$1"
  local mode="$2"
  local current_phase="$3"
  local category="$4"
  local priority="$5"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

  if [ "$mode" = "--skeleton" ]; then
    PROJECT_ROOT="$PROJECT_ROOT" python3 <<PYEOF
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.propose.scripts import propose_change as pc
kwargs = dict(
    project_root=os.environ["PROJECT_ROOT"],
    name="$name",
    current_phase="$current_phase",
    category="$category",
    priority="$priority",
)
pf = os.environ.get("PARENT_FEATURE") or None
if pf is not None:
    kwargs["parent_feature"] = pf
result = pc.create_skeleton_change(**kwargs)
if not result:
    sys.exit(1)
PYEOF
  fi
}
```

2. `propose_finalize_change` (L55-95) - 同样模式：
```bash
propose_finalize_change() {
  local name="$1"
  local current_phase="$2"
  local category="$3"
  local priority="$4"
  local valid_categories="$5"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

  PROJECT_ROOT="$PROJECT_ROOT" CURRENT_PHASE="$current_phase" \
    VALID_CATEGORIES="$valid_categories" \
    python3 <<PYEOF
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.propose.scripts import propose_change as pc
project_root = os.environ["PROJECT_ROOT"]
current_phase = os.environ["CURRENT_PHASE"]
valid_categories = os.environ.get("VALID_CATEGORIES", "")
pf = os.environ.get("PARENT_FEATURE") or None
meta_kwargs = dict(
    project_root=project_root,
    name="$name",
    current_phase=current_phase,
    change_category="$category",
    priority="$priority",
    valid_categories=valid_categories,
)
if pf is not None:
    meta_kwargs["parent_feature"] = pf
pc.update_roadmap_meta(**meta_kwargs)
pc.update_roadmap_state(
    project_root=project_root,
    name="$name",
    change_phase=current_phase,
    change_category="$category",
)
iter_kwargs = dict(
    project_root=project_root,
    name="$name",
    phase=current_phase,
    category="$category",
    priority="$priority",
)
if pf is not None:
    iter_kwargs["parent_feature"] = pf
pc.update_iteration_proposed(**iter_kwargs)
PYEOF
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_propose_parent_feature.bats`
Expected: PASS (3 个测试全部通过)

- [ ] **Step 5: Commit**

```bash
git add skills/propose/scripts/propose_change.sh tests/integration/test_propose_parent_feature.bats
git commit -m "feat(propose): bash wrapper passes PARENT_FEATURE env var

- propose_create_change reads PARENT_FEATURE, passes to create_skeleton_change
- propose_finalize_change reads PARENT_FEATURE, passes to both update_roadmap_meta
  and update_iteration_proposed
- Oracle C1 safe: env-var passing (no bash string interpolation)
- 3 bats integration tests (with env, with env, backward compat without env)"
```

---

### Task 5: 端到端 feature 分组验证

**Files:**
- Test: `tests/unit/test_propose_change.py` (新 TestParentFeatureGrouping class)

- [ ] **Step 1: Write the failing test**

追加到 `tests/unit/test_propose_change.py` 末尾（新 class）：

```python
class TestParentFeatureGrouping:
    """端到端验证：两个 change 同 parent_feature 应归入同一 feature 组。

    依赖 iteration.list_feature_groups 与 derive_feature_name 已正确读取
    parent_feature 字段（这两个消费端自 v2.0.1 起已支持）。本测试
    验证写入端激活后，端到端 grouping 正常工作。
    """

    def test_two_changes_same_parent_feature_grouped_together(self, tmp_path):
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        # Create two changes with the same parent_feature
        pc.create_skeleton_change(
            str(tmp_path), "core-impl", "phase-1", "general", "P2",
            parent_feature="feature-rddf",
        )
        pc.create_skeleton_change(
            str(tmp_path), "core-tests", "phase-1", "general", "P2",
            parent_feature="feature-rddf",
        )
        # Load and group
        loaded = it.load(str(tmp_path))
        groups = it.list_feature_groups(loaded)
        # Both changes should be in the 'feature-rddf' group
        assert "feature-rddf" in groups
        names_in_group = {c["name"] for c in groups["feature-rddf"]}
        assert names_in_group == {"core-impl", "core-tests"}

    def test_changes_with_different_parent_features_separate(self, tmp_path):
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        pc.create_skeleton_change(
            str(tmp_path), "a-core", "phase-1", "general", "P2",
            parent_feature="feature-a",
        )
        pc.create_skeleton_change(
            str(tmp_path), "b-core", "phase-1", "general", "P2",
            parent_feature="feature-b",
        )
        loaded = it.load(str(tmp_path))
        groups = it.list_feature_groups(loaded)
        assert set(groups.keys()) == {"feature-a", "feature-b"}
        assert len(groups["feature-a"]) == 1
        assert len(groups["feature-b"]) == 1

    def test_parent_feature_overrides_name_prefix(self, tmp_path):
        """显式 parent_feature 优先于 feature- 命名约定。"""
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        # This change has feature- prefix (would derive 'feature-stream')
        # but explicit parent_feature overrides it
        pc.create_skeleton_change(
            str(tmp_path), "feature-stream-core", "phase-1", "general", "P2",
            parent_feature="feature-cdc",
        )
        loaded = it.load(str(tmp_path))
        groups = it.list_feature_groups(loaded)
        # Should be in feature-cdc group, NOT feature-stream
        assert "feature-cdc" in groups
        assert "feature-stream" not in groups
        assert groups["feature-cdc"][0]["name"] == "feature-stream-core"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestParentFeatureGrouping -v`
Expected: FAIL - TypeError (create_skeleton_change 不接受 parent_feature)

（注：若 Task 1-3 已完成，此测试应直接 PASS，则 Step 2 改为验证依赖已就绪的回归测试）

- [ ] **Step 3: Verify implementation is complete (no new code needed)**

此 task 不需要新实现代码 - 它验证 Task 1-3 的实现已正确激活消费端。
若 Task 1-3 已完成，跳到 Step 4。

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_propose_change.py::TestParentFeatureGrouping -v`
Expected: PASS (3 个测试)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_propose_change.py
git commit -m "test(propose): end-to-end parent_feature grouping tests

- Two changes with same parent_feature group together
- Different parent_features produce separate groups
- Explicit parent_feature overrides feature- name prefix
- 3 new unit tests in TestParentFeatureGrouping class"
```

---

### Task 6: propose.md 文档更新

**Files:**
- Modify: `skills/propose/SKILL.md:439-540` (Phase 4 section)

- [ ] **Step 1: Identify documentation gap**

Phase 4 中 `propose_create_change` 和 `propose_finalize_change` 调用未提及 `PARENT_FEATURE` env var。

- [ ] **Step 2: Add PARENT_FEATURE documentation**

在 `skills/propose/SKILL.md` Phase 4 的 `propose_create_change` 调用（L473）前追加注释块：

```bash
# Optional: set PARENT_FEATURE env var to register the change under a feature group
# This activates the parent_feature field in iteration.json + roadmap-meta.yaml
# Rejected values: "__ungrouped__" (reserved synthetic key)
# Example: PARENT_FEATURE="feature-rddf" propose_create_change ...
# When unset, behavior is unchanged (backward compatible)
```

同样在 `propose_finalize_change` 调用（L538）前追加相同注释。

- [ ] **Step 3: Verify doc update with grep**

Run: `grep -n "PARENT_FEATURE" skills/propose/SKILL.md`
Expected: 至少 2 处命中（两处注释块）

- [ ] **Step 4: Run propose skill structural test**

Run: `bats tests/integration/test_propose_skill.bats`
Expected: PASS（结构测试不应被破坏）

- [ ] **Step 5: Commit**

```bash
git add skills/propose/SKILL.md
git commit -m "docs(propose): document PARENT_FEATURE env var in Phase 4

- Add comment blocks before propose_create_change and propose_finalize_change
- Explain reserved __ungrouped__ rejection
- Note backward compatibility when env var unset"
```

---

### Task 7: 回归验证

**Files:**
- No code changes - verification only

- [ ] **Step 1: Run targeted unit tests**

Run: `python3 -m pytest tests/unit/test_propose_change.py tests/unit/test_iteration.py tests/unit/test_feature_view.py -v --tb=short`
Expected: ALL PASS（含新测试 + 原有测试）

- [ ] **Step 2: Run full unit test suite**

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: ALL PASS（57+ 文件，无新增失败）

- [ ] **Step 3: Run propose-related bats tests**

Run: `bats tests/integration/test_propose_skill.bats tests/integration/test_propose_parent_feature.bats`
Expected: ALL PASS

- [ ] **Step 4: LSP diagnostics on changed files**

Run: `lsp_diagnostics` on `skills/propose/scripts/propose_change.py` and `skills/propose/scripts/propose_change.sh`
Expected: 0 errors, 0 warnings

- [ ] **Step 5: No commit (verification only)**

此 task 仅验证，无代码变更。若所有 Step 1-4 通过，回归完成。

---

## Self-Review

### Spec 覆盖

| Proposal 需求 | 对应 Task |
|---|---|
| `create_skeleton_change + update_iteration_proposed 加 parent_feature 可选参数` | Task 1, 3 |
| `propose_change.sh bash wrapper 加 --parent-feature 参数解析` | Task 4 (env-var 模式，比位置参数更安全) |
| `拒绝 parent_feature=__ungrouped__ (保留字)` | Task 1, 3 (入口校验) |
| `前向声明语义: parent_feature 指向不存在的 feature 时视为定义新 feature` | 设计决策 D3 (无需代码 - 消费端 derive_feature_name 已支持) |
| `unit test + bats integration test` | Task 1-5 (unit) + Task 4 (bats) |
| `4 个 unit test + 2 个 integration test` | 实际：4 (Task 1) + 2 (Task 2) + 3 (Task 3) + 3 (Task 5) = 12 unit; 3 bats (Task 4)。超额完成 |

### 占位符扫描

无 TBD/TODO。每个 Step 含完整代码块。

### 类型一致性

- `parent_feature: Optional[str] = None` - 三个函数签名一致
- `kwargs["parent_feature"] = parent_feature` - 传递方式一致
- `pf_yaml = f'"{parent_feature}"' if parent_feature else "null"` - yaml 写入一致
- `pf = os.environ.get("PARENT_FEATURE") or None` - bash env 读取一致

### 文件路径检查

所有路径基于实际已存在的文件结构（已通过 Read 工具验证）。
