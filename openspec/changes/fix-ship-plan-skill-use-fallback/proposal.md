## Why

会话复盘 2026-07-31 实测：`run_ship_phase1` 对 3 个 change 调用后全部输出 `❌ 实施计划生成失败 / rdd-workflow-writing-plans 技能未找到`，worktree 创建成功但计划文件缺失。

根因：`skill_use` 是 **AI 平台函数**（OpenCode/Claude Code 等提供），在 bash 子进程执行时**不存在**（command not found），`if ! skill_use ...` 恒为 true → 恒失败。后果：AI 编排环境（bash 调用辅助脚本）无法自动生成计划，必须由编排者手动加载技能生成，破坏了 guide-ship 的自动化流程。

## What Changes

- `skills/guide-ship/scripts/ship_plan.sh` — 检测 bash 环境无 `skill_use` 时的降级处理（输出指引而非报错退出）。
- `skills/guide-ship/SKILL.md` Phase 1 — 补充说明：AI 编排环境计划生成由编排者完成。
- `tests/integration/test_ship_plan_extraction.bats` — 补充降级场景测试。

## Capabilities

### New Capabilities
- `ship-plan-bash-degradation`: bash 子进程无 `skill_use` 时输出降级指引而非"技能未找到"错误，且不中断 worktree 创建流程

### Modified Capabilities
<!-- 无 spec 级行为变更 -->

## Impact

**In Scope:**
- `skills/guide-ship/scripts/ship_plan.sh::generate_implementation_plan()` — `command -v skill_use` 环境能力检测 + 降级指引输出
- `skills/guide-ship/SKILL.md` Phase 1 — AI 编排环境计划生成说明
- `tests/integration/test_ship_plan_extraction.bats` — 降级场景测试

**Out of Scope:**
- 不修改 `rdd-workflow-writing-plans` 技能本身
- 不修改 execute 技能
- 不提供 CLI 版计划生成器（超出本提案范围，可后续独立提案）
