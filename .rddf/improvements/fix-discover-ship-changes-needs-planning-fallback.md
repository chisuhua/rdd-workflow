# fix-discover-ship-changes-needs-planning-fallback

**优先级**: P1 | **来源**: 本会话 view bug 调查 (2026-08-21)
**阶段**: v2.2 | **分类**: core-impl
**类型**: bug
**依赖 ADR**: ADR-0030 (跨项目联邦状态模型)

## 架构依据

`discover_ship_changes.py` 的 `_classify()` 函数 line 211 在 `filesystem_present=False` 且非 worktree/branch 时走 `else` 分支错误打上 `"needs_planning"` flag（优先级 3）。该 flag 应仅在"迭代中正常创建 proposal.md"的场景出现 — 即 `iteration_status in (None, "planned", "proposed")` 且 `filesystem_present=False`（待落盘或已规划）。

当 `iteration_status` 为 `"approved"` 或 `"archived"` 但 `openspec/changes/<name>/` 不存在（已实施但未路径重访，或历史遗留），`_classify` 仍错误归类为 `needs_planning`，应改为仅持 `"missing_disk"` flag（优先级 6）。

**复现证据**（2026-08-21 session）：

- `ship_candidates_json` 报 10 个候选 flag=`"missing_disk"` + `"needs_planning"`
- 全部 10 个 proposal 在 `proposal-approved.md` 中标记为"已实施"(2026-08-16)
- 真实的优先级 3（needs_planning）使这些条目排在 ship menu 顶部，掩盖了真正的待处理 work

**根因**（`/home/ubuntu/.agents/skills/_lib/discover_ship_changes.py`）：

```python
def _classify(cand: Candidate) -> None:
    if not cand.filesystem_present:
        cand.flags.append("missing_disk")              # 已正确加 missing_disk
    if cand.iteration_status is None and cand.filesystem_present:
        cand.flags.append("needs_reconciliation")
    if cand.worktree or cand.branch:
        cand.flags.append("in_progress" if cand.tasks_total - cand.tasks_done > 0 else "ready_to_archive")
    elif cand.filesystem_present and cand.artifact_complete:
        cand.flags.append("executable")
    else:
        cand.flags.append("needs_planning")             # ← BUG: catch-all 错误触发
```

`else` 分支条件"既无 worktree/branch,又无 filesystem_present+artifact_complete"覆盖了"`filesystem_present=False` 且 iteration_status=approved/archived"这一子场景,该子场景的实际语义是"历史已实施,当前路径缺失",不是"需要创建 proposal.md"。

## 范围

**In Scope**:

- 修改 `skills/_lib/discover_ship_changes.py::_classify()` line 208-211 逻辑分支,在 `else` 前加 iteration_status 守卫
- 区分 4 种 iteration_status × filesystem_present 组合的预期 flag
- 补 ≥4 个 pytest unit tests 锁定新行为（每个组合一个）

**Out Scope**:

- iteration.json schema 变更
- openspec archive 命令本身的逻辑
- 主动清理 iteration.json 中的 stale entry（另提案：`sync-iteration-approved-to-archived`）
- `fix-design-proposal-review-approved-parsing` 的实施重写（已标记已实施但实际未解决数据同步）

## 关键场景

**场景 1：已批准 / 已归档但路径缺失**

- GIVEN `iteration.json` 中某 change `status="approved"` 或 `"archived"` 但 `openspec/changes/<name>/` 不存在
- WHEN `ship_candidates_json` 调用 `discover`
- THEN 候选仅持 `["missing_disk"]` flag（不出现 `"needs_planning"`）
- AND sort key 以 `"missing_disk"` 优先级 6 排序，隐藏在底部
- AND 用户 ship menu 不再误提该条

**场景 2：待落盘 proposal（应正常出现 needs_planning）**

- GIVEN `iteration.json` 中某 change `status="planned"` 或 `"proposed"`,但 `openspec/changes/<name>/` 不存在
- WHEN `discover` 运行
- THEN 候选持 `["missing_disk", "needs_planning"]` flag
- AND sort key 以 `"needs_planning"` 优先级 3 排序，提示用户需要 plan

**场景 3：可执行（现状，不变）**

- GIVEN `filesystem_present=True` 且 `artifact_complete=True`
- WHEN `discover` 运行
- THEN 候选持 `["executable"]` flag（无变化）

**场景 4：无任何信号但有磁盘（现状，不变）**

- GIVEN `filesystem_present=True` 但 `artifact_complete=False`
- WHEN `discover` 运行
- THEN 候选持 `["missing_disk", "needs_planning"]` flag（artifact 待补全）

## 技术约束

- **MUST**: 保留 `filesystem_present=True` 场景的现有 `executable` / `needs_reconciliation` 逻辑分支
- **MUST**: `_classify` 的修改在所有 4 个 source 路径合并后行为一致（`_disk_candidates` / `_handoff_candidates` / `_iteration_candidates` / `_git_candidates`）
- **MUST**: 添加 pytest unit tests 覆盖 4 种 iteration_status × filesystem_present 组合
- **MUST NOT**: 修改 iteration.json schema 或字段语义
- **MUST NOT**: 修改 discover() 的排序顺序或优先级常量
- **SHOULD**: 单元测试覆盖 `Candidate.flags` 列表的精确内容（避免单元素被追加遗漏）
- **SHOULD**: 在 `discover_ship_changes.py` 头部注释添加本次修复的 commit hash 与 issue 链接

## 验收标准

- `pytest tests/unit/test_discover_ship_changes.py` 添加 ≥4 新 tests 全过（每个 scenarios 1+1）
- 全套测试 baseline：2201 passed / 4 pre-existing failures unchanged / 无新增失败
- 手动验证：创建临时 test fixture,设 `iteration.json` 中某 change `status="approved"`,确认 `ship_candidates_json` 输出该候选的 `flags=["missing_disk"]` 而非 `["missing_disk", "needs_planning"]`
- 验证场景 4:手动设 `filesystem_present=True, artifact_complete=False`,确认保留 `needs_planning` flag（向后兼容）
- 现有 ship menu 截图：原 10 个 needs_planning 误报应消失,executable 列表保持正确

## 不在本提案范围但相关

- **`fix-design-proposal-review-approved-parsing`** (P0, 2026-08-07 标记已实施) — 实际未解决数据同步问题。建议另提案 `sync-iteration-approved-to-archived` 主动清理 stale entry。
- **`fix-archive-iteration-sync`** (P0, 2026-08-06 标记已实施) — 涉及 plan-handoff 的 archived_changes 同步,与本提案不重叠。

## 复现命令

```bash
# 验证当前 bug
rddf-discover-ship-changes  # 或直接调 ship_candidates_json
# 期望修复前：输出 10 个 needs_planning（含已 approved 的 stale entry）
# 期望修复后：输出 0 个 needs_planning（除非真有待 plan 的）

# 单元测试
pytest tests/unit/test_discover_ship_changes.py -v
```

## 相关 issue / commit

- session: rds_d911d19adace (2026-08-21 ship of move-populate-roadmap-into-guide-arch)
- discovery 在 Phase 1 plan 阶段 ship_candidates_json 调用中暴露