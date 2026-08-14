# fix-generator-scope-extraction

## Why

- ADR-0025（design proposal creation）：`guide-design` 阶段通过 `generate_full_proposal.py` 把 `.rddf/improvements/<name>.md` 的 5 段（架构依据/范围/关键场景/技术约束/验收标准）转换为 openspec `proposal.md`（Why/What Changes/Capabilities/Impact/Acceptance）
- AGENTS.md "状态文件清单"：`.rddf/improvements/` 是仓库已有 138+ 文件的改进提案池，generator 必须兼容所有现有格式
- 现有 improvements 格式（参考 `complete-third-party-replay-and-upstream-reporting.md`、`preserve-orchestrator-command-stdout.md` 等）：用 `### In Scope` 和 `### Out Scope` markdown H3 标题 + numbered list (1., 2., 3.) 列出范围
- generator 期望格式：`generate_full_proposal.py::_extract_scope_items` 当前只匹配 `- ` bullet items

### 已修复的上下文（不在本提案 scope）

> **前置修复（commit 132a654, 2026-08-04）** 已解决以下问题，**不在本提案范围内**：
> - `_extract_scope_items()` 现已支持 `- **In Scope**:` 和 `**In Scope**:` 两种 header 风格
> - Capabilities/Impact 现已从 `.rddf/improvements` 的"技术约束"段派生（不再 hardcoded `move-proposal-creation-to-design` 内容）
> - 已加 4 个基础回归测试覆盖 header 风格变更
>
> 本提案聚焦**剩余未修复的真实差距**。

### 识别的剩余缺口（来自 Oracle 2026-08-13 dogfooding）

1. **numbered list items 被忽略**：现有 generator 仅匹配 `- ` bullet items（line 73: `if stripped.startswith("- ")`），但 `.rddf/improvements/` 大量文件使用 `1. ` / `2. ` numbered items，导致 `## What Changes` 段 In Scope 项数显著少于原始 improvements 的 In Scope 项数
2. **空 section fallback 误导**：缺 In Scope 或 Out Scope 时输出 `- (TBD)`，占位符不够明确（应输出 `- (no items specified)` 避免读为"待补"）
3. **Capabilities 与 Impact 内容完全相同**：line 117-119 仍用同一份 `constraint_items` 拼出两个段，导致 `## Capabilities` 和 `## Impact` 视觉重复

### 引用现有惯例

- 现有 improvements 格式（138+ 文件）是事实来源，generator 必须支持
- ADR-0025 D2 映射：技术约束 → Capabilities/Impact（应是 stakeholder 视角的差异化映射，非同一份内容复制）

## What Changes

**In Scope**:

- **不重构 `generate_full_proposal.py` 整个文件**（保留 D2 映射逻辑）
- **不修改 `_extract_section()` 函数**（除非要修复相同 bug）
- **不修改 improvements 文件本身的格式要求**（H3 + numbered 是合法格式，向后兼容 138+ 文件）
- **不重做 commit 132a654 已修复的 header 风格处理**（已 ship）
- **不引入新依赖**（Python 标准库足够）
- **Capabilities/Impact 段落精细化拆分**：本提案做粗略拆分（按 MUST/MUST NOT/SHOULD 分类），精细化的"受哪些 capability 影响 vs 影响哪些 stakeholder"留独立提案
- **`.rddf/improvements/` 历史 138 个文件批量 reformat**：本提案只修 generator，已有 138 个文件保留现状（向后兼容）

### 关键场景

- GIVEN improvements 文件用 `### In Scope` (H3) 标题 + `1. **xxx**:` numbered items 列出范围，WHEN `generate_full_proposal.py` 转换，THEN `proposal.md` 的 `## What Changes` 段正确显示 In Scope 项 + Out Scope 项（数量与原始 improvements 一致）。

- GIVEN improvements 文件的 In Scope 段用 numbered items + 缩进子项（如 `1. **stdout/stderr 透传**:\n   - 主进程透传\n   - 后台异步`），WHEN 转换，THEN numbered item 作为完整一行（含子项拼接），保留 markdown 缩进结构。

- GIVEN improvements 文件 Out Scope 段完全缺失，WHEN 转换，THEN `**Out of Scope**:` 段输出 `- (no items specified)` 而非 `- (TBD)`（避免误解为占位符）。

- GIVEN generator 处理一份 5 段齐全的 improvements，WHEN 转换，THEN Capabilities 段填 MUST/MUST NOT/SHOULD 中带"能力"含义的项，Impact 段填"对 stakeholder 影响"含义的项（粗略拆分，避免完全相同）。

- GIVEN improvements 文件用 `- ` bullet items（现有测试已覆盖），WHEN 转换，THEN 行为不变（向后兼容，132a654 测试不退化）。

**Out of Scope**:

- (TBD)

## Capabilities

- MUST 修改 `_extract_scope_items()` 同时支持 `- ` (bullet) **和** `1. ` / `2. ` / `1) ` (numbered) 两种 item 起始格式（不破坏现有 `- ` 兼容）。
- MUST numbered item 子项（缩进的 `- `）拼接到父 item description（保留 `\n   - sub-item` 格式）。
- MUST 修复空 section fallback：缺 In Scope 或缺 Out Scope 时输出 `- (no items specified)`（仅 scope 段；其他段保留 `(TBD)` 语义）。
- MUST Capabilities 与 Impact 段内容差异化（粗略按 MUST/MUST NOT/SHOULD 语义分类，避免完全相同）。
- MUST 新增单元测试覆盖 3 种剩余格式场景（fixtures 目录 + pytest）。
- MUST NOT 修改 `_extract_section()` 签名（向后兼容）。
- MUST NOT 修改 improvements 文件本身的格式要求（H3 + numbered 是合法格式）。
- MUST NOT 修改 commit 132a654 已修复的 header 风格处理逻辑。
- MUST NOT 引入新依赖（Python 标准库足够）。
- SHOULD 用 `itertools.takewhile` 或类似技术简化 numbered + sub-items 的拼接逻辑（避免手工循环 bug）。
- SHOULD 在 `_extract_scope_items` 函数 docstring 明确支持 numbered items 处理。

## Impact

- MUST 修改 `_extract_scope_items()` 同时支持 `- ` (bullet) **和** `1. ` / `2. ` / `1) ` (numbered) 两种 item 起始格式（不破坏现有 `- ` 兼容）。
- MUST numbered item 子项（缩进的 `- `）拼接到父 item description（保留 `\n   - sub-item` 格式）。
- MUST 修复空 section fallback：缺 In Scope 或缺 Out Scope 时输出 `- (no items specified)`（仅 scope 段；其他段保留 `(TBD)` 语义）。
- MUST Capabilities 与 Impact 段内容差异化（粗略按 MUST/MUST NOT/SHOULD 语义分类，避免完全相同）。
- MUST 新增单元测试覆盖 3 种剩余格式场景（fixtures 目录 + pytest）。
- MUST NOT 修改 `_extract_section()` 签名（向后兼容）。
- MUST NOT 修改 improvements 文件本身的格式要求（H3 + numbered 是合法格式）。
- MUST NOT 修改 commit 132a654 已修复的 header 风格处理逻辑。
- MUST NOT 引入新依赖（Python 标准库足够）。
- SHOULD 用 `itertools.takewhile` 或类似技术简化 numbered + sub-items 的拼接逻辑（避免手工循环 bug）。
- SHOULD 在 `_extract_scope_items` 函数 docstring 明确支持 numbered items 处理。

## Acceptance

1. **单元测试覆盖**：新增 `tests/unit/test_generate_full_proposal_scope.py`（或扩展现有 `tests/unit/test_generate_full_proposal.py`）≥3 cases：
   - H3 + numbered items → 正确分类 In/Out Scope（项数与原始 improvements 一致）
   - H3 + numbered items + 缩进子项 → 子项拼接到父 item description
   - 缺 Out Scope 段 → 输出 `(no items specified)`
   - Capabilities 与 Impact 段内容不重复（粗略分类生效）

2. **回归测试**：现有 `tests/unit/test_generate_full_proposal.py` 12 个测试 + `tests/integration/test_design_proposal_review*.bats` 全部通过。

3. **端到端验证**：在仓库根目录验证生成：
   ```bash
   IMPROVEMENTS_PATH=.rddf/improvements/fix-generator-scope-extraction.md \
   CHANGE_NAME=fix-generator-scope-extraction \
     python3 skills/guide-design/scripts/generate_full_proposal.py
   ```
   断言生成的 `## What Changes` 段 In Scope 项数 = 原始 improvements 的 In Scope 项数（误差 ±0）。

4. **验证命令**：`./test.sh --python --unit` 全绿；`./test.sh --full --regression` 全绿，无新增失败（`tests/KNOWN_FAILURES.txt` baseline 内）。

5. **行数约束**：`generate_full_proposal.py` 增量 ≤50 行（最小侵入）。

6. **向后兼容**：现有 improvements 文件（138 个）`generate_full_proposal()` 输出的 `## What Changes` 段 In Scope 项数 ≥ 原始 improvements 的 In Scope 项数（对用 `- ` bullet 的文件行为不变）。

