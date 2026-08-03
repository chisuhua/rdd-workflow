# add-rddf-session-status-cmd

## Why

rddf-session 当前用户可见性差:
- 用户只在 entry hook 输出 1 行 session ID (`rds_5219d1402217 (stage_ship, parent=...)`)
- 想看完整状态必须手动 `cat .rddf/state/sessions.json` 或读 sessions_schema.json
- 多 sessions 并存时无汇总视图 (本会话实测 5 个 completed 同 owner 显示在 list 中但用户不易区分"我自己 vs 历史")

后果:
- 用户感知不到"我现在到底在哪个 session 里"
- 调试时难定位"owner X 是哪个 tool/bash 调用产生的"
- ship-done 的"5 个 orphaned"提示缺乏上下文 (哪个?为什么?何时产生?)

依据:rddf-session SKILL.md L266-278 list 输出格式 (已有但信息密度低)。

## What Changes

**In Scope**:

- **In Scope**:
- 新增 `skill_use("rddf-session", "status")` 子命令: 输出表格 (含 session_id / kind / owner / sub_phase / state / started_at / last_heartbeat / age_min / changes_attached)
- 输出当前 active session 的 "BINDING_LINES" (类似 `guide` 推荐器): "📍 你在 rds_xxx (stage_ship, parent=rds_yyy, 处理中 change: foo)"
- 输出总览 (table): active / completed / orphaned / abandoned 计数 + 各自的最新 1 条
- 集成到 `guide` 推荐器扫描: 检测到有 active session 时,在主菜单上方显示 "💡 Active session: rds_xxx (kind=stage_ship)"
- SKILL.md 增加 status 子命令章节
- **Out Scope**:
- 不修改现有 `list` / `show` / `current` 子命令 (向后兼容)
- 不修改 schema (status 是只读视图)

### 关键场景

- GIVEN `rddf-session status`,WHEN 调用,THEN 输出包含表格 + 当前 binding + 计数总览
- GIVEN `guide` 在 active session 存在时被调用,WHEN 扫描完成,THEN 推荐菜单上方显示 "📍 Active: rds_xxx (kind=stage_ship, started 5min ago)"
- GIVEN 没有 active session,WHEN `rddf-session status`,THEN 输出 "(no active session)" 并推荐最近 archived

**Out of Scope**:

- design 阶段不生成 tasks.md / design.md / specs (留在 plan fill)
- 不修改 ADR-0003 (另起 ADR 记录本次职责再分配)


## Capabilities

- `design-proposal-creation`: design 审批批准即创建完整 openspec change
- `design-content-review`: 两层内容审查 (improvements 5 段 + openspec validate), warning / strict 双模式


## Impact

- **受影响文件**: `skills/guide-design/SKILL.md` + 4 个 scripts, `skills/guide-plan/scripts/plan_intake.sh`, `docs/adr/ADR-0025-*.md` (新增)
- **兼容性**: `SKIP_DESIGN_HANDOFF=yes` 存量路径行为不变
- **硬约束**: 批准动作幂等; env-var 传参 (Oracle C1)


## Acceptance

- [ ] `skill_use("rddf-session", "status")` 输出含表格 + binding + 计数
- [ ] `guide` 在 active session 存在时显示 binding line
- [ ] 只读操作,不修改 sessions.json
- [ ] 单元测试 + bats 集成测试通过
- [ ] SKILL.md 增加 status 子命令文档

