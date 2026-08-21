# design.md — fix-discover-ship-changes-needs-planning-fallback

## Context

`discover_ship_changes.py` 的 `_classify()` 在 line 208-211 处使用 `else` 兜底分支,导致当候选 `filesystem_present=False` 且无 worktree/branch 时一律打上 `needs_planning` flag(优先级 3)。该 flag 应仅在"待落盘或已规划"的 iteration_status (`None | "planned" | "proposed"`) 场景出现;当 `iteration_status` 为 `"approved"` 或 `"archived"` 时(已实施或已归档,但路径因 archive 已不存在),应仅持 `missing_disk` flag(优先级 6),不应再误提。

本提案经实测复现(2026-08-21):ship_candidates_json 报 10 个 needs_planning 候选,全部 10 个 proposal 在 `proposal-approved.md` 中标记为"已实施"。修正后,这些条目自动从 ship menu 顶部消失,不再误导。

修复策略:
- 在 `_classify()` 的 `else` 分支前加 iteration_status 守卫
- 区分 4 种 `iteration_status × filesystem_present` 组合
- 补 pytest unit tests 锁定新行为

## Goals / Non-Goals

**Goals:**
- 修复 `_classify()` line 211 的 catch-all 误判
- 保持 `filesystem_present=True` 场景的现有 executable / needs_reconciliation / in_progress 行为不变
- 单元测试覆盖 4 种 iteration_status × filesystem_present 组合
- 修复后,本会话刚归档的 `move-populate-roadmap-into-guide-arch` 等已 approved/archived 提案不再误报 needs_planning

**Non-Goals:**
- 不修改 iteration.json schema 或字段语义
- 不实现 iteration.json → proposal-approved.md 主动同步(另提:`sync-iteration-approved-to-archived`)
- 不修改 discover() 排序顺序或优先级常量
- 不重写 `fix-design-proposal-review-approved-parsing`(已标记已实施,实际未解决数据同步;不在本提案范围)

## Decisions

### 1. 修改 `_classify()` 在 `else` 分支前加 iteration_status 守卫

**决策**:将 line 208-211 的 `elif ... else: needs_planning` 改为按 iteration_status 分流:

```python
def _classify(cand: Candidate) -> None:
    if not cand.filesystem_present:
        cand.flags.append("missing_disk")
    if cand.iteration_status is None and cand.filesystem_present:
        cand.flags.append("needs_reconciliation")
    if cand.worktree or cand.branch:
        cand.flags.append("in_progress" if cand.tasks_total - cand.tasks_done > 0 else "ready_to_archive")
    elif cand.filesystem_present and cand.artifact_complete:
        cand.flags.append("executable")
    elif cand.iteration_status in (None, "planned", "proposed"):
        # filesystem_present=False 且迭代中"待落盘/已规划"——正常需要创建 proposal.md
        cand.flags.append("needs_planning")
    # else: filesystem_present=False 且 iteration_status in ("approved", "archived")
    #       历史已批准/已归档且路径因 archive 缺失——仅 missing_disk,不再 needs_planning
```

**理由**:
- 与现有 branch 注释一致(注释说明 `branch-only` 候选被丢弃以避免遗留)
- 区分"真需要 plan"vs"历史遗留,仅路径缺失"
- 最小化代码变更(单分支守卫)

### 2. 保留现有 priority 常量排序逻辑

**决策**:不变更 priority dict 的键值。修复后:
- 真正 needs_planning (None/planned/proposed) 仍排第 3(优先级最低数字=最先排序)
- missing_disk 仍排第 6(隐藏底部)

**理由**:修复目标只是防止 approved/archived 误报 needs_planning,不改变排序行为。

### 3. 测试覆盖 4 种 iteration_status × filesystem_present 组合

**决策**:在 `tests/unit/test_discover_ship_changes.py` 新增 4 个测试函数(每个组合一个):

| 测试名 | filesystem_present | iteration_status | 预期 flags |
|--------|---------------------|------------------|-----------|
| `test_classify_approved_missing_disk_only` | False | "approved" | ["missing_disk"] |
| `test_classify_archived_missing_disk_only` | False | "archived" | ["missing_disk"] |
| `test_classify_proposed_needs_planning` | False | "proposed" | ["missing_disk", "needs_planning"] |
| `test_classify_planned_needs_planning` | False | "planned" | ["missing_disk", "needs_planning"] |

**理由**:覆盖守卫的所有分支,锁定行为。

### 4. 修复文件:直接修改 rdd-workflow skill 内的 `_lib/discover_ship_changes.py`

**决策**:修改 `/home/ubuntu/.agents/skills/_lib/discover_ship_changes.py`(全局安装路径)。这是用户级 skill,影响所有 rdd-workflow 项目使用。

**理由**:
- ship_candidates_json 是 bash 包装调用 `_discover_py()` → 加载全局安装的模块
- 修改全局 skill 一次,所有项目受益
- 本地仓库没有 `_lib/discover_ship_changes.py`(skill 是外部依赖)

**备选**(已否决):
- 在仓库内建本地副本覆盖 — 增加维护成本,且与全局 skill 行为可能漂移
- 在 ~/.agents/skills/ 下 fork — 不必要的派生

### 5. 验证方式:单元测试 + 手动 ship_candidates_json 端到端测试

**决策**:
- 单元测试:`pytest tests/unit/test_discover_ship_changes.py -v` 全过
- 手动测试:创建临时 tmp 仓库,设 iteration.json 某 change status="approved",调 ship_candidates_json 验证输出不包含 needs_planning flag

**理由**:双层验证,单元覆盖逻辑,手动覆盖集成。

## Risks / Trade-offs

| 风险 | 严重度 | 缓解 |
|------|--------|------|
| 全局 skill 修改可能影响其他 rdd-workflow 项目 | MEDIUM | 单元测试覆盖 4 种组合;修复语义严格收缩(只移除误标 flag,不加新 flag) |
| 现有项目依赖 needs_planning 误报作为 work-around | LOW | 误报是 bug 而非 feature;误报消失后,真待 plan 的 change 仍正确标 needs_planning |
| 单元测试 setup 需要 mock iteration.json | LOW | 用 tmp_path fixture + monkeypatch 注入数据 |

## Implementation Plan (Tasks 概览)

完整 tasks 拆分见 `tasks.md`。覆盖:
1. **T1**: 修改 `discover_ship_changes.py::_classify()` line 208-211 加 iteration_status 守卫
2. **T2**: 在 `tests/unit/test_discover_ship_changes.py` 新增 4 个 pytest tests(4 种 iteration_status × filesystem_present 组合)
3. **T3**: 验证全套 pytest 不退化 + 手测 ship_candidates_json 端到端
4. **T4**: (可选) 用 rdd-doctor 检查孤儿 gates,确认无回归

预计修改行数:约 5 行(主逻辑) + 80 行(测试) = ~85 行。