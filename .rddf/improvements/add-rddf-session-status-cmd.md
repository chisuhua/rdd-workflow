# add-rddf-session-status-cmd

**优先级**: P2 | **来源**: 2026-08-02 ship 复盘
**阶段**: v2.1 | **分类**: observability
**类型**: feature

## 架构依据

rddf-session 当前用户可见性差:
- 用户只在 entry hook 输出 1 行 session ID (`rds_5219d1402217 (stage_ship, parent=...)`)
- 想看完整状态必须手动 `cat .rddf/state/sessions.json` 或读 sessions_schema.json
- 多 sessions 并存时无汇总视图 (本会话实测 5 个 completed 同 owner 显示在 list 中但用户不易区分"我自己 vs 历史")

后果:
- 用户感知不到"我现在到底在哪个 session 里"
- 调试时难定位"owner X 是哪个 tool/bash 调用产生的"
- ship-done 的"5 个 orphaned"提示缺乏上下文 (哪个?为什么?何时产生?)

依据:rddf-session SKILL.md L266-278 list 输出格式 (已有但信息密度低)。

## 范围

- **In Scope**:
  - 新增 `skill_use("rddf-session", "status")` 子命令: 输出表格 (含 session_id / kind / owner / sub_phase / state / started_at / last_heartbeat / age_min / changes_attached)
  - 输出当前 active session 的 "BINDING_LINES" (类似 `guide` 推荐器): "📍 你在 rds_xxx (stage_ship, parent=rds_yyy, 处理中 change: foo)"
  - 输出总览 (table): active / completed / orphaned / abandoned 计数 + 各自的最新 1 条
  - 集成到 `guide` 推荐器扫描: 检测到有 active session 时,在主菜单上方显示 "💡 Active session: rds_xxx (kind=stage_ship)"
  - SKILL.md 增加 status 子命令章节
- **Out Scope**:
  - 不修改现有 `list` / `show` / `current` 子命令 (向后兼容)
  - 不修改 schema (status 是只读视图)

## 关键场景

- GIVEN `rddf-session status`,WHEN 调用,THEN 输出包含表格 + 当前 binding + 计数总览
- GIVEN `guide` 在 active session 存在时被调用,WHEN 扫描完成,THEN 推荐菜单上方显示 "📍 Active: rds_xxx (kind=stage_ship, started 5min ago)"
- GIVEN 没有 active session,WHEN `rddf-session status`,THEN 输出 "(no active session)" 并推荐最近 archived

## 技术约束

- status 输出宽度 ≤100 字符 (适配终端)
- BINDING_LINES 与 `guide` 推荐器现有逻辑共存,不破坏现有输出格式
- status 永不修改 sessions.json (纯读视图)

## 验收标准

- [ ] `skill_use("rddf-session", "status")` 输出含表格 + binding + 计数
- [ ] `guide` 在 active session 存在时显示 binding line
- [ ] 只读操作,不修改 sessions.json
- [ ] 单元测试 + bats 集成测试通过
- [ ] SKILL.md 增加 status 子命令文档