# OpenSpec Change Quality Guide

> 本文档定义 OpenSpec change 的质量标准，作为提案创建和审查的参考。
>
> **与 Plan B 的关系**: `skills/propose/scripts/propose_quality_check.py` 实现了本文档中定义的质量检查的自动化版本。
> **与 ADR-0019 的关系**: 反模式清单以 ADR-0019 为准，本文档不重复。

## 质量等级

### 🥉 Bronze (基本合格)

通过 `propose_quality_check.py` 全部 5 项检查：

- proposal.md ≥ 500 字符（去除骨架模板标记后）
- proposal.md 引用 ≥ 1 个 ADR
- proposal.md 含 In Scope / Out of Scope 章节
- tasks.md 含 ≥ 2 个任务
- change 在 roadmap.md 中有映射

Bronze 是**唯一被强制执行**的等级。设置 `STRICT_PROPOSE_GATE=yes`
（或加 `--strict` 参数）会将这 5 项 warning 升级为 error，CI 可据此
阻断不合规提案。

### 🥈 Silver (良好)

在 Bronze 基础上附加：

- design.md 包含架构决策和备选方案
- 提案描述包含关键场景（GIVEN/WHEN/THEN）
- 验收标准可量化

### 🥇 Gold (优秀)

在 Silver 基础上附加：

- 变更包含集成测试
- proposal-suggestions.md 条目已更新
- deps 分析已运行且 blocker 已标注

## 阈值速查表

| 检查项 | 阈值 | Plan B 实现 | 备注 |
|--------|------|-------------|------|
| proposal 长度 | ≥ 500 字符 | `check_proposal_length()` | 会剥离骨架文本 |
| ADR 引用 | ≥ 1 个 | `check_adr_references()` | - |
| 范围章节 | In Scope + Out Scope | `check_scope_sections()` | - |
| 任务数 | ≥ 2 个 | `check_tasks_completeness()` | - |
| Roadmap 对齐 | 出现变更名 | `check_roadmap_alignment()` | - |
| 反模式清单 | 见 ADR-0019 | - | 单一真相源，本文档不重复 |

> 阈值与 `propose_quality_check.py` 中的常量（`MIN_PROPOSAL_LENGTH=500`、
> `MIN_TASKS_COUNT=2`、`_ADR_PATTERN=ADR-\d{4}`）一一对应。若 Plan B 调整
> 阈值，本表必须在同一 PR 内同步更新。

## 使用方式

### 提案作者

1. 起草 proposal.md 时对照 Bronze 5 项检查；
2. 对架构性变更，对照 Silver 增补 design.md 的备选方案与场景；
3. 对影响多个 change 的变更，对照 Gold 运行 deps 分析。

### 审查者

- **Bronze 不通过** → 直接要求作者修正（CI 会在 `STRICT_PROPOSE_GATE=yes` 时阻断）；
- **Bronze 通过但 Silver 缺失** → 提示，不阻断；
- **Gold 全部满足** → 鼓励性反馈。

> 本指南**非强制**：Silver 和 Gold 是质量愿景，不是 gate。不要用它来
> 否决已经通过 Bronze 的提案。

## 新增 skill 注册 checklist

每新增一个 `skills/<name>/SKILL.md`（或顶层 `skills/<name>.md`），按顺序核对以下五项，否则本地 `python3 -m pytest tests/unit/test_doc_contracts.py -q` 与 `bats tests/integration/test_skill_metadata_consistency.bats` 会失败：

- [ ] `skills/INSTALL.md` 描述中的 `全部 N 个子技能` 与磁盘 `_count_skill_files()` 完全一致
- [ ] `skills/INSTALL.md` 的子技能表中追加一行 `| \`<name>\` | <用途说明> |`
- [ ] `package.json` 的 `skills[]` 数组按字母顺序追加 `<name>`
- [ ] `tests/smoke.bats` 中“all skill files exist (dynamic)”/“v1.x baseline skills still present”用例若需静态示例，则保留与新技能名同步
- [ ] `USAGE.md` 中如出现计数或示例，须同步刷新（CI 暂未强制，文档层面维护即可）

自动化校验覆盖了第 1、2、3 项；第 4、5 项为辅助检查项，确保示例与文档不会漂移。

## 相关文档

- `skills/propose/scripts/propose_quality_check.py` - 自动检查工具（Plan B）
- `docs/adr/ADR-0019-change-arch-alignment.md` - 反模式清单（单一真相源）
- `roadmap.md` - 路线图与变更映射
- `AGENTS.md` - 项目文档索引
