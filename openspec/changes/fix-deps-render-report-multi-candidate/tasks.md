## 1. 修复候选列表转换

- [x] 1.1 修复 `deps_render_report.sh` L33：CANDIDATES → Python list 使用逗号分隔（`['a', 'b', 'c']`），消除相邻字符串字面量自动拼接
- [x] 1.2 验证 CANDIDATES="a b c" 渲染出 3 个独立 Mermaid 节点（当前：1 个拼接节点）

## 2. fallback 重算

- [x] 2.1 修复 L35-41 fallback 分支：读取 `.deps-candidates.json` 成功更新 CANDIDATES 后重新计算 `candidates_py`
- [x] 2.2 验证 CANDIDATES 为空 + `.deps-candidates.json` 3 候选 → 报告显示 3 个候选（当前：0 候选）

## 3. 测试

- [x] 3.1 新增 `tests/integration/test_deps_report_render_extraction.bats` 用例：3+ 候选渲染出独立节点
- [x] 3.2 新增 fallback 非空候选渲染用例
- [x] 3.3 运行 `bats tests/integration/test_deps_report_render_extraction.bats` 全部通过
- [x] 3.4 运行 `python3 -m pytest tests/unit/test_deps_output.py -q` 确认无破坏
