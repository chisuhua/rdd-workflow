## Why

会话复盘 2026-07-31 实测：传入 3 个候选 `fix-plan-deps-candidates-import-guard fix-rddf-session-lifecycle-binding fix-test-infrastructure-and-skill-registration` 调用 `skills/deps/scripts/deps_render_report.sh::render_deps_report`，Mermaid 图渲染成**单个拼接节点** `fix-plan...fix-rddf...fix-test...`，依赖图完全错误。

根因 1：L33 `sed "s/[^ ]*/'&'/g"` 把空格分隔候选包成 `'c1' 'c2' 'c3'`（无逗号）→ Python 相邻字符串字面量**自动拼接**成 `'c1c2c3'`。
根因 2：L35-41 fallback 分支读取 `.deps-candidates.json` 成功更新 `CANDIDATES` 后，**未重新计算** `candidates_py`（仍是空串算出的 `[]`），导致 fallback 路径渲染出 0 候选。

## What Changes

- `skills/deps/scripts/deps_render_report.sh:30-47` — 修复 CANDIDATES → Python 列表转换（加逗号分隔），fallback 后重新计算 `candidates_py`。
- `tests/integration/test_deps_report_render_extraction.bats` — 补充 3+ 候选与 fallback 场景测试。

## Capabilities

### New Capabilities
- `deps-render-multi-candidate`: 多候选 CANDIDATES 正确渲染为独立 Mermaid 节点；fallback 路径正确渲染非空候选

### Modified Capabilities
<!-- 无 spec 级行为变更 -->

## Impact

**In Scope:**
- `skills/deps/scripts/deps_render_report.sh:30-47` — CANDIDATES → Python 列表转换（逗号分隔）+ fallback 后重新计算 `candidates_py`
- `tests/integration/test_deps_report_render_extraction.bats` — 新增 3+ 候选与 fallback 非空候选用例

**Out of Scope:**
- 不修改 `skills/deps/scripts/deps_output.py::render_markdown_report` 的渲染逻辑（接收方正确）
- 不修改 `.deps-candidates.json` schema
- 不涉及 guide-plan 的 `generate_deps_candidates`
