# 实施计划: v3-scheduled-triggers

> 对应 ADR-0009: Scheduled Triggers (v2.1 候选)
> 基于: tasks.md 中的 7 组 21 任务
> 实施位置: `.rddf/wt/v3-scheduled-triggers/`

## 概览

| 阶段 | 任务组 | 工作量 | 风险 |
|------|--------|--------|------|
| 触发器基础设施 | 1.1-1.4 | 4 任务 | 低 |
| Cron 调度 | 2.1-2.3 | 3 任务 | 中（线程并发） |
| 事件驱动 | 3.1-3.4 | 4 任务 | 中（webhook 线程） |
| 去重与速率限制 | 4.1-4.3 | 3 任务 | 低 |
| LoopEngine 集成 | 5.1-5.4 | 4 任务 | 高（核心引擎） |
| 配置与安全 | 6.1-6.4 | 4 任务 | 低 |
| 测试 | 7.1-7.5 | 5 任务 | 中 |

## 实施策略

**按依赖顺序**：1 → 2 → 3 → 4 → 5 → 6 → 7

注意：任务 5（LoopEngine 集成）必须在 1-4 完成后才能开始。

## 关键文件

| 文件 | 操作 | 来源任务 |
|------|------|---------|
| `skills/_lib/triggers.py` | CREATE | 1.1 |
| `skills/_lib/trigger_registry.py` | CREATE | 1.2 |
| `skills/_lib/schemas/trigger_schema.json` | CREATE | 1.3 |
| `requirements.txt` | MODIFY | 1.4 |
| `skills/_lib/schedulers/cron_scheduler.py` | CREATE | 2.1-2.3 |
| `skills/_lib/schedulers/fs_watcher.py` | CREATE | 3.1 |
| `skills/_lib/schedulers/git_hook.py` | CREATE | 3.2 |
| `skills/_lib/schedulers/webhook_receiver.py` | CREATE | 3.3 |
| `skills/_lib/event_queue.py` | CREATE | 3.4 |
| `skills/_lib/rate_limiter.py` | CREATE | 4.2 |
| `skills/loop_engine.py` | MODIFY | 5.1, 5.4 |
| `skills/_lib/detectors.py` | MODIFY | 5.2 |
| `skills/_lib/config.py` | MODIFY | 6.2 |
| `config.yaml` | MODIFY | 6.1 |
| `tests/unit/test_triggers.py` | CREATE | 7.1 |
| `tests/unit/test_cron_scheduler.py` | CREATE | 7.2 |
| `tests/unit/test_rate_limiter.py` | CREATE | 7.3 |
| `tests/integration/test_trigger_loop_integration.py` | CREATE | 7.4 |
| `tests/unit/test_detectors.py` | MODIFY | 7.5 |

## 实施步骤

按 tasks.md 的顺序逐项实施，每个任务完成后立即 commit。

## 验收标准

1. `TriggerManager` 支持 register/unregister/deduplicate
2. cron 触发器按表达式定时调用 LoopEngine
3. 文件监听器（30s 轮询）触发 LoopEngine
4. webhook 接收器（端口 9090）触发 LoopEngine
5. 速率限制（token bucket）阻止过度触发
6. LoopEngine 集成不破坏现有检测器
7. `--trigger-off` 禁用所有触发器
8. 崩溃恢复持久化
9. 所有 unit + integration 测试通过