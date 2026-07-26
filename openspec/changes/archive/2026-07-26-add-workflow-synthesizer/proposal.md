## Why

`guide` 推荐器当前依赖 `scan-state.sh` 的纯 bash 实现，输出两个扁平字符串 (`RECOMMEND` + `REASON`)。缺少结构化信息：阶段状态、可执行 change 列表、session 绑定状态、working tree 健康度。当 `guide.md` 需要展示交互式菜单（含 resume/restart/start-arch/all-done 选项）时，扁平字符串不足以支撑。

架构分析 2026-07-21 结论：引入一个**只读阶段感知综合器** (phase-aware synthesizer)，读取 sessions.json / handoff / iteration.json / git 状态，产出结构化 `WorkflowRecommendation`，覆盖 13 条推荐路径。与 `scan-state.sh` 并列工作：Python synthesizer 为主，bash scan_state 为 fallback。

## What Changes

- **NEW** `skills/_lib/workflow_synthesizer.py` (~792 行): read-only synthesizer with `PhaseStatus` + `WorkflowRecommendation` + `MenuOption` + `WorkingTreeIssue` frozen dataclasses + `synthesize()` entry point + 13-path decision tree mirroring `scan-state.sh::scan_state()` + helpers for unblocked_changes / active_session / orphaned_sessions / worktree task scan / committed change detection / working tree issue detection / all-options interactive menu builder. Never-raises contract with fallback recommendation.
- **NEW** `tests/unit/test_workflow_synthesizer.py` (~797 行, 54 测试): covers dataclass shape, all 13 decision paths (parametrized + individual), phase status summary, unblocked_changes filtering/sorting, rddf-session binding, orphaned sessions, never-raises contract, corrupt state resilience, worktree task detection, determinism, working tree issue detection.
- **NEW** `skills/_lib/state_reader.py` (~265 行): shared read-only data layer consumed by synthesizer, status CLI, feature CLI, and guide-arch/plan/ship intake phases. Provides `read_arch_handoff`, `read_plan_handoff`, `read_iteration`, `read_sessions`, `read_roadmap_state`, `list_worktrees`, `list_change_dirs`, `read_proposal_approved` — all never-raises, all read-only.
- **MODIFY** `skills/guide/SKILL.md`: integrate Python synthesizer call into the scan logic block with graceful fallback to legacy `scan_state` RECOMMEND/REASON globals. Synthesizer overrides RECOMMEND/REASON when Python available; scan_state baseline preserved on any error.
- **MODIFY** `skills/guide/scripts/guide_entry.sh`: add `menu_mode` support with synthesizer-driven interactive menu (all_options → user selection loop).
- **MODIFY** `tests/integration/test_guide_skill.bats`: add tests asserting synthesizer integration block present + scan_state fallback retained.
- **MODIFY** `tests/integration/test_guide_entry.bats`: add tests for interactive menu mode with synthesizer.

## Capabilities

### New Capabilities
- `workflow-synthesizer`: Read-only structured recommendation engine producing `WorkflowRecommendation` with confidence levels, phase status, unblocked changes, session binding, orphaned sessions, working tree issues, and all-options interactive menu.
- `state-reader`: Shared read-only data layer (8 functions) consumed by 4+ subsystems.

### Modified Capabilities
- `guide`: The scan logic now calls Python synthesizer with fallback to bash scan_state; interactive menu mode uses synthesizer's `all_options` for structured menu display.

## Impact

- **New code**: ~1854 lines (workflow_synthesizer.py 792 + state_reader.py 265 + test_workflow_synthesizer.py 797)
- **Modified**: `guide/SKILL.md`, `guide/scripts/guide_entry.sh`, bats integration tests
- **Dependencies**: None (stdlib only + existing `iteration.store` internal module)
- **Compatibility**: 100% backward compatible — synthesizer falls back to scan_state on any error; RECOMMEND/REASON globals unchanged
- **Risk**: Low — read-only module, never-raises contract, no schema changes
- **Source**: improvement `add-workflow-synthesizer`