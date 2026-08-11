# add-rddf-session-auto-archive-on-entry

**优先级**: P1 | **来源**: 2026-08-02 ship 复盘
**阶段**: v2.1 | **分类**: hygiene
**类型**: feature

## 架构依据

sessions.json 累积问题实证:
- 2026-08-02 本会话一次性发现 19 个 orphaned/abandoned 会话,需手动调 `archive-history --keep=5` 清理 31 个
- 31 个 archived 中 16 个 `user-abandoned` (用户主动关闭但未自动归档)
- 3 个 `heartbeat-timeout` 已被自动 orphaned,但仍未归档,继续占用 sessions.json 容量
- 现状:`archive-history` 仅靠用户主动调用 → 容易遗忘 → sessions.json 越长越大

依据:ADR-0017 §4 retention policy (有,但无自动触发)。

## 范围

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

## 关键场景

- GIVEN sessions.json 含 15 个 old terminal sessions + 5 个 active,WHEN `rddf_session_hook_entry` 被调用,THEN 调用后 sessions.json ≤10 个 old + active 不变
- GIVEN `RDDF_AUTO_ARCHIVE_KEEP=0`,WHEN entry 被调用,THEN 不触发自动归档 (用户显式禁用)
- GIVEN archive-history 失败 (e.g., disk full,permission),WHEN entry 被调用,THEN 主流程不阻塞,stderr 打印警告

## 技术约束

- 入口自动归档必须 best-effort,任何异常 swallow (不影响 hooks 主流程)
- 默认 keep=10 与现有 `archive-history --keep=20` 默认值协调:hooks 自动 keep=10,显式命令 keep=20
- **触发阈值修正**: 原 `≥ 15` 在 keep=10 + 2-4 个 active 的常见稳态 (12-14 条) 下永远不触发,sessions.json 长期累积。**改为 `≥ keep + 5`** (默认 15),等价于 `≥ keep*1.5`。**关键**: 触发后 archive-history 已按 keep 切片 (10 terminal + active 保留),稳态 10 + N active,触发频率自然下降 — 避免每次 hook 都重写文件
- 阈值可被 `RDDF_AUTO_ARCHIVE_THRESHOLD` env var 覆盖 (0 表示禁用归档,与 `RDDF_AUTO_ARCHIVE_KEEP=0` 协调)

## 验收标准

- [ ] entry hook 触发后 sessions.json 减少 (历史 sessions 归档到 sessions.archive.json)
- [ ] `RDDF_AUTO_ARCHIVE_KEEP=0` 时 hooks 不触发自动归档
- [ ] archive 失败时 hooks 主流程不抛异常
- [ ] 单元测试 + bats 集成测试通过
- [ ] SKILL.md 增加"自动归档"章节,说明 keep 默认值与覆盖方式