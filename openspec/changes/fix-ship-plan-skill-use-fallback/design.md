## Context

`skills/guide-ship/scripts/ship_plan.sh`（P1-14 提取自 guide-ship.md Phase 1）在 `generate_implementation_plan()` 内调用 `skill_use "rdd-workflow-writing-plans"` 生成实施计划。`skill_use` 是 AI 平台函数，在 bash 子进程执行时不存在，导致 `if ! skill_use ...` 恒为 true → 恒失败。

## Goals / Non-Goals

**Goals:**
- bash 环境无 `skill_use` 时，输出"计划生成需由编排者调用 skill_use(\"rdd-workflow-writing-plans\")"指引而非"技能未找到"错误
- 降级时不返回非零退出码，**不中断** worktree 创建流程（当前 `return 1` 使 run_ship_phase1 失败）
- 交互式 AI 环境（skill_use 可用）计划生成行为保持不变

**Non-Goals:**
- 不修改 `rdd-workflow-writing-plans` 技能本身
- 不修改 execute 技能
- 不提供 CLI 版计划生成器（超出本提案范围）

## Decisions

1. **环境能力检测前置**：用 `command -v skill_use >/dev/null 2>&1` 判断环境能力，而非依赖调用失败后兜底——避免把"命令不存在"误判为"技能未找到"。
2. **降级不中断**：无 `skill_use` 时输出明确指引（计划文件缺失，需编排者按 rdd-workflow-writing-plans 规范生成 `.rddf/plans/<name>.md`），返回可辨识状态码（非 1），`run_ship_phase1` 继续执行。
3. **行为保持**：`skill_use` 可用时直接调用技能生成，交互式 AI 环境行为不变。
4. **测试覆盖**：新增降级场景测试——模拟 bash 子进程（无 skill_use）调用 `run_ship_phase1`，断言输出降级指引且退出码 0。

## Risks / Trade-offs

- **可感知降级**：worktree 创建成功 + 计划生成降级时，返回非 1 状态码让编排者可感知需手动补计划，而非静默失败。
- **回归验证**：现有 `tests/integration/test_ship_plan_extraction.bats` 全部通过（含新增降级用例）。
- **低风险**：改动仅为 skill_use 调用的能力检测 + 降级分支，不触碰 worktree 创建 / COMMIT GATE / 执行模式检测逻辑。
