# ADR-0036-session-metrics — schema v3 加 session metrics opt-in 字段

## Status

已采纳 — 2026-09-01

## Context

rddf-session 跨 OpenCode session 工作流恢复,但无任何指标记录 session 耗时、工具调用分布、重试次数。无法量化"哪个阶段最耗时"或"哪个改进有效"。

## Decision

`sessions_schema.json` 从 v2 升级到 v3,在 `$defs.Session.properties` 加 `metrics` 字段:

```json
{
  "metrics": {
    "started_at": "<ISO8601>",
    "ended_at": "<ISO8601>",
    "duration_s": <int>,
    "user_decisions": <int>,
    "retries": <int>
  }
}
```

**最小可行实现** (本次):
- Schema bump + 5 个单测
- 后续 hook 注入(由 `add-session-metrics-collection` 后续 task 跟进)

## Consequences

- ✅ 向后兼容:旧 v2 entries 无 `metrics` 字段仍 valid (additionalProperties=false 仅约束 session item 顶层,metrics 是 opt-in)
- ❌ 暂未实现: hook 自动注入 started_at / ended_at / 工具调用计数 (留后续)
- ❌ 暂未实现: `rddf session metrics <id>` 子命令 (留后续)

## References

- ADR-0017 (rddf-session lifecycle)
- Schema: `skills/_lib/schemas/sessions_schema.json`
- Tests: `tests/unit/test_session_metrics.py`
