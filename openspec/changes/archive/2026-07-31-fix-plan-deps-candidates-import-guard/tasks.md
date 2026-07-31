## 1. Import Guard 修复

- [x] 1.1 在 `plan_deps_candidates_env.py` 中 `spec_from_file_location()` 返回后添加 `if spec is None:` guard，抛出带目标文件路径的 `ImportError`
- [x] 1.2 在调用方（bash wrapper）捕获该错误，打印诊断信息并以退出码 1 结束，而非 Python traceback 崩溃

## 2. 执行模式决策过滤

- [x] 2.1 修改 `plan_done_gate.py::_load_execution_mode_decisions()`：读取 `deps-analysis.json` 后，以 `openspec/changes/` 活跃目录（非 archive）为白名单过滤 change 名
- [x] 2.2 确保 `.plan-handoff.json` 的 `execution_mode_decisions` 只包含当前活跃 change

## 3. 单元测试

- [x] 3.1 新增 `tests/unit/test_plan_deps_candidates.py`：构造 `spec_from_file_location` 返回 `None` 的场景，断言抛出可诊断错误
- [x] 3.2 构造含已归档 change 的 `deps-analysis.json`，断言 `_load_execution_mode_decisions()` 过滤后仅剩活跃 change
- [x] 3.3 运行 `python3 -m pytest tests/unit/ -q` 全量回归，确认无破坏
