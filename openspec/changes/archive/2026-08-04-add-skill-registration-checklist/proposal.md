# add-skill-registration-checklist

## Why

- **2026-08-03 会话实测**: `extract-rdd-env-check` change 新增第 18 个 skill 后，`test_doc_contracts.py::test_install_description_skill_count_matches_disk` 失败——`skills/INSTALL.md` 声明"全部 17 个子技能"，磁盘实际 18 个。需人工搜索 `17 个` 并更新，流程无指引。
- **断言容差掩盖缺陷**: `test_doc_contracts.py::test_package_json_skills_count_within_delta` 使用 `len(pkg["skills"]) <= disk + 2` 容差断言，导致 package.json 未注册新 skill（16 ≤ 18 通过）时测试仍 GREEN——漂移被静默容忍。
- **多文件契约**: 新增 skill 需同步 `skills/INSTALL.md`（计数 + 子技能表）、`package.json`（skills 数组）、`tests/smoke.bats`（frontmatter 校验）、`USAGE.md`（可选）、`docs/change-quality-guide.md`。当前仅 test_doc_contracts 捕获部分漂移。
- **既有模式**: 仓库已有 `tests/integration/test_skill_metadata_consistency.bats`（package.json ↔ skills/ ↔ smoke.bats 一致性），本提案在其基础上扩展。

## What Changes

**In Scope**:

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

### 关键场景

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

**Out of Scope**:

- design 阶段不生成 tasks.md / design.md / specs (留在 plan fill)
- 不修改 ADR-0003 (另起 ADR 记录本次职责再分配)


## Capabilities

- `design-proposal-creation`: design 审批批准即创建完整 openspec change
- `design-content-review`: 两层内容审查 (improvements 5 段 + openspec validate), warning / strict 双模式


## Impact

- **受影响文件**: `skills/guide-design/SKILL.md` + 4 个 scripts, `skills/guide-plan/scripts/plan_intake.sh`, `docs/adr/ADR-0025-*.md` (新增)
- **兼容性**: `SKIP_DESIGN_HANDOFF=yes` 存量路径行为不变
- **硬约束**: 批准动作幂等; env-var 传参 (Oracle C1)


## Acceptance

- `test_doc_contracts.py` 全部用例 GREEN（精确匹配后无既有 skill 漂移——当前 18 个 skill 与 INSTALL.md 对齐）
- package.json 未注册 skill 时测试 FAIL（不再被容差掩盖）——用临时移除验证
- INSTALL.md 子技能表行数与磁盘 SKILL.md 数一致断言生效
- `docs/change-quality-guide.md` 含 5 项注册 checklist
- 新增 2 个测试用例 GREEN
- 既有 100 个 improvement 相关测试零回归

