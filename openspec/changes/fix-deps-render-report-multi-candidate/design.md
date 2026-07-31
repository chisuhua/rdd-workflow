## Context

`skills/deps/scripts/deps_render_report.sh::render_deps_report`（P0-3 提取自 deps.md Step 5）负责渲染 `.rddf/state/.deps-output.md`。会话复盘 2026-07-31 实测：传入 3 个候选时 Mermaid 图渲染成单个拼接节点，fallback 路径（CANDIDATES 为空、从 `.deps-candidates.json` 读取）渲染出 0 候选。

## Goals / Non-Goals

**Goals:**
- CANDIDATES="a b c"（3 个空格分隔候选）渲染出 3 个独立 Mermaid 节点
- CANDIDATES 为空 + `.deps-candidates.json` 有 3 候选时，fallback 正确读取并渲染 3 个节点
- 单候选 CANDIDATES="c1" 保持现有行为（渲染 1 个节点）

**Non-Goals:**
- 不修改 `render_markdown_report(candidates, project_root, ...)` 的签名
- 不修改 `deps_output.py` 渲染逻辑
- 不修改 `.deps-candidates.json` schema

## Decisions

1. **CANDIDATES → Python list 使用逗号分隔**：`sed "s/[^ ]*/'&'/g"` 替换为 `python3 -c` + `json.dumps(shlex.split("$CANDIDATES"))` 生成 `['a', 'b', 'c']` 形式，消除相邻字符串字面量自动拼接。
2. **fallback 后重新计算 `candidates_py`**：fallback 分支读取 `.deps-candidates.json` 成功更新 `CANDIDATES` 后，必须重新计算 `candidates_py`（用更新后的 CANDIDATES），而非沿用空串算出的 `[]`。
3. **测试覆盖**：新增 3+ 候选渲染用例 + fallback 非空候选渲染用例，锁定两类回归。

## Risks / Trade-offs

- **健壮性**：用 `shlex.split` / `json.dumps` 替代 sed 字符串处理更健壮（正确处理空格、引号、特殊字符）。
- **回归验证**：现有 `test_deps_output.py` 单元测试 + 新增 bats 用例双覆盖；单候选行为不变。
- **低风险**：改动集中在候选列表转换与 fallback 重算两点，不触碰渲染接收方逻辑。
