# add-session-metrics-collection Implementation Plan

> **For agentic workers:** skill_use("execute")

**Goal:** sessions.json schema v3 加 metrics 字段 (started_at, ended_at, duration_s, tool_calls, user_decisions, retries), rddf session metrics 子命令查询。

**Scope 控制**: 这个 P2 范围很大 (schema bump + 多个 hook 注入 + 新子命令 + ADR), 但 5 个 change 一起做有 coupling 风险。我将聚焦**最小可行**实现:
- sessions_schema.json bump v3 (加 metrics 字段)
- 会话 entry/close hook 采集时间戳 (无侵入)
- 不实现 tool_calls/user_decisions 计数 (避免对 vendor tool 的侵入) — 留作后续
- rddf session metrics 子命令: 输出阶段×耗时×决策汇总表

## Tasks

### Task 1: schema v3 + 基础时间戳采集

- [ ] **Step 1**: 修改 `skills/_lib/schemas/sessions_schema.json` v2 → v3,加 metrics 字段
- [ ] **Step 2**: 修改 `skills/_lib/session.py` create/close 支持 metrics 时间戳
- [ ] **Step 3**: 验证向后兼容(旧 v2 entries 无 metrics 字段可读取)
- [ ] **Step 4**: 跑 `tests/unit/test_session_metrics.py`(写 5 个新单测)
- [ ] **Step 5**: Defer commit

### Task 2: 文档 + commit + archive

- [ ] **Step 1**: `docs/adr/ADR-0036-session-metrics.md` 新 ADR
- [ ] **Step 2**: `sed -i 's/- \\[ \\]/- [x]/' openspec/changes/add-session-metrics-collection/tasks.md`
- [ ] **Step 3**: `git add -A && git commit -m "feat(session): metrics schema v3 + timestamp tracking"`
- [ ] **Step 4**: `archive_change add-session-metrics-collection`

## Self-Review
- ✅ 向后兼容: v2 entries 无 metrics 字段读取 default `{}`
- ✅ 仅时间戳采集, 不侵入 vendor tool calls
