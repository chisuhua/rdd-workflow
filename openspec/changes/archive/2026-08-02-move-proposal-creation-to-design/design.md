# move-proposal-creation-to-design — Design

## Context

v2.1 四阶段架构后，`guide-design` 的批准动作仅追加 `proposal-approved.md` 表格行（哑管道），openspec change 的实际创建全部留在 `guide-plan` Phase 2。`improvements/<name>.md` 的 5 段内容在 design 审批时已完备，足以生成完整 openspec `proposal.md`。本设计将"创建 + 审查"前移到批准动作，plan 收缩为"回填 + fill + deps + 门控"。

## Goals / Non-Goals

**Goals:**
- 批准即创建：approve → `openspec new change` + 完整 proposal.md（用户确认后落盘）+ roadmap-meta.yaml（含 change_type）+ iteration.json（planned）
- design 两层内容审查（improvements 层 + openspec proposal 层），warning/strict 双模式
- `.design-handoff.json` schema v2（`changes_pre_created`），plan_intake 兼容 v1/v2
- guide-plan 对预建 change 零重复创建；fill 收缩为 specs/design/tasks

**Non-Goals:**
- design 阶段不生成 tasks.md/design.md/specs（留 plan fill）
- 不改 proposal-suggestions/approved 表格格式；不引入 iteration.json 新状态值
- 不修改 ADR-0003（另起 ADR-0025）；不删骨架模式（留作存量 fallback）

## Decisions

- **D1 — approve 编排为"生成 → 确认 → 落盘"**：`approve_proposal.sh` 追加表格行后，guide-design SKILL.md 编排 AI 将 improvements 5 段转换为完整 proposal.md 草稿并展示；用户确认后才写盘 + `openspec new change` + 状态写入。保持审批的人控属性。
- **D2 — 5段 → proposal.md 固定映射**：架构依据 → `## Why`；范围+关键场景 → `## What Changes`（含 In/Out Scope）；技术约束涉及面 → `## Capabilities`/`## Impact`；验收标准 → `## Acceptance`。映射写入 guide-design SKILL.md 作为转换契约。
- **D3 — design-handoff v2**：新增 `changes_pre_created: [<name>, ...]`，`version: 2`，schema `additionalProperties: false` 同步更新；`plan_intake.sh::check_design_handoff` 接受 v1 与 v2（v1 时 changes_pre_created 视为空）。
- **D4 — 审查分层与严重度**：improvements 层（5 段完整性/ADR 引用/可量化验收/必填头部字段）+ openspec proposal 层（propose_quality_check 的 proposal 3 项 + `openspec validate <name> --json`）。默认 warning；`STRICT_DESIGN_GATE=yes` 阻断；openspec validate 的 ERROR 始终阻断。Oracle 4 维审查可选叠加（`SKIP_CONTENT_REVIEW=yes` 跳过）。
- **D5 — propose_quality_check 拆分调用**：design 只调 proposal 相关 3 项（长度/ADR/In-Out Scope）；tasks ≥2 与 roadmap 对齐 2 项留在 plan（对象在设计时不存在，前移必然误报）。plan_done 既有 5 项行为不变。
- **D6 — 元数据来源优先级**：`improvements/<name>.md` 头部 > 批准时用户输入 > fallback（default/general + warning）。修复 `batch_create_pending` 硬编码同款缺陷；roadmap-meta.yaml 骨架分支补 `change_type` 字段。

## Risks / Trade-offs

- **approve 变重**：AI 生成完整 proposal 增加批准耗时 → 以"批量批准仍走骨架 + 单条批准走完整"为折衷？否——统一走完整模式，批量批准逐条生成（用户逐条确认）。接受耗时换取审查实质化。
- **AI 生成质量波动**：映射契约（D2）+ 用户确认环节（D1）+ proposal 3 项质量检查（D4）三重防线。
- **schema 版本分裂**：存量 v1 handoff 必须可读（D3 兼容）；`SKIP_DESIGN_HANDOFF=yes` 路径完全不变。
- **ADR-0003 漂移扩大**：以 ADR-0025 显式记录再分配，漂移从"隐性"变"显性治理"。

## Migration Plan

1. schema v2 + plan_intake 兼容先行（存量 v1 不受影响）
2. approve 升级 + 内容审查上线（默认 warning，观察一周后可考虑 STRICT 默认化——另议）
3. guide-plan fill 收缩 + intake 消费 changes_pre_created
4. ADR-0025 采纳；docs（AGENTS.md/README）同步

## Open Questions

- 批量批准（`a` 选项）是否也逐条生成完整 proposal？（当前决策：是，逐条确认；若实战证明太重，后续 change 引入"批量=骨架"开关）
- Oracle 4 维审查是否纳入默认路径？（当前：可选叠加，默认关闭）
