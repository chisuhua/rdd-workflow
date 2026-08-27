# plan-batch-fill-tool

**优先级**: P1 | **来源**: 2026-08-27 ship audit (9 个 design-pre-created change 时, AI agent 创建 tmp_batch_fill.py 手写批量逻辑 fill 9 个 change, 应提供原生工具)
**阶段**: phase-2 | **分类**: governance
**类型**: improvement

**主题**: 2026-08-27 文档与代码一致性审计后续修复

## 架构依据

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

## 范围

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

- MUST: 接受 change name list 作为参数 (`--changes <c1,c2,...>` 或 stdin)
- MUST: 复用 `generate_full_proposal.py` 的 D2 映射逻辑(同格式 design.md)
- MUST: atomic write iteration.json
- MUST: idempotent — 跳过已 fill 的 change
- SHOULD: 提供 `--dry-run` 模式

## Impact

- MUST NOT: 修改 `_lib/iteration/store.py` schema
- MUST NOT: 修改 `generate_full_proposal.py` (复用, 不修改)

## Acceptance

- [ ] `rddf plan batch-fill` CLI 命令可用 (或 `bash skills/guide-plan/scripts/plan_batch_fill.sh`)
- [ ] 对 9 个 design-pre-created change, 1 次调用完成 fill
- [ ] iteration.json 自动更新 status (planned → proposed)
- [ ] 8 个 unit test 全部通过
- [ ] 与现有 `plan_intake.sh` 兼容 (Phase 0.5 不冲突)
- [ ] `bash tests/scripts/report_regression.sh` 不增加新 failure