# ADR-0025: design 阶段承担 openspec proposal 创建与内容审查

> **状态**: 已采纳
> **日期**: 2026-08-02
> **作者**: sisyphus
> **evolved-from**: ADR-0003 (三阶段架构 v2.1 已漂移为四阶段, 本 ADR 显式记录再分配)

## Context

v2.1 四阶段架构（arch → design → plan → ship）落地后，`guide-design` 成为"哑管道"：
批准动作仅向 `proposal-approved.md` 追加一行表格（`approve_proposal.sh` → `state.sh::append_approved`），
无内容审查、不触碰 openspec，审批与 change 实体创建脱节。

与此同时，openspec proposal 的实质内容在 design 审批时已全部具备：
`.rddf/improvements/<name>.md` 的 5 段（架构依据/范围/关键场景/技术约束/验收标准）经 brainstorm 逐段确认，
信息量足以转换为完整 openspec `proposal.md`（Why / What Changes / Capabilities / Impact）。

当前流程把 improvements 5 段降级为占位骨架（`<skeleton motivation>`），到 plan 阶段才填实。
结果是：审批时无实质 proposal 可审，design-done 门控只能检查状态列枚举，提案内容质量问题
要到 guide-plan 甚至 plan-done 才暴露，反馈链路过长。

**架构依据**:
- ADR-0003 — 三阶段架构（v2.1 已漂移为四阶段，本 ADR 显式记录再分配）
- ADR-0016 — handoff 发现契约
- ADR-0017 — rddf-session 绑定
- ADR-0019 — change-arch 对齐检查范式
- 已归档 change `add-propose-content-review` — 4 维 Oracle 内容审查原型

## Decision

将"创建 + 审查"前移到 design 阶段的批准动作：

### D1 — approve 编排为「生成 → 确认 → 落盘」

`approve_proposal.sh` 追加表格行后，guide-design SKILL.md 编排 AI 将 improvements 5 段
转换为完整 proposal.md 草稿并展示；用户确认后才写盘 + `openspec new change` + 状态写入。
保持审批的人控属性。

### D2 — 5 段 → proposal.md 固定映射

- 架构依据 → `## Why`
- 范围 + 关键场景 → `## What Changes`（含 In/Out Scope）
- 技术约束涉及面 → `## Capabilities` / `## Impact`
- 验收标准 → `## Acceptance`（markdown checkboxes 保留）

映射写入 `generate_full_proposal.py` 作为转换契约。

### D3 — design-handoff schema v2

新增 `changes_pre_created: [<name>, ...]`, `version: 2`，
schema `additionalProperties: false` 同步更新；`plan_intake.sh::check_design_handoff` 接受 v1 与 v2
（v1 时 changes_pre_created 视为空，向后兼容）。

### D4 — 审查分层与严重度

- **improvements 层**（5 段完整性 / ADR 引用 / 可量化验收 / 必填头部字段）
- **openspec proposal 层**（`propose_quality_check.run_design_checks` 3 项 + `openspec validate`）

默认 warning；`STRICT_DESIGN_GATE=yes` 阻断；openspec validate 的 ERROR 始终阻断。
Oracle 4 维审查可选叠加（`SKIP_CONTENT_REVIEW=yes` 跳过）。

### D5 — propose_quality_check 拆分调用

design 阶段只调 proposal 相关 3 项（长度 ≥500 / ADR 引用 / In-Out Scope）；
tasks ≥2 与 roadmap 对齐 2 项留在 plan 阶段（对象在设计时不存在，前移必然误报）。
plan_done 既有 5 项行为不变。

### D6 — 元数据来源优先级

`.rddf/improvements/<name>.md` 头部 > 批准时用户输入 > fallback（default/general + warning）。
`create_skeleton_change` 骨架分支也补 `change_type` 字段。

### 配套改动

- `guide-plan` intake 消费 `changes_pre_created` 跳过已建 change
- Phase 2.5 fill 范围收缩为 specs / design.md / tasks.md（proposal 已完成）
- `SKIP_DESIGN_HANDOFF=yes` 存量路径行为不变；骨架模式保留为 fallback

## Consequences

**正面**:
- 审批时即可看到完整 proposal，反馈链路从 plan 阶段前移到 design 阶段
- 提案内容质量问题（缺 ADR 引用、In/Out Scope 不清）暴露在前移位置
- proposal 3 项质量检查 + openspec validate + 用户确认 = 三重防生成质量波动
- schema 升级保证存量 v1 不受影响

**负面/权衡**:
- approve 动作变重：单条批准多走一遍 AI 生成 + 用户确认。批量批准（`a`）逐条生成
- ADR-0003 漂移扩大：以 ADR-0025 显式记录再分配，将"隐性漂移"转为"显式治理"
- 元数据来源修复属于"扩大 schema 边界"类改动，须配套变更 to plan shell 的 fallback 行为

**兼容性**:
- `SKIP_DESIGN_HANDOFF=yes` 路径完全不变
- design-handoff v1 仍被 plan_intake 接受
- iteration.json `status=planned` 已存在,无需 schema 变更

## Alternatives

- **维持 design 仅状态流转**（v2.0 行为）— 反馈链路问题持续，违反 design/done 阶段"应有实质审查"的直觉
- **引入独立 review 阶段** — 复杂度上升，新增 state 反而问题增多
- **AI 仅生成 + 跳过用户确认** — 失去审批的人控属性，违反 open-spec 协作的核心理念

## References

- `openspec/changes/move-proposal-creation-to-design/{proposal,design,tasks}.md`
- `skills/guide-design/scripts/{generate_full_proposal,design_content_review,approve_proposal}.{py,sh}`
- `skills/_lib/schemas/design_handoff_schema.json` (v2)
- `skills/guide-plan/scripts/plan_intake.sh` (v1+v2 compat)
- `skills/propose/scripts/propose_quality_check.py` (run_design_checks)
- ADR-0003, ADR-0016, ADR-0017, ADR-0019 (相关)
