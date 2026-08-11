# fix-plan-deps-candidates-import-guard

**优先级**: P0 | **来源**: 会话复盘 2026-07-31 — 端到端工作流执行中发现 2 个运行时缺陷
**阶段**: default | **分类**: core-impl
**类型**: fix

## 架构依据

- 会话复盘 2026-07-31: `plan_deps_candidates_env.py` 的 `importlib.util.spec_from_file_location()` 返回值未做 `None` 检查，当文件不存在或加载失败时 Python 在 `module_from_spec()` 上崩溃
- 同样会话中发现 `.plan-handoff.json` 的 `execution_mode_decisions` 字段残留已归档旧 change 的数据

## 范围

- **In Scope**:
  - `skills/guide-plan/scripts/plan_deps_candidates_env.py` — 添加 `spec is None` guard，或改为直接内联调用 `generate_deps_candidates()`
  - `skills/guide-plan/scripts/plan_done_gate.py::_load_execution_mode_decisions()` — 过滤已归档 change，或改为基于当前 `openspec/changes/` 目录重算
  - 新增单元测试覆盖 guard 逻辑
- **Out Scope**:
  - 不修改 `plan_deps_candidates.py` 的核心逻辑
  - 不修改 `plan_done_gate.sh` 的 bash 门控逻辑

## 关键场景

- GIVEN `plan_deps_candidates_env.py` 运行时 `spec_from_file_location()` 返回 `None`, WHEN 进入 `module_from_spec()`, THEN 抛出 `AttributeError: 'NoneType' object has no attribute 'loader'` — 当前无 guard 保护
- GIVEN `plan-done` 写入 handoff, WHEN `_load_execution_mode_decisions()` 从 `deps-analysis.json` 读取, THEN 可能返回已归档 change 的旧决策数据, 导致 ship 端执行模式决策错误

## 技术约束

- MUST `plan_deps_candidates_env.py` 添加 `if spec is None: raise ImportError(...)` guard
- MUST `_load_execution_mode_decisions()` 过滤掉不在 `openspec/changes/` 活跃目录中的 change
- MUST NOT 修改 `plan_deps_candidates.py` 的 `generate_deps_candidates()` 签名或行为
- SHOULD 添加单元测试: `tests/unit/test_plan_deps_candidates.py` 覆盖 guard 和过滤逻辑

## 验收标准

- `plan_deps_candidates_env.py` 在 `spec` 为 `None` 时打印错误并退出 1，而非 `AttributeError`
- `.plan-handoff.json` 的 `execution_mode_decisions` 只包含当前活跃的 change
- 现有 `pytest tests/unit/` 测试全部通过