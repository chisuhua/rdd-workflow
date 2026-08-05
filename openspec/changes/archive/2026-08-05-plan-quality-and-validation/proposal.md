# plan-quality-and-validation

## Why

本次会话中两个 plan 出现预期不符,执行阶段才暴露问题:
- `execute-gate-unified-regression`: plan 假设脚本只定义函数,实际测试要求直接 bash 执行 → 需补加 `BASH_SOURCE[0]` guard
- `python-failures-baseline`: plan Step 4 期望 "17 passed",实际 "16 passed + 1 cross-stage conflict" → 需 `RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes`

plan 生成器缺乏 dry-run 验证和发布前检查清单,导致执行阶段返工。

## What Changes

**In Scope**:

- plan 生成器加入 dry-run 步骤:用临时 fixture 验证 step 3 代码 + step 4 断言可行性
- `skills/rdd-workflow-writing-plans/SKILL.md` 加入发布前检查清单:
- Step 5 脚本能否直接 bash 执行(需 `BASH_SOURCE[0]` guard)
- expected 数字是否基于实际测试运行(非估算)
- 涉及跨 stage 测试的 plan 加入 `RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes` env var
- worktree 源不在 sys.path 的 LSP 噪音容忍
- 脚本型 plan 模板自动生成 direct-execution guard
- 重写整个 rdd-workflow-writing-plans 技能
- 修改 execute 技能

**Out of Scope**:

- (TBD)

## Capabilities

- (TBD)

## Impact

- (TBD)

## Acceptance

- [ ] (TBD — 验收标准 from improvements 头部未提供)

