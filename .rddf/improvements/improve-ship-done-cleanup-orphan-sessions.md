# improve-ship-done-cleanup-orphan-sessions

**优先级**: P2 | **来源**: session 2026-08-01 — `guide-ship` Phase 5 (ship-done) 菜单未提示存在的 orphaned rddf-sessions (本会话发现 3 个: `rds_a1b5` / `rds_1221` / `rds_0569`),用户关闭 session 后才知道 session 残留
**阶段**: default | **分类**: ux
**类型**: ux-improvement

## 架构依据

- **ADR-0017** §3 (rddf-session lifecycle): session 进入 `orphaned` 状态后无自动 GC,需用户显式 `abandon` 或 `archive-history`
- **ADR-0021** (已采纳): Phase 2 per-skill helper 迁移 — 单 skill helper 移走,跨 skill helper 留在 `_lib/`
- **触发场景**: 用户 `skill_use("guide")` → 入口菜单看到 "3 个 orphaned sessions", 但 `skill_use("guide-ship")` 进入 ship-done 后**没有任何步骤**提示清理这些孤儿。session 2026-08-01 (commit `34b9a95` 之前): 用户从入口走到 ship-done,从未被提示过有 orphaned session 可清理
- **临时绕过 (不可持续)**: 用户要么手动 `cat .rddf/state/sessions.json | jq` 看,要么等下次 `skill_use("guide")` 看入口菜单 (绕远路);不主动清理会越积越多

## 范围

**In Scope**:
1. `skills/guide-ship/scripts/ship_done.sh::check_remaining_work` — 增加 orphaned 检测 + 条件菜单
2. 新增 helper: `skills/_lib/sessions_count.sh::count_orphaned_sessions <project_root>` — 输出 orphaned session 数 (返回 exit 0 always,纯只读)
3. `tests/integration/test_ship_done_orphan_prompt.bats` — 4 矩阵测试 (有/无 orphans × 有/无 changes)
4. `guide-ship/SKILL.md` Phase 5 章节 — 更新文档说明新菜单

**Out Scope**:
- 不修改 `rddf-session` skill 的 abandon/archive-history 逻辑 (cleanup 是用户决定)
- 不引入自动清理 (prompt 用户,用户选)
- 不为 `guide-arch` / `guide-plan` 同步改动 (本改进仅 ship-done 这一阶段; 如有需要另起)
- 不动 `sessions.json` schema

## 关键场景

**场景 1** (有 orphans + 无 changes):
- GIVEN `.rddf/state/sessions.json` 含 3 个 state=orphaned + 0 active changes + 0 worktrees
- WHEN 调用 `check_remaining_work $PROJECT_ROOT`
- THEN 菜单输出:
  ```
  ✅ 所有 changes 已处理完毕
  
  ⚠️ 发现 3 个 orphaned rddf-sessions (rds_a1b5, rds_1221, rds_0569)
     建议清理:`skill_use("rddf-session", "abandon", ...)` 或 `archive-history`
  
  请选择:
  1. 继续处理 (skill_use("guide-ship")) - 还有 worktree 要处理
  2. 回到 spec 端 ...
  3. 本次 session 结束 ...
  4. 项目完成 ...
  5. 🧹 清理 3 个 orphaned sessions (skill_use("rddf-session", "abandon", ...))
  i. 其他输入
  ```

**场景 2** (无 orphans + 无 changes):
- GIVEN sessions.json 无 orphaned + 0 active changes + 0 worktrees
- WHEN 调用 `check_remaining_work`
- THEN 输出与当前完全一致 (diff 0 字节) — 避免视觉噪声

**场景 3** (有 orphans + 有 changes):
- GIVEN 1 个 state=orphaned + 1 active change
- WHEN 调用 `check_remaining_work`
- THEN 走"还有"分支 (L28),orphan 提示 + 清理选项 5 一起出现

**场景 4** (sessions.json 不存在,首次使用):
- GIVEN `.rddf/state/sessions.json` 不存在 (项目从未用过 rddf-session)
- WHEN 调用 `check_remaining_work`
- THEN 走无 orphans 分支, 无 error (helper silently treats 0)

## 技术约束

**MUST**:
- 新 helper `count_orphaned_sessions` 是**只读** (不修改 sessions.json),同 `check_stale_workflow_state` 的 sentinel 约束
- 只统计 `state == "orphaned"`,不区分 kind (arch / plan / ship 一视同仁)
- 菜单输出**不得**格式化破坏 `check_remaining_work` 的已有契约:行数格式 (5 行选项) 与原文一致
- sessions.json 读取失败时 (corrupt JSON / permission denied),默认按 0 处理,不阻塞
- 详细 session id 列表 (e.g. `rds_a1b5, rds_1221`) **只列前 3 个**,超过 3 个追加 `... +N more`,避免菜单纵向过长
- 新增的 `选项 5` 是**唯一**新增的 option,不动现有 1/2/3/4/i 语义
- 测试覆盖率 100% (4 矩阵 + 1 corruption case + 1 sessions.json 不存在 case = 6)

**MUST NOT**:
- 不得把 orphan 清理动作做成自动执行 (用户必须显式选择 option 5)
- 不得修改 `sessions.json` schema (读 `state` 字段足够)
- 不得把 sessions 列表泄露到 RECO_JSON 或环境变量 (隐私 + 体积)
- 不得复用现有 `check_stale_workflow_state` (功能不同,即使模式相似)
- 不得让 helper 递归调用其他 skill (必须 atomic bash function)

**SHOULD**:
- helper 用 `jq` 优先 (项目可能装了), 用 `python3 -c` fallback (已确认项目用 python3.11+)
- helper 输出**只 echo int**,不输出 human-readable 文案 (让 `check_remaining_work` 包装)
- helper 加 set -euo pipefail (match repo style)

## 验收标准

1. **新增 helper 行为**: `tests/integration/test_ship_done_orphan_prompt.bats` 6 case 全 PASS:
   - 有 3 orphans + 无 changes → 菜单出现选项 5 + ⚠️ 提示
   - 无 orphans + 无 changes → 输出 diff = 0 (与未改动代码一致)
   - 有 1 orphan + 有 1 change → 走"还有"分支 + 选项 5 出现
   - sessions.json 不存在 → 默认 0, 无 error
   - sessions.json 内容损坏 → helper exit 0, 默认 0
   - 超过 3 orphans → 详情只列前 3 + `... +N more`
2. **菜单输出稳定**: 选项 5 出现时,选项 1-4 + i 的行内容/顺序与现有完全一致 (diff 0)
3. **行数约束**: `ship_done.sh` ≤ 30 行 (现状 46); `sessions_count.sh` ≤ 20 行; 总代码 ≤ 50 行
4. **CI 绿**: `bats tests/integration/test_ship_done_orphan_prompt.bats` + 现有 `tests/integration/test_ship_*.bats` 全 PASS 零修改
5. **向后兼容**: 现有调用 `check_remaining_work` 的上游 (`guide-ship` SKILL.md Phase 5 段落) 不需改调用方式
6. **文档**: `guide-ship/SKILL.md` Phase 5 段落加 1 段 (≤5 行) 说明孤儿提示

## 关联

- 与 `fix-scanner-fallback-and-orphan-archival.md` 互补:后者修 schema (orphaned 应入 `_TERMINAL_STATES`),本改进修 UX (即使 schema 改了,用户也得在 ship-done 看到提示)
- 与 `guide-ship/scripts/ship_done.sh` 单文件改动,不跨 skill
- 后续可扩展: `guide-arch` / `guide-plan` 同款菜单提示 (Out of scope)
