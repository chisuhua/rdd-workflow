# fix-design-proposal-review-approved-parsing

## Why

- **3 处相同 bug**：`skills/guide-design/scripts/design_proposal_review.sh:82`、`skills/guide/scripts/scan-state.sh:276-278`、`skills/propose/scripts/propose_change.py:436` 都用 `re.split(r"## 已实施", content)[0]` 解析 approved，**只读 `## 已批准提案` 段（当前为空）**，永远返回 0 个 approved entries
- **直接后果**：
  - design phase 把 3 个已批准 P1 proposal 误判为"待审"（2026-08-07 会话实际遇到：`RDDF-0001-fix-rddf-session-import-path` / `fix-rddf-session-owner-cross-call` / `ship-delete-branch-safety` 都已批准 + 已实施 2026-07-29，但被列为待审）
  - dashboard 显示 `approved: 0`（实际 122+ 个）
  - propose 阶段检查 approved 状态误判
- **根因分析**：`proposal-approved.md` 设计为 `## 已批准提案`（已批准待实施）+ `## 已实施`（已批准 + 已实施）两段。历史 proposals 直接 archive，从未经过"approved"段滞留——导致 `## 已批准提案` 段实际为空，3 个脚本的"## 已实施 之前"读取永远是空集
- **关联 improvement**：`detect-suggestions-approved-inconsistency`（P3 已实施 2026-07-29）解决 suggestions ↔ approved **数据视角一致性**，**不修解析逻辑本身**。本次提案与它互补（一个修数据视角，一个修解析视角）
- **设计依据**：ADR-0016 (arch-artifact-discovery-contract) 强调 artifacts 的发现契约应跨脚本一致；Oracle C1 safe 模式（env var 传递路径）已用于其他 `_lib/` helpers，是 v2.0+ 的标准模式
- **修复策略**：提取 helper 集中解析逻辑，3 处调用点统一调用，消除"一处改一处忘"的脆弱模式

## What Changes

**In Scope**:

- 新建 `skills/_lib/parse_approved.py`（纯函数 helper，无副作用）
- 修改 `skills/guide-design/scripts/design_proposal_review.sh:74-86` → 调用 helper（替代内联 PYEOF heredoc）
- 修改 `skills/guide/scripts/scan-state.sh:275-278` → 调用 helper（替代内联 PYEOF heredoc）
- 修改 `skills/propose/scripts/propose_change.py:436` → 调用 helper（替代内联 re.split）
- 新增 `tests/unit/test_parse_approved.py`（pytest，覆盖 helper 4 个 case）
- 新增 `tests/integration/test_approved_parsing_fix.bats`（bats，覆盖 3 个调用点的修复）

### 关键场景

- GIVEN `proposal-approved.md` 有 122 个 approved entries（全部位于 `## 已实施` 段）WHEN `guide-design` Phase 3 调用 `design_proposal_review.sh` THEN 列出 **0 个**待审查条目（修复前误列 ≥3 个）
- GIVEN 用户调用 `rddf dashboard` WHEN `scan-state.sh` 检测 approved 数量 THEN 返回 **122**（修复前返回 0）
- GIVEN `propose_change.py` 在 propose 阶段检查某 proposal 是否已批准 WHEN helper 调用 THEN 正确识别（修复前总是返回 false）
- GIVEN `proposal-approved.md` 文件不存在 WHEN helper 调用 THEN 返回空 list（不抛异常）
- GIVEN `proposal-approved.md` 为空文件 WHEN helper 调用 THEN 返回空 list（不抛异常）
- GIVEN `proposal-approved.md` 只有 `## 已批准提案` 段（有内容）WHEN helper 调用 THEN 返回该段全部 entries（不漏）
- GIVEN `proposal-approved.md` 只有 `## 已实施` 段（当前实际状态）WHEN helper 调用 THEN 返回该段全部 entries（修复点）
- GIVEN `proposal-approved.md` 两段都有内容 WHEN helper 调用 THEN 返回两段合并去重后的 entries（不重复）

**Out of Scope**:

- 不修改 `proposal-approved.md` 数据结构（保持 git tracked 历史不变）
- 不修改 `## 已批准提案` vs `## 已实施` 语义定义（保留两段含义）
- 不动 `detect-suggestions-approved-inconsistency`（已实施，互补关系）
- 不动 `skills/propose/scripts/update_proposal_status.py` 的迁移逻辑
- 不修复其他类似的 proposal 文件解析 bug（如果存在，独立提案跟进）
- 不创建新 CLI 命令（helper 内部使用，不暴露 rddf 命令）

## Capabilities

- MUST helper 函数签名：`parse_approved_proposals(path: str) -> list[str]`，纯函数无副作用
- MUST helper 放 `skills/_lib/parse_approved.py`（与 `_lib/state.sh` 风格一致）
- MUST 3 个调用点使用 Oracle C1 safe 模式（env var 传递文件路径，不用 bash `$VAR` 字符串插值）
- MUST helper 路径在 3 个脚本中保持一致（避免路径漂移，参考 AGENTS.md Round A 修复 `roadmap_exists` 失效教训）
- MUST NOT 修改 `proposal-approved.md` 文件结构（保持 git tracked 历史兼容）
- MUST NOT 改变 `## 已批准提案` vs `## 已实施` 语义定义
- MUST NOT 在 helper 内部打开文件写入（只读 helper）
- SHOULD 加 docstring 说明 helper 的意图 + 当前为全文匹配的设计选择 + 与 `detect-suggestions-approved-inconsistency` 的关系
- SHOULD helper 输出按文件出现顺序排序（确定性输出，便于测试）
- SHOULD helper 返回值去重（防止同 name 在两段都出现的边角 case）

## Impact

- MUST helper 函数签名：`parse_approved_proposals(path: str) -> list[str]`，纯函数无副作用
- MUST helper 放 `skills/_lib/parse_approved.py`（与 `_lib/state.sh` 风格一致）
- MUST 3 个调用点使用 Oracle C1 safe 模式（env var 传递文件路径，不用 bash `$VAR` 字符串插值）
- MUST helper 路径在 3 个脚本中保持一致（避免路径漂移，参考 AGENTS.md Round A 修复 `roadmap_exists` 失效教训）
- MUST NOT 修改 `proposal-approved.md` 文件结构（保持 git tracked 历史兼容）
- MUST NOT 改变 `## 已批准提案` vs `## 已实施` 语义定义
- MUST NOT 在 helper 内部打开文件写入（只读 helper）
- SHOULD 加 docstring 说明 helper 的意图 + 当前为全文匹配的设计选择 + 与 `detect-suggestions-approved-inconsistency` 的关系
- SHOULD helper 输出按文件出现顺序排序（确定性输出，便于测试）
- SHOULD helper 返回值去重（防止同 name 在两段都出现的边角 case）

## Acceptance

- 单元测试覆盖 helper 4 个 case：file 不存在 / file 空 / file 有 `## 已批准提案` 段 / file 有 `## 已实施` 段
- 单元测试覆盖混合场景：两段都有内容时去重
- 在本仓库跑 `design_proposal_review.sh` → 列出 **0 个**待审查（修复前误列 3 个）
- 在本仓库跑 `rddf dashboard` → approved 数量显示 **122**（修复前显示 0）
- 现有 51 个 `.rddf/plans/*.md` / 184 个 `openspec/changes/archive/` / 23 个 `docs/adr/ADR-*.md` 不受影响
- 新增 bats integration 测试覆盖 3 个调用点的修复：
  - `tests/integration/test_design_proposal_review_no_false_pending.bats`
  - `tests/integration/test_scan_state_approved_count.bats`
  - `tests/integration/test_propose_change_approved_check.bats`
- CI 全绿（`./test.sh --quick` 通过，~45s）
- 不引入新依赖（仅 stdlib `re` + `pathlib`）
- 改动行数 < 100（净增，遵守 _lib 提取的极简原则）

