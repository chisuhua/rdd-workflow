## Context

**背景**: 新增 skill 需要同步多文件契约（`skills/INSTALL.md` 计数 + 子技能表、`package.json` skills 数组、`tests/smoke.bats` frontmatter 校验、`USAGE.md`、`docs/change-quality-guide.md`），但当前流程无指引，且校验存在容差掩盖缺陷。2026-08-03 会话实测：`extract-rdd-env-check` change 新增第 18 个 skill 后 `test_install_description_skill_count_matches_disk` 失败——`skills/INSTALL.md` 声明"全部 17 个子技能"，磁盘实际 18 个，需人工搜索更新。

**当前状态**: `test_doc_contracts.py::test_package_json_skills_count_within_delta` 使用 `len(pkg["skills"]) <= disk + 2` 容差断言（L76），package.json 未注册新 skill（16 ≤ 18 通过）时测试仍 GREEN——漂移被静默容忍。`test_install_description_skill_count_matches_disk`（L63）只断言 INSTALL.md 描述中的总数，未校验子技能表行数。仓库已有 `tests/integration/test_skill_metadata_consistency.bats` 做 package.json ↔ skills/ ↔ smoke.bats 一致性校验，但断言集是硬编码的 10 个 skill 名单。

**约束**:
- MUST 保持 test_doc_contracts 的磁盘计数逻辑不变（`_count_skill_files`：顶层 md + 子目录 SKILL.md）
- MUST 精确断言 `== disk`（删除 `+2` 容差），除非有明确的兼容性理由
- MUST 新 checklist 与既有 `test_skill_metadata_consistency.bats` 互补，不重复实现
- MUST NOT 修改既有 18 个 skill 的注册（只改校验逻辑与文档）
- SHOULD checklist 用可勾选任务格式（与 plan 的 `- [ ]` 风格一致）

## Goals / Non-Goals

**Goals**:
- 在 `docs/change-quality-guide.md` 增加"新增 skill 注册 checklist"章节（5 项：INSTALL.md 计数 / INSTALL.md 子技能表 / package.json skills 数组 / smoke.bats frontmatter / USAGE.md）
- 收紧 `test_doc_contracts.py::test_package_json_skills_count_within_delta`：从 `<= disk + 2` 改为 `== disk`（精确匹配）
- `test_doc_contracts.py` 增加断言：INSTALL.md 子技能表行数 == 磁盘 SKILL.md 数（当前只断言描述中的总数）
- 更新 `tests/integration/test_skill_metadata_consistency.bats` 使新 skill 自动纳入（动态 glob，不硬编码）
- 添加 2 个 bats/unit 用例：INSTALL.md 子技能表计数一致 / package.json 精确匹配

**Non-Goals**:
- 不实现新增 skill 的自动脚手架（创建 skill 目录的模板化）——留作 follow-up
- 不修改 `skills/INSTALL.md` 的安装逻辑本身
- 不处理非 skill 类新文件（如新增 scripts/ 辅助脚本）的注册
- 不引入 pre-commit hook 强制校验（CI 门控已覆盖）

## Decisions

### 决策 1: 精确断言 `== disk` 替代容差 `<= disk + 2`

`test_package_json_skills_count_within_delta` 改为 `len(pkg["skills"]) == disk`。当前 18 个 skill 与 package.json 对齐，收紧后无既有漂移；package.json 未注册新 skill 时测试立即 FAIL，不再被容差掩盖。`_count_skill_files` 计数逻辑保持不变。

### 决策 2: INSTALL.md 子技能表行数独立断言

新增断言解析 `skills/INSTALL.md` 的子技能表（Markdown 表格行），校验表行数 == 磁盘 SKILL.md 数。与既有 `test_install_description_skill_count_matches_disk`（描述总数）互补：一个锁总数，一个锁表完整性。表行解析规则与磁盘计数使用同一 `_count_skill_files()` 口径。

### 决策 3: 注册 checklist 写入 change-quality-guide.md，采用可勾选格式

在 `docs/change-quality-guide.md` 新增"新增 skill 注册 checklist"章节，5 项以 `- [ ]` 可勾选格式列出（INSTALL.md 计数、INSTALL.md 子技能表、package.json skills 数组、smoke.bats frontmatter、USAGE.md），与 plan 的 `- [ ]` 风格一致。不实现自动脚手架（out of scope）。

### 决策 4: metadata 一致性 bats 改为动态 glob

`tests/integration/test_skill_metadata_consistency.bats` 的硬编码 skill 名单改为从磁盘动态 glob（`skills/*/SKILL.md` + `skills/*.md`），新 skill 自动纳入断言面，无需每次新增 skill 时改测试。保留与既有 smoke.bats frontmatter 校验的互补关系，不重复实现。

## Risks

- **收紧断言导致既有漂移浮现**: 若当前 package.json 与磁盘本就不对齐，`== disk` 立即 FAIL → 验收标准已锁定"当前 18 个 skill 与 INSTALL.md/package.json 对齐"，先验证再提交
- **子技能表解析误判**: INSTALL.md 表格含非 skill 行（如分组标题）→ 解析时按表格分隔符精确过滤，仅计 skill 链接行；解析失败时跳过断言并告警而非误报
- **动态 glob 扩大断言面**: 硬编码 → 动态后历史遗留目录被纳入 → 测试先以当前磁盘状态验证零漂移，再切动态 glob
- **checklist 与测试重复**: 文档 checklist 与测试断言职责重叠 → 明确 checklist 面向"开发者动作指引"，测试面向"机器校验"，各自独立
- **回归风险**: 修改既有测试断言逻辑影响其他用例 → 仅改动目标函数与新增用例，其余 test_doc_contracts 用例不动

## Open Questions

- 无；断言收紧、表行数校验、checklist 位置与动态 glob 范围均由 proposal 和 improvement source 明确约束。
