# fix-skill-count-and-table-schema

## Why

Wave 完成后审计发现 2 项 rdd-doctor WARNING(预存债务):

1. **G1 (测试失败)**: `tests/unit/test_doc_contracts.py` 3 个失败(INSTALL.md 24 vs disk 25)。根因:`_count_skill_files()` 同时计入 INSTALL.md(顶层 installer)和 24 个 SKILL.md 文件,得 25;但 INSTALL.md/package.json 声称 24(只算 sub-skills)。测试逻辑比较了"总文件数"vs"sub-skill 数",这是定义不一致。

2. **G2 (schema 漂移)**: `proposal-approved.md` lines 108-116 有 9 行仅 3 列(`提案 | 优先级 | 完成时间`),而 `proposal_table_check.py` schema 要求 4 列(`提案 | 优先级 | 完成时间 | 状态`)。前 7 行(已实施条目)有 4 列含 `状态: 已实施`,后 9 行(已批准未实施)缺 `状态` 列。

**严重后果**:
- G1:3 个 CI 测试持续红,掩盖真新增失败
- G2:`bash skills/rdd-doctor/scripts/doctor.sh` 报 16 个 WARNING,使基线噪音膨胀,降低信号噪声比

## What Changes

**In Scope**:

- **修复** `_count_skill_files()` — 仅计 sub-skill `SKILL.md`(排除 INSTALL.md),使 disk count 与 INSTALL.md/package.json 声称的 24 一致
- **添加** `状态` 列到 `proposal-approved.md` lines 108-116(9 行已批准未实施条目),值统一为 `已批准`
- **不**改 INSTALL.md/package.json 声称的 24(它们正确指 sub-skill 数量)
- **不**改 rdd-doctor `proposal_table_check.py` 的 schema 定义(4 列是正确的)
- **不**碰 `.rddf/state/` 残留文件(已在 cleanup-pre-existing-debt 处理)
- **不**改其他 doc_contracts 测试(general/spec, ADR index, npm test trap — 全部通过)

### 关键场景

### 场景 A:测试通过

**GIVEN** `_count_skill_files()` 修正后
**WHEN** `python3 -m pytest tests/unit/test_doc_contracts.py -v`
**THEN**
- `test_install_description_skill_count_matches_disk` ✅
- `test_package_json_skills_count_within_delta` ✅
- `test_install_sub_skill_table_count_matches_disk` ✅

### 场景 B:rdd-doctor WARNING 减少

**GIVEN** proposal-approved.md lines 108-116 补 `状态` 列
**WHEN** `bash skills/rdd-doctor/scripts/doctor.sh`
**THEN**
- `[proposal-table] proposal-approved.md` WARNING 从 16 → 0
- 整体 WARNING 84 → 68(去掉 16)

### 场景 C:INSTALL.md + package.json 不动

**GIVEN** INSTALL.md 声称"24 个子技能",package.json skills 数组含 24 条
**WHEN** 修复完成
**THEN** 两文件**不**修改(它们正确指 sub-skill 数)

**Out of Scope**:

- (no items specified)

## Acceptance

### 功能验收

- [ ] **AC-1**:`tests/unit/test_doc_contracts.py::test_install_description_skill_count_matches_disk` 通过
- [ ] **AC-2**:`tests/unit/test_doc_contracts.py::test_package_json_skills_count_within_delta` 通过
- [ ] **AC-3**:`tests/unit/test_doc_contracts.py::test_install_sub_skill_table_count_matches_disk` 通过
- [ ] **AC-4**:`proposal-approved.md` 所有数据行(linked)为 4 列
- [ ] **AC-5**:rdd-doctor `[proposal-table] proposal-approved.md` WARNING 数为 0
- [ ] **AC-6**:整体 rdd-doctor WARNING 84 → 68

### 测试

- [ ] 1 unit 测试 (counter 排除 INSTALL.md)
  - `tests/unit/test_doc_contracts.py` 修改 `_count_skill_files()`,加 inline comment
- [ ] 1 regression 测试 (proposal 表 4 列)
  - `tests/unit/test_proposal_table_schema.py` 新建,验证 `proposal-approved.md` 每个数据行 4 列

### 不变量

- INSTALL.md 声称的"24 个子技能"**不**变
- package.json skills 数组长度 24 **不**变
- `_count_skill_files()` 行为变更为"仅 sub-skill",inlined comment 说明
- `proposal_table_check.py` schema(4 列)**不**变