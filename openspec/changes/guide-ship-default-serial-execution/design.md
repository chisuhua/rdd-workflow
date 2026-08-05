# guide-ship-default-serial-execution — Design

## Context

**复盘证据**:
- 8 个 deep agent 同时发起导致 volcengine-plan 限流 + kimi-code 配额耗尽（task-parallel-throttle 复盘 2026-07-21），6/8 agent 需 2-3 次重试完成；总延迟从线性变超线性（约 20 分钟 vs 预期 10 分钟）
- `task-parallel-throttle` 是**治标**方案（节流限流），但根本问题是默认行为应为串行
- 用户当前心智模型：能并行的也走串行；并行是 opt-in 操作

**现有实施盘点**（commits `ddf4b9d` `6296169` 已 merge 到 master）:
- `skills/_lib/parallel_throttle.sh` — `throttle_acquire/release/drain` 节流原语 ✅
- `skills/_lib/ship_parallel.sh` — 只解析 `--max-concurrent`，**无实际执行逻辑** ⚠️
- `skills/_lib/parallel_executor.py` — ThreadPoolExecutor 入口，但 `execute_change()` 是 echo stub，**没有任何代码调用它** ⚠️
- `guide-ship/SKILL.md` 主流程**未集成**任何并行执行器

**关键缺口**: 并行零件存在但未组装。`guide-ship` 主流程下 wave 内独立 changes 实际默认行为取决于 `task()` 调用点的 `run_in_background` 标志，缺乏统一执行模式开关。

**决策**: 翻转默认行为 = serial。Opt-in = parallel via `--parallel` flag 或 `RDD_SHIP_PARALLEL=yes` env var。复用现有 `parallel_throttle.sh` 作为 parallel-mode 内部实现，不引入新依赖。

**相关 ADR/提案引用**:
- `improvements/task-parallel-throttle.md` (P1, 2026-07-21, 已合并 `ddf4b9d`) — 节流方案（治标保留为 parallel-mode 内部实现）
- `improvements/parallel-wave-execution.md` (P1, 部分合并 `6296169`) — opt-in `--parallel` 雏形
- `improvements/add-rddf-concurrency-tests.md` (P1, v2.1) — LOCK_NB fail-fast 语义不变
- `improvements/parallel-oracle-review.md` (P1, 2026-07-23) — arch 端不在本提案范围

## Goals / Non-Goals

**Goals:**

- `skills/guide-ship/SKILL.md` 主流程增加 `--parallel` flag + `RDD_SHIP_PARALLEL=yes` env var
  - 新建 `skills/_lib/ship_execution_mode.sh`：`parse_execution_mode()` + `execute_wave_serial()` + `execute_wave_parallel()`
  - `skills/guide-ship/scripts/ship_plan.sh` 调用新 helper（替换原 echo stub 间接路径）
  - `skills/_lib/parallel_executor.py` 重构为兼容层：默认 serial + opt-in 走 ThreadPoolExecutor 包装（保留 `execute_wave_parallel` 入口）
  - 现有 `skills/_lib/parallel_throttle.sh` 保留为 parallel-mode 内部实现
  - 现有 `--max-concurrent=N` 兼容（parallel-mode 下生效，serial-mode 下输出 warning + 忽略）
  - 新建 `tests/integration/test_guide_ship_execution_mode.bats`：默认 / opt-in / env-var / max-concurrent 兼容 / 失败处理 5 个测试
  - `skills/guide-ship/SKILL.md` 新增 `Execution Mode` 章节
- **Out Scope**:
  - 不修改 `execute/SKILL.md` 的 `run_in_background=false` 默认（已是 serial）
  - 不修改 `skills/_lib/loop_engine.py::execute_plan`（已是 for 循环 serial）
  - 不修改 `deps/SKILL.md` 的 `run_in_background=false`（已是 serial）
  - 不实现 parallel → serial 自动降级 fallback
  - 不改 `parallel_group` 数据模型
  - 不动 `parallel-oracle-review` (arch 端)
  - 不引入新的执行引擎或新依赖

**Non-Goals:**

参见提案 Out of Scope 段

## Decisions



## Risks / Trade-offs



## Migration Plan

1. 本提案在主仓库实施,通过 guide-plan + guide-ship 工作流
2. 执行完成后 openspec archive 归档到 openspec/changes/archive/YYYY-MM-DD-guide-ship-default-serial-execution/
3. 不涉及运行时数据迁移(纯 workflow 增强)

## Open Questions

无 — 提案中所有关键场景(S1-S6 等)已定义清晰。
