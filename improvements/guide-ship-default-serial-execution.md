# guide-ship-default-serial-execution

**优先级**: P1 | **来源**: Session 复盘限流/配额问题 + 用户决策 2026-08-04
**阶段**: v2.1 | **分类**: core-impl
**类型**: refactor

## 架构依据

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

## 范围

- **In Scope**:
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

## 关键场景

- **S1** GIVEN 默认执行模式, WHEN 用户 `skill_use("guide-ship")` 无 flag, THEN wave 内独立 changes 顺序执行，并发数 = 1，输出 `🚀 Wave N sequentially`
- **S2** GIVEN serial 默认 + 多独立 changes, WHEN 用户 `skill_use("guide-ship --parallel")`, THEN 走 `max_concurrent=3` 节流并行，输出 `🚀 Wave N parallel (3 concurrent)`
- **S3** GIVEN serial 默认, WHEN 用户设置 `RDD_SHIP_PARALLEL=yes`, THEN 与 `--parallel` 等价（CLI flag 优先级 > env var）
- **S4** GIVEN parallel mode + 5+ 独立 changes, WHEN `--parallel --max-concurrent=5` flag, THEN 实际并发 = 5（兼容现有 max_concurrent 标志）
- **S5** GIVEN parallel mode + 任务失败（disk full / git lock / test regression）, WHEN 任务失败, THEN 输出 warning + 保持 exit code ≠ 0，**不**自动降级到 serial
- **S6** GIVEN serial mode + `--max-concurrent=5` flag, WHEN 任何 serial 执行, THEN 输出 warning `⚠ --max-concurrent ignored in serial mode` + 仍按 1 并发执行

## 技术约束

- **MUST**: 默认 execution mode = serial（env var 缺失 + flag 缺失）
- **MUST**: `--parallel` flag + `RDD_SHIP_PARALLEL=yes` env var 作为唯一 opt-in 路径
- **MUST**: CLI flag 优先级 > env var
- **MUST**: `--max-concurrent=N` 在 parallel-mode 下生效，serial-mode 下 warning + 忽略
- **MUST**: 复用现有 `skills/_lib/parallel_throttle.sh`（不引入新依赖）
- **MUST**: serial-mode 复用现有 `skills/_lib/parallel_executor.py::execute_change` 兼容逻辑（但默认走 serial 路径，stub echo 替换为真实调用 `guide-ship` Phase 2 execute 子流程）
- **MUST NOT**: 改 `execute/SKILL.md`、`loop_engine.py`、`deps/SKILL.md` 的 `run_in_background=false` 默认
- **MUST NOT**: 实现 parallel → serial 自动 fallback
- **MUST NOT**: 改变 `parallel_group` 数据模型
- **SHOULD**: serial-mode 提供单行 per-change 完成进度（可预测输出格式）
- **SHOULD**: 5 个 bats 测试覆盖 S1-S5（可加 S6 作为边角验证）

## 验收标准

- `bats tests/integration/test_guide_ship_execution_mode.bats` 5 个核心测试全部通过
  - **S1 测试**: 默认无 flag → serial 模式，1 个并发，stdout 含 `sequentially`
  - **S2 测试**: `--parallel` → parallel 模式，3 个并发，stdout 含 `parallel (3 concurrent)`
  - **S3 测试**: `RDD_SHIP_PARALLEL=yes` → 等价 `--parallel`（env var 生效）
  - **S4 测试**: `--parallel --max-concurrent=5` → 实际并发 = 5
  - **S5 测试**: parallel-mode 注入失败 → exit code ≠ 0，**不**降级到 serial
- 现有 `tests/integration/test_task_parallel_throttle.bats` 仍通过（兼容性回归保护）
- 现有 `bats tests/smoke.bats` 仍通过（不破坏冒烟测试）
- `skills/guide-ship/SKILL.md` 新增 `Execution Mode` 章节，列出 `--parallel` flag + `RDD_SHIP_PARALLEL=yes` env var + `--max-concurrent=N` 兼容性说明
- `skills/_lib/ship_execution_mode.sh` 公开 3 个函数：`parse_execution_mode()` / `execute_wave_serial()` / `execute_wave_parallel()`
- 默认执行（无 flag）下，并发数精确为 1，无后台任务残留（`jobs -l` 验证）
