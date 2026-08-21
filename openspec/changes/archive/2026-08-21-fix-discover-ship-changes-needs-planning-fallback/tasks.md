## Implementation Tasks

> 任务编号沿用 `proposal.md` §范围 A-D + 测试场景 T1-T18 编号。**checkboxes 是契约**:执行者按序勾选,全部勾完才能进 archive 阶段。

### A. 修改 `_classify()` 加 iteration_status 守卫

- [x] A1. 打开 `/home/ubuntu/.agents/skills/_lib/discover_ship_changes.py`,定位 `_classify()` 函数 (line 200-211)
- [x] A2. 在 `elif cand.filesystem_present and cand.artifact_complete:` 分支后、`else: cand.flags.append("needs_planning")` 前插入守卫:

```python
elif cand.iteration_status in (None, "planned", "proposed"):
    # filesystem_present=False 且迭代中"待落盘/已规划"——正常需要创建 proposal.md
    cand.flags.append("needs_planning")
```

(原 `else` 改为无操作 — 已 approved/archived 但路径缺失仅持 missing_disk,不再误报 needs_planning)

- [x] A3. 验证修改后文件 Python 语法合法: `python3 -c "import ast; ast.parse(open('/home/ubuntu/.agents/skills/_lib/discover_ship_changes.py').read())"`

### B. 添加 4 个 pytest unit tests 锁定新行为

- [x] B1. 检查 `tests/unit/test_discover_ship_changes.py` 是否存在;若不存在,创建骨架(参考 `tests/unit/test_iteration.py` 风格)
- [x] B2. 在该文件中新增 4 个测试函数:

```python
import pytest
from pathlib import Path
from skills._lib.discover_ship_changes import Candidate, _classify


def test_classify_approved_missing_disk_only():
    """approved + filesystem_present=False → only missing_disk (NOT needs_planning)."""
    cand = Candidate(name="x", filesystem_present=False, iteration_status="approved")
    _classify(cand)
    assert cand.flags == ["missing_disk"]


def test_classify_archived_missing_disk_only():
    """archived + filesystem_present=False → only missing_disk (NOT needs_planning)."""
    cand = Candidate(name="x", filesystem_present=False, iteration_status="archived")
    _classify(cand)
    assert cand.flags == ["missing_disk"]


def test_classify_proposed_needs_planning():
    """proposed + filesystem_present=False → needs_planning (existing behavior preserved)."""
    cand = Candidate(name="x", filesystem_present=False, iteration_status="proposed")
    _classify(cand)
    assert cand.flags == ["missing_disk", "needs_planning"]


def test_classify_planned_needs_planning():
    """planned + filesystem_present=False → needs_planning (existing behavior preserved)."""
    cand = Candidate(name="x", filesystem_present=False, iteration_status="planned")
    _classify(cand)
    assert cand.flags == ["missing_disk", "needs_planning"]
```

- [x] B3. 验证导入路径: `python3 -c "from skills._lib.discover_ship_changes import Candidate, _classify; print('OK')"`

### C. 验证全套不退化

- [x] C1. 跑新测试: `pytest tests/unit/test_discover_ship_changes.py -v --tb=short` → 4/4 pass
- [x] C2. 跑全量 unit: `pytest tests/unit/ -q --tb=short` → baseline 2201 passed + 4 新测试 pass,4 pre-existing failures 不变,无新增失败
- [x] C3. 跑 smoke bats: `bats tests/smoke.bats` → 9/9 pass

### D. 手动端到端验证

- [x] D1. 在 tmp 仓库复现 bug: 创建 tmp 仓库,设 iteration.json 中某 change status="approved",调 ship_candidates_json 验证输出 flags 仅 `["missing_disk"]`
- [x] D2. 验证现状(本会话已归档的 `move-populate-roadmap-into-guide-arch`): `ship_candidates_json` 输出该 change 仅 `["missing_disk"]`(因为 status="archived")
- [x] D3. 验证真 needs_planning 路径:设 `fix-foo-test.md` 在 iteration.json status="proposed",验证 ship_candidates_json 输出包含 `needs_planning` flag

### E. (可选) rdd-doctor 巡检

- [x] E1. 跑 `bash skills/rdd-doctor/scripts/doctor.sh --category state` → 确认无孤儿 gate 引入

## 验收标准

- [x] `discover_ship_changes.py::_classify()` line 208-211 已加 `iteration_status in (None, "planned", "proposed")` 守卫
- [x] `tests/unit/test_discover_ship_changes.py` 含 4 新测试,全部 pass
- [x] pytest unit baseline: 2201 + 4 = 2205 passed,4 pre-existing failures 不变,无新增失败
- [x] 端到端验证:tmp 仓库 + iteration.json status="approved" → ship_candidates_json 输出不含 needs_planning
- [x] 现有 needs_planning 路径未被破坏 (proposed/planned/None 状态仍正确标 needs_planning)
- [x] 现有 executable / in_progress / ready_to_archive / needs_reconciliation 路径行为不变