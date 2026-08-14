# fix-generator-scope-extraction

**优先级**: P1 | **来源**: Oracle 审查 + dogfooding 实战发现
**阶段**: v2.1 | **分类**: core-impl
**类型**: bug-fix
**主题**: 不适用

## 架构依据

- ADR-0025（design proposal creation）：`guide-design` 阶段通过 `generate_full_proposal.py` 把 `.rddf/improvements/<name>.md` 的 5 段（架构依据/范围/关键场景/技术约束/验收标准）转换为 openspec `proposal.md`（Why/What Changes/Capabilities/Impact/Acceptance）
- AGENTS.md "状态文件清单"：`.rddf/improvements/` 是仓库已有 138+ 文件的改进提案池，generator 必须兼容所有现有格式
- 现有 improvements 格式（参考 `complete-third-party-replay-and-upstream-reporting.md`、`preserve-orchestrator-command-stdout.md` 等）：用 `### In Scope` 和 `### Out Scope` markdown H3 标题 + numbered list (1., 2., 3.) 列出范围
- generator 期望格式：`generate_full_proposal.py::_extract_scope_items` 只匹配 `**In Scope**:` 和 `**Out Scope**:` bold-with-colon 标题
- Oracle 2026-08-13 dogfooding 验证：批准 2 个改进提案（`preserve-orchestrator-command-stdout` + `harden-plan-intake-bootstrap-and-design-gate-tests`）时，generator 输出的 `proposal.md` 把 **In Scope** 标题填了 **Out Scope** 内容（错位 bug）

核心原则：generator 必须匹配**真实存在的格式**（H3 标题），不假设某条具体路径的格式。改进的扩展性优先于写新工具。

## 范围

### In Scope

1. **修复 `_extract_scope_items()` 标题检测**：同时匹配 `### In Scope` / `### Out Scope` (H3) **和** `**In Scope**:` / `**Out Scope**:` (bold-colon) 两种格式
2. **修复 numbered list 项处理**：`1. **xxx**:` 这种 numbered item 应作为 in-scope item 抓取，子项（缩进的 `- `）作为 description 拼接到上一行
3. **修复空 section fallback**：当某个 section 完全缺失时，`## What Changes` 的对应子标题应输出 `- (no items)` 而非 `- (TBD)`（避免误导）
4. **修复 Capabilities / Impact 重复**：当前两个段都被填入同一份"技术约束"内容，应按 D2 映射分别填 — Capabilities = 涉及的能力面，Impact = 受影响面（拆分为前后半句或由 MUST/MUST NOT/SHOULD 分类）
5. **新增 fixtures 测试**：覆盖 5 种格式场景（H3 + numbered / H3 + bulleted / bold-colon + bulleted / empty section / mixed）

### Out Scope

- 不重构 `generate_full_proposal.py` 整个文件（保留 D2 映射逻辑）
- 不修改 `_extract_section()` 函数（除非要修复相同 bug）
- 不修改 improvements 文件本身的格式要求（保留兼容性）

### 不修复 / Deferred（独立提案）

- **Capabilities/Impact 段落内容拆分**：本提案先实现简单拆分（按 MUST/MUST NOT/SHOULD 分类），精细化的"受哪些 capability 影响 vs 影响哪些 stakeholder"留独立提案
- **`.rddf/improvements/` 历史 138 个文件批量 reformat**：本提案只修 generator，已有 138 个文件保留现状（向后兼容）

## 关键场景

- GIVEN improvements 文件用 `### In Scope` (H3) 标题 + `1. **xxx**:` numbered items 列出范围，WHEN `generate_full_proposal.py` 转换，THEN `proposal.md` 的 `## What Changes` 段正确显示 In Scope 项 + Out Scope 项（不再错位）。

- GIVEN improvements 文件的 In Scope 段用 numbered items + 缩进子项（如 `1. **stdout/stderr 透传**:\n   - 主进程透传\n   - 后台异步`），WHEN 转换，THEN numbered item 作为完整一行（含子项拼接），保留 markdown 缩进结构。

- GIVEN improvements 文件用 `**In Scope**:` (bold-colon) + bulleted items 格式，WHEN 转换，THEN 与现有逻辑保持一致（向后兼容）。

- GIVEN improvements 文件 Out Scope 段完全缺失，WHEN 转换，THEN `**Out of Scope**:` 段输出 `- (no items specified)` 而非 `- (TBD)`（避免误解为占位符）。

- GIVEN improvements 文件 关键场景段存在 GIVEN/WHEN/THEN bullets，WHEN 转换，THEN 拼接在 `### 关键场景` 子段（保留 generator 现有行为）。

- GIVEN generator 处理一份 5 段齐全的 improvements，WHEN 转换，THEN Capabilities 段填 MUST/MUST NOT/SHOULD 中带"能力"含义的项，Impact 段填"对 stakeholder 影响"含义的项（粗略拆分，避免重复）。

## 技术约束

- MUST 修改 `_extract_scope_items()` 同时支持 H3 + bold-colon 两种标题检测（不破坏现有 bold-colon 兼容）。
- MUST numbered list items (`1. `, `2. `) 视为 in-scope items 抓取，子项（缩进的 `- `）拼接到父 item description（保留 `\n   - sub-item` 格式）。
- MUST 修复空 section fallback：缺 In Scope 或缺 Out Scope 时输出 `- (no items specified)`。
- MUST Capabilities 与 Impact 段内容差异化（粗略按 MUST/MUST NOT/SHOULD 语义分类，避免完全相同）。
- MUST 新增单元测试覆盖 5 种格式场景（fixtures 目录 + pytest）。
- MUST NOT 修改 `_extract_section()` 签名（向后兼容）。
- MUST NOT 修改 improvements 文件本身的格式要求（H3 + numbered 是合法格式）。
- MUST NOT 引入新依赖（Python 标准库足够）。
- SHOULD 用 `itertools.takewhile` 或类似技术简化 numbered + sub-items 的拼接逻辑（避免手工循环 bug）。
- SHOULD 在 `_extract_scope_items` 函数 docstring 明确支持两种标题格式 + numbered items 处理。

## 验收标准

1. **单元测试覆盖**：新增 `tests/unit/test_generate_full_proposal_scope.py` ≥5 cases：
   - H3 + numbered items → 正确分类 In/Out Scope
   - H3 + bulleted items → 正确分类
   - bold-colon + bulleted → 现有逻辑不变（向后兼容）
   - 缺 Out Scope 段 → 输出 `(no items specified)`
   - Capabilities 与 Impact 段内容不重复（粗略分类生效）

2. **回归测试**：现有 `tests/integration/test_design_proposal_review*.bats`（如适用）+ `tests/unit/test_*proposal*` 全部通过。

3. **端到端验证**：在仓库根目录重跑 approve flow：
   ```bash
   bash skills/guide-design/scripts/approve_proposal.sh \
     "preserve-orchestrator-command-stdout" "P1" "$PROJECT_ROOT"
   ```
   （注意：会失败因为 change 已存在；改用 `--dry-run` 或临时脚本验证 generator 输出）

4. **手写验证脚本**：`/tmp/verify_scope_extraction.py` 加载 `.rddf/improvements/preserve-orchestrator-command-stdout.md` + `.rddf/improvements/harden-plan-intake-bootstrap-and-design-gate-tests.md`，调 `generate_full_proposal()`，断言生成的 `## What Changes` 段 In Scope 项数 = 原始 improvements 的 In Scope 项数（误差 ±0）。

5. **验证命令**：`./test.sh --python --unit` 全绿；`./test.sh --full --regression` 全绿，无新增失败（`tests/KNOWN_FAILURES.txt` baseline 内）。

6. **行数约束**：`generate_full_proposal.py` 增量 ≤50 行（最小侵入）。

7. **向后兼容**：现有 improvements 文件（138 个）`generate_full_proposal()` 输出虽可能仍不完美（取决于格式混合），但至少 `## What Changes` 段的 In Scope 项数 ≥ 原始 improvements 的 In Scope 项数。