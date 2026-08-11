# fix-ship-plan-skill-use-fallback

**优先级**: P1 | **来源**: 会话复盘 2026-07-31 — 3 次 worktree 创建后实施计划生成全部失败
**阶段**: v2.1 | **分类**: core-impl
**类型**: fix

## 架构依据

- `skills/guide-ship/scripts/ship_plan.sh`（P1-14 提取自 guide-ship.md Phase 1）在 `generate_implementation_plan()` 内调用 `skill_use "rdd-workflow-writing-plans"` 生成实施计划
- 会话复盘 2026-07-31 实测：`run_ship_phase1` 对 3 个 change 调用后全部输出 `❌ 实施计划生成失败 / rdd-workflow-writing-plans 技能未找到`，worktree 创建成功但计划文件缺失
- 根因：`skill_use` 是 **AI 平台函数**（OpenCode/Claude Code 等提供），在 bash 子进程执行时**不存在**（command not found），`if ! skill_use ...` 恒为 true → 恒失败
- 后果：AI 编排环境（bash 调用辅助脚本）无法自动生成计划，必须由编排者手动加载技能生成，破坏了 guide-ship 的自动化流程

## 范围

- **In Scope**:
  - `skills/guide-ship/scripts/ship_plan.sh` — 检测 bash 环境无 `skill_use` 时的降级处理（输出指引而非报错退出）
  - `skills/guide-ship/SKILL.md` Phase 1 — 补充说明：AI 编排环境计划生成由编排者完成
  - `tests/integration/test_ship_plan_extraction.bats` — 补充降级场景测试
- **Out Scope**:
  - 不修改 `rdd-workflow-writing-plans` 技能本身
  - 不修改 execute 技能
  - 不提供 CLI 版计划生成器（超出本提案范围，可后续独立提案）

## 关键场景

- GIVEN bash 环境无 `skill_use` 命令（AI 编排子进程）, WHEN `run_ship_phase1` 执行, THEN 输出"计划生成需由编排者调用 skill_use(\"rdd-workflow-writing-plans\")"指引而非"技能未找到"错误, 且**不中断** worktree 创建流程
- GIVEN 交互式 AI 环境有 `skill_use`（SKILL.md 内联执行）, WHEN 计划生成, THEN 保持现有行为（直接调用技能生成）
- GIVEN worktree 创建成功但计划生成降级, WHEN guide-ship Phase 1 继续, THEN 返回可辨识状态码（非 1），编排者可感知需手动补计划

## 技术约束

- MUST 检测方式：`command -v skill_use >/dev/null 2>&1` 判断环境能力，而非依赖调用失败
- MUST 降级时不返回非零退出码导致 Phase 1 中断（当前 `return 1` 使 run_ship_phase1 失败）
- MUST 降级时输出明确指引：计划文件缺失，需编排者按 rdd-workflow-writing-plans 规范生成 `.rddf/plans/<name>.md`
- MUST NOT 修改 worktree 创建 / COMMIT GATE / 执行模式检测逻辑
- SHOULD 在计划文件缺失时（后续校验）给出与降级一致的提示

## 验收标准

- bash 子进程调用 `run_ship_phase1` 时不再输出"技能未找到"错误，改为降级指引
- worktree 创建成功 + 计划生成降级时，`run_ship_phase1` 退出码 0（可感知降级而非失败）
- AI 交互环境（skill_use 可用）计划生成行为不变
- 现有 `tests/integration/test_ship_plan_extraction.bats` 全部通过（含新增降级用例）
