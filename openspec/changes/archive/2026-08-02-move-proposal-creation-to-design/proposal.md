# move-proposal-creation-to-design

## Why

v2.1 四阶段架构（arch → design → plan → ship）落地后，`guide-design` 成为"哑管道"：批准动作仅向 `proposal-approved.md` 追加一行表格（`approve_proposal.sh` → `state.sh::append_approved`），无内容审查、不触碰 openspec，审批与 change 实体创建脱节。与此同时，openspec proposal 的实质内容在 design 审批时已全部具备——`improvements/<name>.md` 的 5 段（架构依据/范围/关键场景/技术约束/验收标准）经 brainstorm 逐段确认，信息量足以转换为完整 openspec `proposal.md`，但当前流程把它降级为占位骨架（`<skeleton motivation>`），到 plan 阶段才填实。结果是：审批时无实质 proposal 可审，design-done 门控只能检查状态列枚举，提案内容质量问题要到 guide-plan 甚至 plan-done 才暴露，反馈链路过长。

依据：ADR-0003（三阶段架构，v2.1 已漂移为四阶段，本次再分配需另起 ADR-0025 记录）、ADR-0016（handoff 发现契约）、ADR-0017（rddf-session 绑定）、ADR-0019（change-arch 对齐检查范式）、已归档 change `add-propose-content-review`（4 维 Oracle 内容审查原型）。

## What Changes

**In Scope**:

- **approve 动作升级**（`skills/guide-design/scripts/approve_proposal.sh` + `guide-design/SKILL.md`）：批准后调 `openspec new change <name>` 脚手架 → AI 将 `improvements/<name>.md` 5 段内容转换为**完整** `proposal.md`（Why ← 架构依据；What Changes ← 范围 + 关键场景；Capabilities/Impact ← 技术约束涉及面）→ 用户确认后落盘 → 写 `roadmap-meta.yaml`（含 `change_type`，从 improvements 头部 `**类型**` 映射）→ `iteration.json`（status=planned）
- **design 阶段两层内容审查**：
  - improvements 层：5 段格式完整性、架构依据含 ≥1 个 ADR 引用、验收标准可量化、`**阶段**`/`**分类**` 字段存在
  - openspec proposal 层（生成后）：`propose_quality_check` 中适用于 proposal 的 3 项（长度 ≥500 去骨架标记、ADR 引用 ≥1、In/Out Scope）+ `openspec validate <name> --json` 原生校验
  - 默认 warning 级，`STRICT_DESIGN_GATE=yes` 升级为阻断；可叠加 Oracle 4 维审查（`SKIP_CONTENT_REVIEW=yes` 可跳过）
- **元数据来源修正**：骨架创建的 `phase`/`category` 从 `improvements/<name>.md` 头部读取（禁止硬编码 default/general）；`parent_feature` 在 design 审查时询问并透传
- **`.design-handoff.json` schema bump 至 v2**：新增 `changes_pre_created: [<name>, ...]` 字段；`plan_intake.sh::check_design_handoff` 兼容 v1/v2
- **`guide-plan` 适应性调整**：intake 识别 `changes_pre_created` 跳过 change 创建；Phase 2.5 fill 范围收缩为 specs/design/tasks（proposal 已完成，`openspec status --json` 工件 DAG 自然显示 proposal=done）
- **新 ADR-0025**：记录 design/plan 职责再分配（不修改 ADR-0003）
- **单元测试 + bats 集成测试**

**Out of Scope**：design 阶段不生成 tasks.md/design.md/specs（留在 plan fill；`propose_quality_check` 的 tasks ≥2、roadmap 对齐 2 项相应留在 plan_done）；不动 `update_roadmap_meta` 完整分支 / `update_iteration_proposed` / Phase 3 deps / plan-done 门控；不改 `proposal-suggestions.md`/`proposal-approved.md` 表格格式；不引入 iteration.json 新状态值；`create_skeleton_change()` 骨架模式保留为 `SKIP_DESIGN_HANDOFF=yes` 存量路径 fallback；不修改 ADR-0003。

## Capabilities

### New Capabilities

- `design-proposal-creation`：design 审批批准即创建完整 openspec change（脚手架 + 完整 proposal.md + roadmap-meta.yaml + iteration.json planned），含"生成 → 用户确认 → 落盘"的人控编排
- `design-content-review`：两层内容审查（improvements 5 段审查 + openspec proposal 质量检查 + openspec validate），warning/strict 双模式

### Modified Capabilities

- `workflow-design-phase`：design-handoff schema v1 → v2（新增 `changes_pre_created`）；approve 动作从纯状态流转升级为"审查 + 创建"
- `workflow-plan-phase`：plan intake 消费 `changes_pre_created` 跳过已建 change；Phase 2.5 fill 范围收缩为 specs/design/tasks

## Impact

- **受影响文件**：`skills/guide-design/SKILL.md`、`skills/guide-design/scripts/approve_proposal.sh`、`skills/guide-design/scripts/design_proposal_review.sh`、`skills/guide-design/scripts/write_design_handoff.py`、`skills/_lib/schemas/design_handoff_schema.json`（v2）、`skills/guide-plan/scripts/plan_intake.sh`（v1/v2 兼容 + changes_pre_created 消费）、`skills/guide-plan/SKILL.md`（fill 范围）、`skills/propose/scripts/propose_change.py`（扩展完整 proposal 模式）、`docs/adr/ADR-0025-*.md`（新增）、`tests/unit/`、`tests/integration/`
- **兼容性**：`SKIP_DESIGN_HANDOFF=yes` 存量路径行为不变；design-handoff v1 仍被 plan_intake 接受；骨架模式保留
- **硬约束**：批准动作幂等；proposal.md 经用户确认才落盘；env-var 传参（Oracle C1）；design 阶段只写 iteration status=planned；design 的 propose_quality_check 只调 proposal 相关 3 项（tasks/roadmap 对齐 2 项对象在设计时不存在，前移必然误报）

## Acceptance

- [ ] 批准后 change 目录含 `.openspec.yaml` + 完整 `proposal.md`（≥500 字符、含 ADR 引用与 In/Out Scope）+ `roadmap-meta.yaml`（含 `change_type`）
- [ ] 完整 proposal.md 经用户确认环节后才落盘
- [ ] design 两层审查运行；`STRICT_DESIGN_GATE=yes` 时不达标阻断
- [ ] `.design-handoff.json` version=2 且含 `changes_pre_created`；plan_intake 兼容 v1/v2
- [ ] `guide-plan` 对预建 change 零重复创建，fill 仅处理 specs/design/tasks
- [ ] phase/category 来自 improvements 头部字段（非硬编码）
- [ ] plan_done 的 `propose_quality_check` 5 项行为无回归
- [ ] `SKIP_DESIGN_HANDOFF=yes` 存量骨架路径行为不变
- [ ] ADR-0025 已采纳；单元 + bats 测试通过，CI 全绿
