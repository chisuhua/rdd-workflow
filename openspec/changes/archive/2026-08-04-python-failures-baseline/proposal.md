# python-failures-baseline

## Why

- 实测：`python3 -m pytest tests/unit/ tests/integration/ -q` 存在存量稳定失败：
  - 9 个 rddf-session 集成测试：schema 不匹配（测试构造 `status`/`created_at`，schema 要求 `state`/`started_at`；`goal` 含 `task`/`workflow` 键不在 schema 中）——稳定失败，属存量漂移
  - `test_query_10k_events_under_100ms`：时序抖动（103.3ms vs 100ms 阈值）——偶发
- `add-known-failures-baseline` 已为 bats 建立 KNOWN_FAILURES.txt，但 Python 失败未纳入任何基线，每个 change 的全量 pytest 仍被存量失败干扰回归判定

## What Changes

**In Scope**:

- 将 Python 稳定失败纳入基线机制：扩展 `tests/KNOWN_FAILURES.txt`（或新增 pytest marker/配置文件）标记已知失败，report 时区分增量
- 修复 rddf-session 测试的 schema 漂移（`status`→`state`、`created_at`→`started_at`、`goal` 键对齐）——这是真正的存量 bug，修优于屏蔽
- 对时序敏感断言增加容差或改为非计时断言
- 1-2 个测试锁定修复

### 关键场景

- **GIVEN** 开发者运行 `python3 -m pytest tests/unit/ tests/integration/ -q`
  **WHEN** 仓库存在已知存量失败
  **THEN** 报告明确区分"已知存量失败"与"本次新增失败"，新增失败才阻断

**Out of Scope**:

- 不改变 event_log 的性能实现
- 不为存量失败引入 `@pytest.mark.skip` 永久屏蔽

## Capabilities

- 修复 schema 漂移时保持与 sessions_schema.json v1 字段一致（`state`/`started_at`/`last_heartbeat`）

## Impact

- 修复 schema 漂移时保持与 sessions_schema.json v1 字段一致（`state`/`started_at`/`last_heartbeat`）

## Acceptance

- rddf-session 9 个稳定失败修复后 GREEN（或纳入明确基线）
- 时序断言不再偶发失败
- 新增失败可被报告机制识别

