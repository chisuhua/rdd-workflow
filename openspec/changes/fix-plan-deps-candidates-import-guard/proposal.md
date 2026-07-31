## Why

会话复盘 2026-07-31 端到端工作流执行中发现 2 个运行时缺陷：

1. `skills/guide-plan/scripts/plan_deps_candidates_env.py` 中 `importlib.util.spec_from_file_location()` 返回值未做 `None` 检查。当目标文件不存在或加载失败时，`spec` 为 `None`，后续调用 `module_from_spec()` 抛出 `AttributeError: 'NoneType' object has no attribute 'loader'`，导致 deps 候选生成阶段崩溃而非给出可诊断的错误。
2. `.plan-handoff.json` 的 `execution_mode_decisions` 字段残留已归档旧 change 的决策数据。`plan_done_gate.py::_load_execution_mode_decisions()` 从 `deps-analysis.json` 读取时不过滤已归档 change，导致 ship 端可能采用过期 change 的执行模式决策（违反 ADR-0024 §决策：执行模式必须以**当前活跃** change 为准）。

## What Changes

- `skills/guide-plan/scripts/plan_deps_candidates_env.py` — 添加 `spec is None` guard：当 `spec_from_file_location()` 返回 `None` 时抛出带诊断信息的 `ImportError` 并退出 1，而非在 `module_from_spec()` 上崩溃。
- `skills/guide-plan/scripts/plan_done_gate.py::_load_execution_mode_decisions()` — 过滤掉不在 `openspec/changes/` 活跃目录中的 change，使 `execution_mode_decisions` 只包含当前活跃 change 的决策（对齐 ADR-0024）。
- 新增单元测试覆盖 guard 与过滤逻辑。

## Capabilities

### New Capabilities
- `deps-candidates-import-guard`: 对 `plan_deps_candidates_env.py` 的动态导入提供 None-guard，失败时给出可诊断错误而非 AttributeError

### Modified Capabilities
<!-- 无 spec 级行为变更 -->

## Impact

**In Scope:**
- `skills/guide-plan/scripts/plan_deps_candidates_env.py` — None-guard
- `skills/guide-plan/scripts/plan_done_gate.py` — 执行模式决策过滤
- `tests/unit/test_plan_deps_candidates.py`（新增）— 覆盖 guard 和过滤逻辑

**Out of Scope:**
- 不修改 `plan_deps_candidates.py` 的核心逻辑（generate_deps_candidates 签名/行为不变）
- 不修改 `plan_done_gate.sh` 的 bash 门控逻辑
- 不涉及 deps 静态三轴分析逻辑重构
