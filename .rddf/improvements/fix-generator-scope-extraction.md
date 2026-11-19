---
优先级: P1
来源: Oracle 审查 + dogfooding 实战发现
阶段: v2.1
分类: core-impl
类型: bug-fix
主题: 不适用
---
**优先级**: P1 | **来源**: Oracle 审查 + dogfooding 实战发现
**阶段**: v2.1 | **分类**: core-impl
**类型**: bug-fix
**主题**: 不适用

## 架构依据

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

## 范围

### In Scope

1. **修复 `_extract_scope_items()` numbered list 处理**：同时匹配 `- ` (bullet) **和** `1. ` / `2. ` / `1) ` (numbered) 两种 item 起始格式
2. **修复 numbered item 子项拼接**：`1. **xxx**:` 这种 numbered item 缩进的子项（`   - sub-item`）应拼接到上一行 description（保留 `\n   - sub-item` 格式）
3. **修复空 section fallback**：缺 In Scope 或 Out Scope 时输出 `- (no items specified)` 而非 `- (TBD)`（仅针对 scope 段；其他段保留 `- (TBD)` 语义）
4. **修复 Capabilities / Impact 内容差异化**：从同一份 `constraint_items` 拆分为前后半句或按 MUST/MUST NOT/SHOULD 分类（Capabilities = 涉及的能力面，Impact = 受影响面）
5. **新增 fixtures 测试**：覆盖 3 种剩余格式场景（numbered items / empty section / capabilities 差异化）

### Out Scope

- **不重构 `generate_full_proposal.py` 整个文件**（保留 D2 映射逻辑）
- **不修改 `_extract_section()` 函数**（除非要修复相同 bug）
- **不修改 improvements 文件本身的格式要求**（H3 + numbered 是合法格式，向后兼容 138+ 文件）
- **不重做 commit 132a654 已修复的 header 风格处理**（已 ship）
- **不引入新依赖**（Python 标准库足够）

### 不修复 / Deferred（独立提案）

- **Capabilities/Impact 段落精细化拆分**：本提案做粗略拆分（按 MUST/MUST NOT/SHOULD 分类），精细化的"受哪些 capability 影响 vs 影响哪些 stakeholder"留独立提案
- **`.rddf/improvements/` 历史 138 个文件批量 reformat**：本提案只修 generator，已有 138 个文件保留现状（向后兼容）

## 关键场景

- GIVEN improvements 文件用 `### In Scope` (H3) 标题 + `1. **xxx**:` numbered items 列出范围，WHEN `generate_full_proposal.py` 转换，THEN `proposal.md` 的 `## What Changes` 段正确显示 In Scope 项 + Out Scope 项（数量与原始 improvements 一致）。

- GIVEN improvements 文件的 In Scope 段用 numbered items + 缩进子项（如 `1. **stdout/stderr 透传**:\n   - 主进程透传\n   - 后台异步`），WHEN 转换，THEN numbered item 作为完整一行（含子项拼接），保留 markdown 缩进结构。

- GIVEN improvements 文件 Out Scope 段完全缺失，WHEN 转换，THEN `**Out of Scope**:` 段输出 `- (no items specified)` 而非 `- (TBD)`（避免误解为占位符）。

- GIVEN generator 处理一份 5 段齐全的 improvements，WHEN 转换，THEN Capabilities 段填 MUST/MUST NOT/SHOULD 中带"能力"含义的项，Impact 段填"对 stakeholder 影响"含义的项（粗略拆分，避免完全相同）。

- GIVEN improvements 文件用 `- ` bullet items（现有测试已覆盖），WHEN 转换，THEN 行为不变（向后兼容，132a654 测试不退化）。

## 技术约束

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

## 验收标准

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

## 实施状态核对（2026-11-19 补记）

⚠️ 本节是**事实订正**，不改变本提案的任何决策。目的是让「这个提案到底什么时候兑现的」有个准确答案 ——
索引里写「2026-08-15 已实施」，但**范围段（`## 范围`）的 numbered/子项支持直到 2026-11-19 才真正存在**。

### 逐条验收标准的实际结论

| 验收标准 | 2026-08-14（`c2e315c`） | 2026-11-19（`68623a4`） |
|---|---|---|
| 1.1 H3 + numbered items ⇒ 正确分类 In/Out Scope | **未兑现** | 已兑现 |
| 1.2 numbered items + 缩进子项 ⇒ 子项并入父项 | **未兑现** | 已兑现 |
| 1.3 缺 Out Scope 段 ⇒ 输出 `(no items specified)` | 已兑现 | 保持 |
| 1.4 Capabilities 与 Impact 段内容不重复 | 已兑现 | 保持 |

### 根因：实现落在了**另一个函数**里

`c2e315c`（2026-08-14，commit message 写着 "support numbered lists … in generate_full_proposal"）
把 numbered 前缀匹配与子项归并加到了 **`_extract_bullet_items`**（服务于「技术约束 → Capabilities/Impact」），
而本提案的验收标准、归档 change `2026-08-14-fix-generator-scope-extraction` 的 task 第 1/2 条、
以及已合并的 spec `generator-scope-extraction` 的 Requirement 1/2，指名的都是
**`_extract_scope_items`**（服务于「`## 范围` → In/Out Scope」）。

⇒ **需求没被验证过，所以也没被发现没实现**：
- `c2e315c` 新增的 6 个用例（`tests/unit/test_generate_full_proposal_scope.py`）import 的也是
  `_extract_bullet_items` —— 测的是同一条已经能过的路径；
- 其中 `test_empty_section_fallback` 断言的是**当前行为**（`result == []`，注释里写着
  "Current behavior returns empty list, not explicit marker"），也不是需求本身；
- 该测试文件在 2026-09-06（`93c5ecd` 修 pytest 收集）被**删除** ⇒ 连这层假覆盖都没了。

⇒ 结果就是：门一直绿，spec 的 Requirement 1/2 从 2026-08-15 到 2026-11-19 **一直是未满足状态**，
而 `## What Changes` 的 In Scope 会被整个 `## 范围` 段顶掉、Out of Scope 被输出两遍
（这正是 `fix-script-project-root-anchoring` 立项时手工修过、并在「本次不做」里记为「另案」的现象）。

### 2026-11-19 的补齐（commit `68623a4`）

`_extract_scope_items` 一个函数内三处改动：编号条目识别（`_SCOPE_ITEM_RE`）、子项归并
（按 header 之后首个条目的缩进定 base 层级）、header 拼写归一化（`- **Out Scope**:` 之前不被识别，
导致 175/291 个 improvement 的越界条目全部落进 In Scope）。

- 回归测试：`tests/unit/test_generate_full_proposal.py` +4 例（编号分段 / Out of Scope 只出现一次 /
  spec 原样的子项归并 / `- **In Scope**:`+2 空格孩子的兼容回归）。
- 语料复核（291 个 improvement）：**0 处内容丢失**；in 项数变少 5 个（子项并入父项）、
  变多 18 个（编号条目被认出）、不变 268 个；out 项数变多 175 个。
- 反向变异：条目正则退回只认 `- ` ⇒ 新增用例红。

### 仍然残留的一处偏差（未修，记录在案）

已合并 spec 的 Requirement 4 写的是「`Capabilities` contains **only** `MUST` items」，而实现的
`_split_capabilities_impact` 是「除 `MUST NOT` 外全进 Capabilities」（`SHOULD` / 无前缀条目也进
Capabilities）。改成严格只收 MUST 会让 SHOULD 类约束**从 proposal 里消失**，属于另一个取舍 ⇒ 未动。

### 顺带记下的系统性缺口

本仓**没有「spec Requirement ⇒ 代码兑现」的检查**（`openspec validate` 只查结构）。这次的假绿
之所以能活 3 个月，就是因为「归档 change 的 task 勾了 `[x]`」与「spec Requirement 被满足」之间
没有任何交叉验证。现在这两条 Requirement 由 `tests/unit/test_generate_full_proposal.py` 的 4 个
用例直接钉住（断言的是 spec 的 Scenario 原文），缺口从「靠人记」变成「靠测试」。
