# move-proposal-creation-to-design

**优先级**: P1 | **来源**: 架构评审讨论 2026-08-01
**阶段**: v2.1 | **分类**: arch-design
**类型**: refactor
**依赖**: | **特性**:

## 架构依据

1. **v2.1 四阶段架构（arch → design → plan → ship）后，guide-design 是"哑管道"**：批准动作仅向 `proposal-approved.md` 追加一行表格（`skills/guide-design/scripts/approve_proposal.sh` → `state.sh::append_approved`），无内容审查、不触碰 openspec。审批与 change 实体创建脱节。
2. **openspec proposal 的实质内容在 design 审批时已全部具备**：`improvements/<name>.md` 的 5 段（架构依据/范围/关键场景/技术约束/验收标准）经 brainstorm 逐段确认，信息量足以转换为完整 openspec `proposal.md`（Why / What Changes / Capabilities / Impact）。当前流程把它降级为占位骨架（`<skeleton motivation>`），到 plan 阶段才填实——审批时无实质 proposal 可审，反馈链路过长。
3. **design-done 门控只查状态列枚举**（`skills/guide-design/SKILL.md` Phase 4）。已归档的 `add-propose-content-review` change 提供了 4 维 Oracle 内容审查原型（scope 清晰度 / ADR 引用 / 验收可测试性 / 边界），可作为审查机制参考。
4. **openspec v1.7.0 原生提供 `openspec new change <name>` 脚手架**（实测 v1.4.1 已可用），design 阶段调用无版本障碍；`openspec validate <name> --json` 可对完整 proposal 做原生结构校验。
5. **骨架创建基础设施可复用**：`skills/propose/scripts/propose_change.py::create_skeleton_change()` 的幂等守卫、roadmap-meta.yaml 写入、iteration.json 同步逻辑完整，需扩展为"完整 proposal 模式"而非重写。
6. **ADR-0003 三阶段描述已与代码漂移**（2026-07-30 用户决策接受），本次职责再分配应另起 ADR（建议 ADR-0025）记录，而非修改 ADR-0003。

## 范围

- **In Scope**:
  - `approve_proposal.sh` 批准动作升级为：调 `openspec new change <name>` 脚手架 → **AI 将 `improvements/<name>.md` 5 段内容转换为完整 `proposal.md`**（Why ← 架构依据；What Changes ← 范围 + 关键场景；Capabilities/Impact ← 技术约束涉及面）→ 写 `roadmap-meta.yaml`（含 `change_type`，从 improvements 头部 `**类型**` 映射）→ `iteration.json`（status=planned）
  - **approve 动作性质变化**：从纯脚本追加表格行 → AI 内容生成 + 脚本落盘。guide-design SKILL.md 需编排"生成 → 用户确认 → 落盘"步骤（生成内容须经用户确认后才写入，保持审批的人控属性）
  - design 阶段内容审查（两层）：
    - improvements 层：5 段格式完整性、架构依据含 ≥1 个 ADR 引用、验收标准可量化、`**阶段**`/`**分类**` 字段存在
    - openspec proposal 层（生成后）：`propose_quality_check` 中适用于 proposal 的 3 项（长度 ≥500 去骨架标记、ADR 引用 ≥1、In/Out Scope 存在）+ `openspec validate <name> --json` 原生校验
    - 默认 warning 级，`STRICT_DESIGN_GATE=yes` 升级为阻断；可叠加 Oracle 4 维审查（支持 `SKIP_CONTENT_REVIEW=yes` 跳过）
  - 骨架创建的 `phase`/`category` 从 `improvements/<name>.md` 头部读取（禁止硬编码 default/general）；`parent_feature` 在 design 审查时询问并透传
  - `.design-handoff.json` schema bump 至 v2，新增 `changes_pre_created: [<name>, ...]`（现 schema `additionalProperties: false`，必须 bump version）
  - `guide-plan` 适应性调整：intake 识别 `changes_pre_created` 跳过 change 创建；Phase 2.5 fill 范围收缩为 specs / design / tasks（proposal 已完成，`openspec status --json` 工件 DAG 会自然显示 proposal=done——与 `refine-plan-openspec-integration` 提案天然兼容）
  - 新 ADR（建议 ADR-0025）记录 design/plan 职责再分配
  - 单元测试 + bats 集成测试
- **Out Scope**:
  - design 阶段**不生成** tasks.md / design.md / specs（留在 plan Phase 2.5 fill；`propose_quality_check` 的 tasks ≥2、roadmap 对齐 2 项因此也留在 plan——已在 `skills/_lib/gate.py` plan_done 注册，不后移）
  - 不动 `update_roadmap_meta` 完整分支 / `update_iteration_proposed`（status=proposed 语义绑定 deps 分析，留在 plan）
  - 不动 Phase 3 deps / plan-done 门控 / `.plan-handoff.json`
  - 不改 `proposal-suggestions.md` / `proposal-approved.md` 表格格式
  - 不在 `iteration.json` 引入新状态值（design 阶段只写 `planned`）
  - `create_skeleton_change()` 骨架模式保留，作为 `SKIP_DESIGN_HANDOFF=yes` 存量路径的 fallback（不在本提案删除）
  - 不修改 ADR-0003

## 关键场景

- GIVEN 待审提案在 design 审查中按 `y` 批准, WHEN `approve_proposal.sh` 执行, THEN AI 将 improvements 5 段转换为完整 proposal.md 草稿并展示，用户确认后落盘：`openspec/changes/<name>/` 含 .openspec.yaml + **完整** proposal.md + roadmap-meta.yaml（含 change_type），且两层内容审查运行
- GIVEN 生成的完整 proposal.md（≥500 字符、含 ADR 引用、含 In/Out Scope）, WHEN design 审查的 openspec proposal 层运行, THEN `propose_quality_check` 3 项通过且 `openspec validate <name> --json` 通过
- GIVEN `improvements/<name>.md` 缺 5 段之一或架构依据无 ADR 引用且 `STRICT_DESIGN_GATE=yes`, WHEN 批准动作执行, THEN 阻断并列出失败检查项；未设 STRICT 时仅 warning
- GIVEN `improvements/<name>.md` 头部含 `**阶段**: v2.1` / `**分类**: planning`, WHEN 批准创建 change, THEN roadmap-meta.yaml 写入对应值而非 default/general
- GIVEN design-handoff v2 含 `changes_pre_created: ["foo"]`, WHEN `guide-plan` 运行, THEN `foo` 跳过创建，Phase 2.5 fill 仅补 specs/design/tasks（`status --json` 中 proposal=done）
- GIVEN `openspec/changes/<name>/` 已存在, WHEN 批准动作重复执行, THEN 幂等跳过不报错
- GIVEN 存量项目设置 `SKIP_DESIGN_HANDOFF=yes`, WHEN `guide-plan` 运行, THEN 按旧路径在 plan 阶段创建骨架 + fill（向后兼容）

## 技术约束

- MUST 批准动作幂等（change 目录已存在则跳过）
- MUST 完整 proposal.md 生成后须经用户确认才落盘（审批的人控属性不因自动化丧失）
- MUST 5 段 → proposal.md 的转换保留信息映射：架构依据 → Why、范围+关键场景 → What Changes、技术约束涉及面 → Capabilities/Impact；验收标准以 `## Acceptance` 或 Impact 子节保留
- MUST 所有 Python 子进程通过 env-var 传参（Oracle C1 合规，禁止 bash 字符串插值）
- MUST NOT 改变 status=proposed 语义：design 阶段只写 status=planned，proposed 由 plan 阶段 fill 后写入
- MUST design 阶段的 `propose_quality_check` 只调用 proposal 相关 3 项，tasks/roadmap 对齐 2 项留在 plan（对象在设计时不存在，前移必然误报）
- MUST `.design-handoff.json` schema bump version（v1 → v2），`plan_intake.sh::check_design_handoff` 兼容 v1/v2
- MUST NOT 修改 `deps` / `feature` / `guide-ship` skill 的任何输入输出格式
- SHOULD `openspec validate <name> --json` 作为 design 审查的原生校验层（错误即阻断，与 STRICT 无关）

## 验收标准

- [ ] 批准动作后 `openspec/changes/<name>/` 存在且含 `.openspec.yaml` + **完整** `proposal.md`（Why/What Changes/Impact，≥500 字符，含 ADR 引用与 In/Out Scope）+ `roadmap-meta.yaml`（含 `change_type`）
- [ ] 完整 proposal.md 经用户确认环节后才落盘
- [ ] design 审查两层运行：improvements 5 段审查 + openspec proposal 3 项质量检查 + `openspec validate`；STRICT_DESIGN_GATE=yes 时不达标阻断
- [ ] `iteration.json` 中该 change status=planned（非 proposed）
- [ ] `.design-handoff.json` version=2 且含 `changes_pre_created` 数组
- [ ] `guide-plan` 对预建 change 零重复创建，Phase 2.5 fill 仅处理 specs/design/tasks
- [ ] phase/category 正确来自 improvements 头部字段（非硬编码）
- [ ] plan 阶段 `propose_quality_check` 5 项（含 tasks/roadmap 对齐 2 项）在 plan_done 行为无回归
- [ ] `SKIP_DESIGN_HANDOFF=yes` 存量骨架路径行为不变
- [ ] 新 ADR（ADR-0025 或下一个可用编号）已采纳
- [ ] 单元测试 + bats 集成测试通过，CI 全绿（含恒真断言门控）
