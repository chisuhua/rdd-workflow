# fix-disk-count-semantic-conflict

**优先级**: P1 | **来源**: 2026-08-27 ship audit (sync-package-skills-to-disk ship 时 test_doc_contracts.py 与 test_skill_metadata_consistency.bats 对 disk count 语义不一致,一个含 INSTALL.md 一个不含,反复 3 次才定位)
**阶段**: phase-2 | **分类**: docs
**类型**: improvement

**主题**: 2026-08-26 文档与代码一致性审计后续修复

## 架构依据

`tests/unit/test_doc_contracts.py` 的 `_count_skill_files()` 与 `tests/integration/test_skill_metadata_consistency.bats` 的 disk count 语义**不一致**:

- `_count_skill_files()`: 只数 `skills/*/SKILL.md`(子目录),**不包含** `skills/INSTALL.md`(顶层)。
- `test_skill_metadata_consistency.bats`: 数 `skills/*.md`(顶层 INSTALL.md) + `skills/*/SKILL.md`(子目录),**包含** INSTALL.md。

后果:

- 2026-08-27 ship sync-package-skills-to-disk 时,两个 test 在不同阶段产生不同期望,bats 误报"package.json 25 entries 但 disk 26 (含 INSTALL)"。
- 实际调试: 反复手动对齐两个 test 的期望(3 次)才找到根本原因。
- 修复方案: 把 INSTALL.md 计入 disk(因为它是 skill metadata 的一部分)。

期望行为: 两个 test 用一致的 disk count 语义。

## 范围

**In Scope**:

- `_count_skill_files()` 改为包含 `skills/INSTALL.md`(或显式排除,但与其他语义一致)。
- `test_skill_metadata_consistency.bats` 保持现有语义(已含 INSTALL.md)。
- 更新 `test_doc_contracts.py` 的注释和 docstring 解释 INSTALL 是否计入。
- 同步 `tests/integration/test_doc_contracts.py`(如有)和其他引用。

**Out of Scope**:

- 修复 `test_doc_contracts.py` 的 `_count_skill_files()` 已有的 historical "24" 数字(应随当前数据更新)。
- 修改 `package.json::skills[]` 的语义(已正确)。

## 关键场景

- GIVEN 27 个 `skills/<name>/SKILL.md` + 1 个 `skills/INSTALL.md`
  WHEN `_count_skill_files()` 调用
  THEN 返回 28(对齐 `test_skill_metadata_consistency.bats`)

- GIVEN `package.json::skills[]` 28 entries (含 INSTALL)
  WHEN 两个 test 都运行
  THEN 两者都 PASS(语义一致)

## 技术约束

- MUST: 两个 test 用相同的 disk count 语义
- MUST: `package.json::skills[]` 包含 `INSTALL` 字符串
- MUST NOT: 修改 `bats` test 的现有 semantics(它已经包含 INSTALL)
- SHOULD: 提供 `_count_skill_files(include_top_level: bool)` 参数供其他 test 复用

## 验收标准

- [ ] `_count_skill_files()` 包含 `skills/INSTALL.md`(返回 28 for master)
- [ ] `_count_skill_files()` 的 docstring 明确说明计入/排除策略
- [ ] 新增 unit test 验证两个 test 用一致的 disk count 语义
- [ ] `package.json::skills[]` 确认包含 `INSTALL` 字符串(28 entries)
- [ ] 运行 `tests/unit/test_doc_contracts.py` 和 `bats tests/integration/test_skill_metadata_consistency.bats`,两者都 PASS
- [ ] CI 跑 `./test.sh --full --regression` 不增加新 failure

## 相关

- 关联: `sync-package-skills-to-disk` proposal (本修复由其 ship 触发)
- 来源: 2026-08-27 全链路工作流审计
- 文件: `tests/unit/test_doc_contracts.py` `_count_skill_files()` 函数
