# add-workflow-synthesizer

**Priority**: P0
**Phase**: v2.1
**Status**: skeleton

## Why

## 架构依据
- 核心诉求：guide 运行时知道哪些阶段已完成/待处理，建议 resume 还是 restart
- 只读模块，不写 sessions.json
- 与 add-guide-dashboard 互补：synthesizer 提供数据，dashboard 提供展示

## 范围
- **In Scope**:
  - skills/_lib/workflow_synthesizer.py：读取 sessions.json + handoff + iteration + git 状态
  - 结构化推荐：WorkflowRecommendation + PhaseStatus dataclass
  - 推荐逻辑：resume/restart/start-arch/all-done 决策树
  - scan-state.sh 集成 synthesizer 输出到 CONTEXT_LINES
- **Out Scope**:
  - 不修改 sessions_schema.json（只读）
  - 不自动执行推荐（仅建议，用户确认）

## 验收标准
- synthesizer 输出 WorkflowRecommendation with 置信度
- 10 个测试覆盖每一条推荐路径

## What Changes

- TODO: define specific changes during fill phase

## Impact

- Affected specs: TBD
- Affected code: TBD
