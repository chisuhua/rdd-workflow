# add-skill-registration-checklist

**优先级**: P2 | **来源**: 2026-08-03 extract-rdd-env-check-from-guide-arch 会话复盘
**阶段**: default | **分类**: core-test
**类型**: refactor

## 架构依据

- **2026-08-03 会话实测**: `extract-rdd-env-check` change 新增第 18 个 skill 后，`test_doc_contracts.py::test_install_description_skill_count_matches_disk` 失败——`skills/INSTALL.md` 声明"全部 17 个子技能"，磁盘实际 18 个。需人工搜索 `17 个` 并更新，流程无指引。
- **断言容差掩盖缺陷**: `test_doc_contracts.py::test_package_json_skills_count_within_delta` 使用 `len(pkg["skills"]) <= disk + 2` 容差断言，导致 package.json 未注册新 skill（16 ≤ 18 通过）时测试仍 GREEN——漂移被静默容忍。
- **多文件契约**: 新增 skill 需同步 `skills/INSTALL.md`（计数 + 子技能表）、`package.json`（skills 数组）、`tests/smoke.bats`（frontmatter 校验）、`USAGE.md`（可选）、`docs/change-quality-guide.md`。当前仅 test_doc_contracts 捕获部分漂移。
- **既有模式**: 仓库已有 `tests/integration/test_skill_metadata_consistency.bats`（package.json ↔ skills/ ↔ smoke.bats 一致性），本提案在其基础上扩展。

## 范围

- **In Scope**:
  - 在 `docs/change-quality-guide.md` 增加"新增 skill 注册 checklist"章节（5 项：INSTALL.md 计数 / INSTALL.md 子技能表 / package.json skills 数组 / smoke.bats frontmatter / USAGE.md）
  - 收紧 `test_doc_contracts.py::test_package_json_skills_count_within_delta`：从 `<= disk + 2` 改为 `== disk`（精确匹配）
  - `test_doc_contracts.py` 增加断言：INSTALL.md 子技能表行数 == 磁盘 SKILL.md 数（当前只断言描述中的总数）
  - 更新 `tests/integration/test_skill_metadata_consistency.bats` 使新 skill 自动纳入（动态 glob，不硬编码）
  - 添加 2 个 bats/unit 用例：INSTALL.md 子技能表计数一致 / package.json 精确匹配
- **Out Scope**:
  - 不实现新增 skill 的自动脚手架（创建 skill 目录的模板化）——留作 follow-up
  - 不修改 `skills/INSTALL.md` 的安装逻辑本身
  - 不处理非 skill 类新文件（如新增 scripts/ 辅助脚本）的注册
  - 不引入 pre-commit hook 强制校验（CI 门控已覆盖）

## 关键场景

- **GIVEN** 开发者新增 `skills/rdd-env-check/`（含 SKILL.md）
  **WHEN** 运行 `python3 -m pytest tests/unit/test_doc_contracts.py -q`
  **THEN** INSTALL.md 描述计数断言失败，明确提示"INSTALL.md claims 17 skills, disk has 18"，指引更新 checklist

- **GIVEN** 开发者新增 skill 但忘记更新 `package.json` skills 数组
  **WHEN** 运行 test_doc_contracts
  **THEN** `== disk` 精确断言失败（不再被 `<= disk + 2` 容差掩盖）

- **GIVEN** 开发者新增 skill 且同步了全部 5 项注册
  **WHEN** 运行全量测试
  **THEN** 所有契约测试 GREEN，无漂移

- **GIVEN** 开发者查阅 `docs/change-quality-guide.md`
  **WHEN** 准备新增 skill
  **THEN** 能看到完整注册 checklist（5 项），按序执行

## 技术约束

- MUST 保持 test_doc_contracts 的磁盘计数逻辑不变（`_count_skill_files`：顶层 md + 子目录 SKILL.md）
- MUST 精确断言 `== disk`（删除 `+2` 容差），除非有明确的兼容性理由
- MUST 新 checklist 与既有 `test_skill_metadata_consistency.bats` 互补，不重复实现
- MUST NOT 修改既有 18 个 skill 的注册（只改校验逻辑与文档）
- SHOULD checklist 用可勾选任务格式（与 plan 的 `- [ ]` 风格一致）

## 验收标准

- `test_doc_contracts.py` 全部用例 GREEN（精确匹配后无既有 skill 漂移——当前 18 个 skill 与 INSTALL.md 对齐）
- package.json 未注册 skill 时测试 FAIL（不再被容差掩盖）——用临时移除验证
- INSTALL.md 子技能表行数与磁盘 SKILL.md 数一致断言生效
- `docs/change-quality-guide.md` 含 5 项注册 checklist
- 新增 2 个测试用例 GREEN
- 既有 100 个 improvement 相关测试零回归
