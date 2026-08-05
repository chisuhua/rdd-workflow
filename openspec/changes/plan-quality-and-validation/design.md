# plan-quality-and-validation — Design

## Context

本次会话中两个 plan 出现预期不符,执行阶段才暴露问题:
- `execute-gate-unified-regression`: plan 假设脚本只定义函数,实际测试要求直接 bash 执行 → 需补加 `BASH_SOURCE[0]` guard
- `python-failures-baseline`: plan Step 4 期望 "17 passed",实际 "16 passed + 1 cross-stage conflict" → 需 `RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes`

plan 生成器缺乏 dry-run 验证和发布前检查清单,导致执行阶段返工。

## Goals / Non-Goals

**Goals:**

- plan 生成器加入 dry-run 步骤:用临时 fixture 验证 step 3 代码 + step 4 断言可行性
- `skills/rdd-workflow-writing-plans/SKILL.md` 加入发布前检查清单:
  - Step 5 脚本能否直接 bash 执行(需 `BASH_SOURCE[0]` guard)
  - expected 数字是否基于实际测试运行(非估算)
  - 涉及跨 stage 测试的 plan 加入 `RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes` env var
  - worktree 源不在 sys.path 的 LSP 噪音容忍
- 脚本型 plan 模板自动生成 direct-execution guard

**Non-Goals:**

- 重写整个 rdd-workflow-writing-plans 技能
- 修改 execute 技能

## Decisions

### Dry-run 验证

plan 生成器在输出前执行轻量级验证:
```python
# 临时 fixture 中验证 step 3 代码片段语法
import ast
ast.parse(step3_code)

# 对 expected 数字,运行现有 fixture 估算(collect-only)
pytest existing_fixtures --collect-only -q | wc -l
```

### 检查清单(写入 SKILL.md)

```markdown

## Risks / Trade-offs

- **正向**: plan 准确性提升,减少执行阶段返工
- **正向**: expected 数字可靠,execute 阶段预期明确
- **风险**: dry-run 增加 plan 生成时间(预期 +10-30 秒)
- **兼容性**: 不破坏现有 plan 格式,仅增强生成逻辑

## Migration Plan

1. 本提案在主仓库实施,通过 guide-plan + guide-ship 工作流
2. 执行完成后 openspec archive 归档到 openspec/changes/archive/YYYY-MM-DD-plan-quality-and-validation/
3. 不涉及运行时数据迁移(纯 workflow 增强)

## Open Questions

无 — 提案中所有关键场景(S1-S6 等)已定义清晰。
