## Context

会话复盘 2026-07-31 端到端工作流执行中，`plan_deps_candidates_env.py` 在加载目标模块时，`importlib.util.spec_from_file_location()` 返回 `None`（目标文件缺失或加载失败），代码直接调用 `module_from_spec()` 导致 `AttributeError: 'NoneType' object has no attribute 'loader'`。此外，`plan_done_gate.py::_load_execution_mode_decisions()` 从 `deps-analysis.json` 读取执行模式决策时未过滤已归档 change，导致 `.plan-handoff.json` 残留过期决策。

## Goals / Non-Goals

**Goals:**
- `plan_deps_candidates_env.py` 在 `spec` 为 `None` 时给出可诊断错误（`ImportError` 带目标路径）并退出 1，而非在 `module_from_spec()` 上崩溃
- `_load_execution_mode_decisions()` 只返回当前活跃 change（`openspec/changes/` 下非 archive 目录）的决策
- 新增单元测试覆盖 guard 与过滤逻辑

**Non-Goals:**
- 不修改 `plan_deps_candidates.py::generate_deps_candidates()` 的签名或核心行为
- 不修改 `plan_done_gate.sh` 的 bash 门控逻辑
- 不重构 deps 分析的静态三轴逻辑

## Decisions

1. **`plan_deps_candidates_env.py` None-guard**：在 `spec_from_file_location()` 返回后立即检查，`if spec is None:` 抛出带目标文件路径的 `ImportError`，由调用方捕获并打印错误、退出 1。
2. **执行模式决策过滤**：`_load_execution_mode_decisions()` 读取 `deps-analysis.json` 后，以 `openspec/changes/` 下活跃目录集合为白名单过滤 change 名，只保留仍在活跃目录中的决策条目。
3. **测试**：在 `tests/unit/test_plan_deps_candidates.py` 新增用例——(a) 构造 `spec_from_file_location` 返回 `None` 的场景，断言抛出可诊断错误；(b) 构造含已归档 change 的 `deps-analysis.json`，断言过滤后仅剩活跃 change。

## Risks / Trade-offs

- **guard 位置**：在 `plan_deps_candidates_env.py` 内部加 guard 比在调用方 catch `AttributeError` 更直接，错误信息可包含目标文件路径，便于诊断。
- **过滤一致性**：活跃目录集合以 `openspec/changes/` 实时扫描为准，避免依赖 iteration.json 状态可能滞后的问题。
- **低风险**：两处改动均为防御性修复，不改变正常路径行为；现有 `pytest tests/unit/` 全量回归即可验证无破坏。
