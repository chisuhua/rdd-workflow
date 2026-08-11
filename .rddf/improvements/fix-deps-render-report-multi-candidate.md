# fix-deps-render-report-multi-candidate

**优先级**: P1 | **来源**: 会话复盘 2026-07-31 — 3 个候选 change 渲染成单个拼接字符串
**阶段**: v2.1 | **分类**: core-impl
**类型**: fix

## 架构依据

- `skills/deps/scripts/deps_render_report.sh::render_deps_report`（P0-3 提取自 deps.md Step 5）负责渲染 `.rddf/state/.deps-output.md`
- 会话复盘 2026-07-31 实测：传入 3 个候选 `fix-plan-deps-candidates-import-guard fix-rddf-session-lifecycle-binding fix-test-infrastructure-and-skill-registration`，Mermaid 图渲染成**单个拼接节点** `fix-plan...fix-rddf...fix-test...`，依赖图完全错误
- 根因 1：L33 `sed "s/[^ ]*/'&'/g"` 把空格分隔候选包成 `'c1' 'c2' 'c3'`（无逗号）→ Python 相邻字符串字面量**自动拼接**成 `'c1c2c3'`
- 根因 2：L35-41 fallback 分支读取 `.deps-candidates.json` 成功更新 `CANDIDATES` 后，**未重新计算** `candidates_py`（仍是空串算出的 `[]`），导致 fallback 路径渲染出 0 候选

## 范围

- **In Scope**:
  - `skills/deps/scripts/deps_render_report.sh:30-47` — 修复 CANDIDATES → Python 列表转换（加逗号分隔），fallback 后重新计算 `candidates_py`
  - `tests/integration/test_deps_report_render_extraction.bats` — 补充 3+ 候选与 fallback 场景测试
- **Out Scope**:
  - 不修改 `skills/deps/scripts/deps_output.py::render_markdown_report` 的渲染逻辑（接收方正确）
  - 不修改 `.deps-candidates.json` schema
  - 不涉及 guide-plan 的 `generate_deps_candidates`

## 关键场景

- GIVEN CANDIDATES="a b c" (3 个空格分隔候选), WHEN 调用 render_deps_report, THEN Mermaid 图含 3 个独立节点（当前：1 个拼接节点）
- GIVEN CANDIDATES 为空且 `.deps-candidates.json` 有 3 个候选, WHEN 调用 render_deps_report, THEN fallback 正确读取并渲染 3 个节点（当前：报告显示 0 候选）
- GIVEN 单候选 CANDIDATES="c1", WHEN 调用, THEN 渲染 1 个节点（保持现有行为不变）

## 技术约束

- MUST CANDIDATES → Python list 转换使用逗号分隔：`['a', 'b', 'c']`
- MUST fallback 读取成功时重新计算 `candidates_py`（当前第 33 行算完后第 35-41 行只更新 CANDIDATES 不更新 candidates_py）
- MUST NOT 修改 `render_markdown_report(candidates, project_root, ...)` 的签名
- MUST 补充测试：3+ 候选渲染、fallback 非空候选渲染
- SHOULD 用 Python 的 `json.dumps` 或 `shlex.split` 替代 sed 字符串处理（更健壮）

## 验收标准

- CANDIDATES="a b c" 渲染出 3 个独立 Mermaid 节点
- CANDIDATES 为空 + `.deps-candidates.json` 3 候选 → 报告显示 3 个候选
- `bats tests/integration/test_deps_report_render_extraction.bats` 全部通过（含新增用例）
- 现有 `test_deps_output.py` 单元测试通过
