# add-brainstorm-hardgate-enforcement — Implementation Tasks

- [x] 新建 `skills/rdd-workflow-brainstorm/scripts/pre_create_brainstorm_check.sh` HARD-GATE 校验 helper
- [x] 校验 5 个核心 section：## 架构依据 / ## 范围 / ## Capabilities / ## Impact / ## 验收标准
- [x] 校验 ## Why / ## What Changes 标题与 ## Acceptance 复选框（≥3 项）
- [x] 校验 **主题**: 字段存在且匹配至少 1 个 roadmap 主题
- [x] 将 HARD-GATE pre-create gate 接入 add-improve 入口（from_roadmap.sh / from_issue.sh）并更新 SKILL.md
- [x] 新增 `tests/integration/test_brainstorm_hardgate.bats`（5 用例）全部通过
