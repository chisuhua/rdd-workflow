# plan-batch-fill-tool

## Why

2026-08-27 plan 阶段, AI agent 为 9 个 design-pre-created change 填充 design.md + tasks.md 时, 写了临时 Python 脚本 `tmp_batch_fill.py`:
- 解析每个 change 的 proposal.md ## Why / ## What Changes / ## Capabilities / ## Impact / ## Acceptance
- 生成 design.md (Context / Goals / Decisions / Risks)
- 生成 tasks.md (从 Acceptance checkboxes 生成 Implementation Tasks)
- 批量更新 iteration.json (status: planned → proposed)

后果:
- 临时脚本被手动删除 (无持久化价值)
- AI agent 重复实现批量逻辑的风险高
- 9 个 change × 5 个字段批量处理时间 ~10 秒, 应 < 1 秒

期望行为: `rddf plan batch-fill <list>` 原生命令, 标准 batch 处理 design-pre-created changes。

## What Changes

**In Scope**:

- 新建 `skills/guide-plan/scripts/plan_batch_fill.py`: 批量 fill 核心 (Python)
- 新建 `skills/guide-plan/scripts/plan_batch_fill.sh`: bash wrapper (env-var passing)
- 新建 `tests/unit/test_plan_batch_fill.py`: 8 个 unit test
- 单 change fill
- 多 change 批量 fill
- proposal 缺 ## Acceptance 时降级处理
- iteration.json status planned → proposed
- atomic write 保护 iteration.json
- 跳过已 fill 的 change (idempotent)
- 错误处理 (invalid change name)
- 集成测试 (与 plan_intake.sh 协调)

**Out of Scope**:

- 修改 fill 算法 (沿用 generate_full_proposal.py 的 D2 映射)
- 修改 iteration schema
- 新增 fill wizard (CLI 交互式)

## Capabilities

- (no items specified)

## Impact

- (no items specified)

## Acceptance

- [ ] (TBD — 验收标准 from .rddf/improvements 头部未提供)

