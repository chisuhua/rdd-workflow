# add-rddf-session-auto-archive-on-entry

## Why

sessions.json 累积问题实证:
- 2026-08-02 本会话一次性发现 19 个 orphaned/abandoned 会话,需手动调 `archive-history --keep=5` 清理 31 个
- 31 个 archived 中 16 个 `user-abandoned` (用户主动关闭但未自动归档)
- 3 个 `heartbeat-timeout` 已被自动 orphaned,但仍未归档,继续占用 sessions.json 容量
- 现状:`archive-history` 仅靠用户主动调用 → 容易遗忘 → sessions.json 越长越大

依据:ADR-0017 §4 retention policy (有,但无自动触发)。

## What Changes

**In Scope**:

- **In Scope**:
- `rddf_session_hook_entry` 入口最末尾自动调 `coord.archive_history(keep=10)` (best-effort,`try/except` 不阻塞主流程)
- `rddf_session_hook_close` 关闭时同样自动调一次 (双保险)
- 默认 `keep=10` 可被 `RDDF_AUTO_ARCHIVE_KEEP` env var 覆盖 (0 表示禁用)
- 文档: SKILL.md 增加"自动归档"章节
- 单元测试: 入口 hook 触发时 archive-history 被调用,且不影响主流程
- **Out Scope**:
- 不修改 archive-history 命令本身
- 不修改 sessions.json schema
- 不引入 cron / 后台任务调度 (保持纯 hook 触发)

### 关键场景

- GIVEN sessions.json 含 15 个 old terminal sessions + 5 个 active,WHEN `rddf_session_hook_entry` 被调用,THEN 调用后 sessions.json ≤10 个 old + active 不变
- GIVEN `RDDF_AUTO_ARCHIVE_KEEP=0`,WHEN entry 被调用,THEN 不触发自动归档 (用户显式禁用)
- GIVEN archive-history 失败 (e.g., disk full,permission),WHEN entry 被调用,THEN 主流程不阻塞,stderr 打印警告

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

- [ ] entry hook 触发后 sessions.json 减少 (历史 sessions 归档到 sessions.archive.json)
- [ ] `RDDF_AUTO_ARCHIVE_KEEP=0` 时 hooks 不触发自动归档
- [ ] archive 失败时 hooks 主流程不抛异常
- [ ] 单元测试 + bats 集成测试通过
- [ ] SKILL.md 增加"自动归档"章节,说明 keep 默认值与覆盖方式

