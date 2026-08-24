# clean-stale-plan-handoff-on-ship-done

**优先级**: P1 | **来源**: 本会话 view bug 调查 (2026-08-22)
**阶段**: v2.2 | **分类**: core-impl
**类型**: bug
**依赖 ADR**: —
**后续提案**: `fix-discover-ship-changes-needs-planning-fallback`（已实施但未触及此根因）

## 架构依据

`skills/guide-ship/scripts/ship_archive.sh::cleanup_plan_handoff()` 是 archive 流程末尾的 state-cleanup hook（L299 调用，L331-362 实现）。它当前维护 `.rddf/state/.plan-handoff.json` 的 3 个字段：

```python
data["archived_at"] = datetime.now(timezone.utc).isoformat()
active = data.get("active_changes", 0)
if isinstance(active, int) and active > 0:
    data["active_changes"] = active - 1
if "archived_changes" not in data:
    data["archived_changes"] = []
data["archived_changes"].append(change_name)
```

但**未清空 `current_change` 字段** —— 这是 2026-08-21 ship `fix-discover-ship-changes-needs-planning-fallback` 时残留的 stale state 的根因：`discover_ship_changes` 已修（commit `f1334e0`），但 plan-handoff.json 的 `current_change` 仍指向已 archived 的 change，导致 `ship_candidates_json` 后续每次入口都重复报告 `flags=["missing_disk", "needs_planning"]`，直到手工清理。

**复现证据**（2026-08-22 session）：

- 触发 `skill_use("guide-ship")` → Phase 1 discover
- `ship_candidates_json` 输出：
  ```json
  {
    "name": "fix-discover-ship-changes-needs-planning-fallback",
    "filesystem_present": false,
    "flags": ["missing_disk", "needs_planning"]
  }
  ```
- 实际：`fix-discover-ship-changes-needs-planning-fallback` 已在 6 个 commit 前 archived（`b0b2826 archive(...)`), `git worktree list` 仅 master，`git status --short` 干净
- plan-handoff.json 仍持：
  ```json
  {
    "active_changes": 1,
    "current_change": "fix-discover-ship-changes-needs-planning-fallback",
    "ship_started_at": null
  }
  ```
- 这是 cleanup_plan_handoff 的"半个 cleanup" bug：`active_changes` 应在最后一次 archive 时归 0、`current_change` 应在 archive 时清空、`ship_started_at` 应在 ship-done 时清空 —— 但 cleanup_plan_handoff 只做了"累加 archived_changes / 减一 active_changes"，没有"最终态收敛"逻辑。

## 范围

**In Scope**:

- 修改 `skills/guide-ship/scripts/ship_archive.sh::cleanup_plan_handoff()` 的 Python 块
  - 新增 `current_change` 字段处理：当被 cleanup 的 `change_name == data.get("current_change")` 时设 `current_change=None`
  - 新增 `ship_started_at` 字段处理：所有 changes 归档完成（active_changes==0）时设 `ship_started_at=None`
  - 保留 `execution_mode_decisions` 不动（属于 ship 历史记录，对未来 ship 决策有参考价值）
- 添加最终态一致性检查（active_changes==0 ⇒ current_change 必为 None ⇒ ship_started_at 必为 None）
- 写 1 个新 bats integration test `tests/integration/test_cleanup_plan_handoff.bats`（≥5 cases 锁定新行为）
- 写 1 个新 pytest unit test `tests/unit/test_cleanup_plan_handoff.py` 覆盖 Python 块的 4 个分支

**Out Scope**:

- discover_ship_changes.py 自身（已修，见 `fix-discover-ship-changes-needs-planning-fallback`）
- iteration.json 的 stale-entry 主动清理（另提案：`sync-iteration-approved-to-archived`）
- plan-handoff.json schema 演进（无 schema 变更需求）
- 现有 `cleanup_plan_handoff` 的 archived_changes / active_changes 累加逻辑（已正确）

## 关键场景

**场景 1：单 change archive（current_change 匹配）**

- GIVEN plan-handoff.json `{active_changes: 1, current_change: "fix-foo"}`
- AND 调用 `cleanup_plan_handoff("fix-foo")`
- THEN 末态：`{active_changes: 0, current_change: null, archived_changes: ["fix-foo"]}`
- AND `execution_mode_decisions["fix-foo"]` 保留

**场景 2：多 change 依次 archive（current_change 已被手动切换）**

- GIVEN plan-handoff.json `{active_changes: 2, current_change: "fix-foo"}`
- AND 1st 调用 `cleanup_plan_handoff("fix-bar")`（已先 archive bar）
- THEN 中间态：`{active_changes: 1, current_change: "fix-foo", archived_changes: ["fix-bar"]}`
- AND 2nd 调用 `cleanup_plan_handoff("fix-foo")`
- THEN 末态：`{active_changes: 0, current_change: null, archived_changes: ["fix-bar", "fix-foo"]}`

**场景 3：ship-done 后，ship_started_at 清空**

- GIVEN plan-handoff.json `{active_changes: 0, current_change: null, ship_started_at: "2026-08-22T13:00:00+00:00"}`
- WHEN 调用 `cleanup_plan_handoff`（任意 change_name）作为 ship-done marker
- THEN `ship_started_at: null`

**场景 4：current_change 不匹配被 archive 的 change（保留）**

- GIVEN plan-handoff.json `{current_change: "fix-foo"}`
- AND 调用 `cleanup_plan_handoff("fix-bar")`（不同 change）
- THEN `current_change: "fix-foo"` 保留（不被意外清空）
- AND 仅 `active_changes`, `archived_changes` 更新

**场景 5：plan-handoff.json 不存在（idempotent skip）**

- GIVEN `~/.rddf/state/.plan-handoff.json` 不存在
- WHEN 调用 `cleanup_plan_handoff`
- THEN 立即 return 0，无错误，无副作用

**场景 6：active_changes 已为 0（不应负数）**

- GIVEN `{active_changes: 0}` （已被前次 cleanup 减到底）
- AND 调用 `cleanup_plan_handoff("fix-foo")`
- THEN `active_changes` 保持 0，不变负数

## 技术约束

- **MUST**: 在 `cleanup_plan_handoff` Python 块中加 `current_change` / `ship_started_at` 守卫逻辑
- **MUST**: 保留现有 `archived_at` / `active_changes` / `archived_changes` / `execution_mode_decisions` 行为
- **MUST**: 加 1 个 integration test `tests/integration/test_cleanup_plan_handoff.bats`，≥5 cases（覆盖场景 1-5）
- **MUST**: 加 1 个 unit test `tests/unit/test_cleanup_plan_handoff.py`，覆盖 Python 内联块的 4 个分支
- **MUST NOT**: 修改 `_classify()`（属于 `fix-discover-ship-changes-needs-planning-fallback` scope）
- **MUST NOT**: 修改 schema（`skills/_lib/schemas/plan_handoff_schema.json`）—— 字段全 optional
- **MUST NOT**: 引入新 env-var（保持调用接口不变）
- **SHOULD**: Python 块改写为外部 `skills/_lib/cleanup_plan_handoff.py`（遵循 Round A/B 6-task-580 行内联提取模式），但本提案优先实现正确性，提取留 follow-up
- **SHOULD**: 在 `cleanup_plan_handoff` 函数 docstring 中说明"末态收敛语义"

## 验收标准

- `pytest tests/unit/test_cleanup_plan_handoff.py -v` 4 全过
- `bats tests/integration/test_cleanup_plan_handoff.bats` 5+ 全过
- `./test.sh --unit --integration` 全部 baseline 维持（无新增失败，已知失败见 `tests/KNOWN_FAILURES.txt`）
- `./test.sh --full --regression` 全绿或仅 baseline 已知失败
- 手动验证（场景 1）：构造假 plan-handoff.json（active_changes=1, current_change="fix-foo"），调 `cleanup_plan_handoff "fix-foo"`，确认末态 `{active_changes:0, current_change:null}`
- 手动验证（场景 4）：构造假 `{current_change:"fix-foo"}`，调 `cleanup_plan_handoff "fix-bar"`，确认 `current_change` 仍为 `"fix-foo"`
- 手动验证（场景 6）：构造 `{active_changes:0}`，调 `cleanup_plan_handoff "fix-foo"`，确认 `active_changes=0`（非负）
- 自动验证：`python3 skills/_lib/ship_invariants.py check-plan-handoff` （或类似脚本）—— 集成到 `rdd-doctor --category state` 检 `state` 类

## 不在本提案范围但相关

- **`fix-discover-ship-changes-needs-planning-fallback`** (P1, 已于 2026-08-21 实施) — 修了 discover 脚本的 flag 分类，但未触及 plan-handoff 的字段清理。本提案补上另一面。
- **`fix-archive-iteration-sync`** (P0, 已实施) — 涉及 iteration.json 的 archive 后同步，与 plan-handoff 是平行的两个 state 文件，分别清理。
- **`fix-design-proposal-review-approved-parsing`** (P0, 2026-08-07 标记已实施) — 实际未解决数据同步。建议另提案 `sync-iteration-approved-to-archived` 主动清理 iteration.json stale entry。

## 复现命令

```bash
# 验证当前 bug（2026-08-22 之前）
cat .rddf/state/.plan-handoff.json | jq '.current_change, .active_changes'
# 期望修复前："fix-discover-ship-changes-needs-planning-fallback" / 1（陈旧）
# 期望修复后：null / 0（在最后一次 archive 自动 cleanup）

# 单元 + 集成测试
pytest tests/unit/test_cleanup_plan_handoff.py -v
bats tests/integration/test_cleanup_plan_handoff.bats

# 手动模拟
python3 -c "
import json, subprocess
# 备份 + 写假 plan-handoff.json + 调 helper + 验证末态
"
```

## 相关 issue / commit

- session: rds_a73dfd366dd3 (2026-08-22 ship-done gate check)
- 暴露路径：`guide-ship` Phase 1 `ship_candidates_json` ← `discover_ship_changes.py` flag 优先级 ← plan-handoff `current_change` 残留
- 前序修复：`f1334e0 fix(ship): stop surfacing already-approved/archived changes as needs_planning` （半解，未触及 plan-handoff）
- 关联提案：`fix-discover-ship-changes-needs-planning-fallback` （同源，共 2 个面）
