# fix-disk-count-semantic-conflict — Design

## Context

`tests/unit/test_doc_contracts.py` 的 `_count_skill_files()` 与 `tests/integration/test_skill_metadata_consistency.bats` 的 disk count 语义**不一致**:

- `_count_skill_files()`: 只数 `skills/*/SKILL.md`(子目录),**不包含** `skills/INSTALL.md`(顶层)。
- `test_skill_metadata_consistency.bats`: 数 `skills/*.md`(顶层 INSTALL.md) + `skills/*/SKILL.md`(子目录),**包含** INSTALL.md。
后果:

- 2026-08-27 ship sync-package-skills-to-disk 时,两个 test 在不同阶段产生不同期望,bats 误报"package.json 25 entries 但 disk 26 (含 INSTALL)"。

## Goals / Non-Goals

**Goals:**
- `_count_skill_files()` 改为包含 `skills/INSTALL.md`(或显式排除,但与其他语义一致)。
- `test_skill_metadata_consistency.bats` 保持现有语义(已含 INSTALL.md)。
- 更新 `test_doc_contracts.py` 的注释和 docstring 解释 INSTALL 是否计入。
- 同步 `tests/integration/test_doc_contracts.py`(如有)和其他引用。
- GIVEN 27 个 `skills/<name>/SKILL.md` + 1 个 `skills/INSTALL.md`

**Non-Goals:**
- 修复 `test_doc_contracts.py` 的 `_count_skill_files()` 已有的 historical "24" 数字(应随当前数据更新)。
- 修改 `package.json::skills[]` 的语义(已正确)。

## Decisions

### 1. MUST: 两个 test 用相同的 disk count 语义

Implementation MUST satisfy this constraint.

### 2. MUST: `package.json::skills[]` 包含 `INSTALL` 字符串

Implementation MUST satisfy this constraint.


## Risks / Trade-offs

- No identified risks beyond standard implementation discipline.

- **SHOULD**: SHOULD: 提供 `_count_skill_files(include_top_level: bool)` 参数供其他 test 复用