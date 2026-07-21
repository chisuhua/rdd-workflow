# add-workflow-synthesizer

**Priority**: P0
**Phase**: v2.1
**Status**: proposed

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

- **NEW** `skills/_lib/workflow_synthesizer.py` (~340 行): read-only synthesizer with `PhaseStatus` + `WorkflowRecommendation` frozen dataclasses + `synthesize()` entry point + 13-path decision tree mirroring `scan-state.sh::scan_state()` + helpers for unblocked_changes / active_session / orphaned_sessions / worktree task scan / committed change detection. Never-raises contract with fallback recommendation.
- **NEW** `tests/unit/test_workflow_synthesizer.py` (~600 行, 54 tests): covers dataclass shape, all 13 decision paths (parametrized + individual), phase status summary, unblocked_changes filtering/sorting, rddf-session binding, orphaned sessions, never-raises contract, corrupt state resilience, worktree task detection, determinism.
- **MODIFY** `skills/guide/SKILL.md`: integrate Python synthesizer call into the scan logic block with graceful fallback to legacy `scan_state` RECOMMEND/REASON globals. Synthesizer overrides RECOMMEND/REASON when Python available; scan_state baseline preserved on any error.
- **MODIFY** `tests/integration/test_guide_skill.bats`: add 2 new tests asserting (1) synthesizer integration block present + scan_state fallback retained, (2) synthesizer module exists and imports cleanly.

## Impact

- Affected specs: none (read-only module, no schema changes)
- Affected code:
  - `skills/_lib/workflow_synthesizer.py` (NEW)
  - `skills/guide/SKILL.md` (MODIFIED - scan logic block)
  - `tests/unit/test_workflow_synthesizer.py` (NEW)
  - `tests/integration/test_guide_skill.bats` (MODIFIED - +2 tests)
- No breaking changes: synthesizer is additive, falls back to scan_state on any error
- No new dependencies: uses stdlib + existing `skills._lib.state_reader`
