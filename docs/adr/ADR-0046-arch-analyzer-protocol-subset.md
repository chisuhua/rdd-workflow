# ADR-0046: arch-analyzer protocol subset

> **状态**: 已采纳
> **日期**: 2026-09-07
> **决策者**: rdd-workflow maintainer
> **关联**: ADR-0045 (verifier 5-section pattern), cross-stage-protocol-template.md
> **Oracle session**: ses_f84cabe64ffeBiz3XzHmFSSznc

## Context

`docs/superpowers/specs/verifier-protocol-template.md`（v2.0 由
inline-ac-verifier-into-rdd-verifier / ADR-0045 创立）冻结了 5-section
协议模式给 LLM-as-judge verifier 阶段用。该 spec 自称"first application
candidate: rdd-arch gap analysis. Not implemented in this change;
tracked as future"。

`rdd-arch gap analysis`（`skills/rdd-arch/scripts/arch_gap_analysis.sh`，
86 行，2 函数）是 **deterministic template generator**：生成 5 节 markdown
skeleton（目标架构 / 当前架构 / 差距清单 / 补齐路径 / 参考资料），人类
策展者填写内容。它没有 LLM、没有 verdict、没 agent 消费 context。

naive full-template adoption 会为不存在的消费者造文件、为人写文档的完成度
设置阻断 gate——即 form over substance。模板 spec 自身的 Boundaries 段
已声明 "human-dominated steps stay human-in-loop, only reasoning-assistant
sub-steps may use this template"，gap analysis 落在排除区。

## Decision

**Subset 架构**：rdd-arch gap analysis 采用 Analyzer Subset（template spec
重命名为 `cross-stage-protocol-template.md` 后定义）。逐节裁决：

| § | 裁决 | 一句话理由 |
|---|------|-----------|
| 1 SKILL.md § Protocol | **ADOPT** | 给确定性路径同样的可发现性；frontmatter 加 `protocol_inline: true` + `protocol_data_layer: "_lib/arch/protocol.py"` + `protocol_output_contract: true`（Analyzer Subset 专属 marker） |
| 2 Data Layer (`_lib/arch/protocol.py`) | **ADOPT** | 真工程价值：3 纯函数 + `ValidationReport` dataclass，消除重复路径逻辑，单测覆盖；遵循 ADR-0045 `_lib/verifier/protocol.py` 命名约定 |
| 3 Staged Context File | **SKIP** | 无 agent 消费者；markdown 骨架本身就是 artifact，人直接编辑它 |
| 4 SHA-Bound Cache | **SKIP** | 无 LLM verdict 可绑定 SHA；gap doc 是 git-tracked durable artifact，cache 违反 durability 边界 |
| 5 Fail-Closed Gate | **REPURPOSE** | 改名为 **Output Contract Validation**：结构一致性（5 节齐全 + slug 格式）= 硬；完成度（占位符密度）= advisory status 而已 |

**模板 spec 改名**：`verifier-protocol-template.md` →
`cross-stage-protocol-template.md`，加 Verifier Subset (full 5 sections)
+ Analyzer Subset (§1/§2/§5-repurposed) 两节。零成本（spec-only，
未被任何地方落地/引用）。

**Frontmatter marker 一致性**：Analyzer Subset 用 `protocol_output_contract: true`
而非 `protocol_context_file` / `protocol_cache_file`，避免 cross-stage
scanner 去找不存在的文件。

## Consequences

### 正面

- 真实工程价值：`_lib/arch/protocol.py` 消除了 2 函数里重复的 PROJECT_ROOT/ARCH_DIR 解析；`parse_slug` 顺手闭合 kebab-case 校验缺口（Oracle concern #3）。
- 仓库 precedent 一致：Oracle C1 3-file env-var pattern（参考 `roadmap_incremental_update.{sh,env.py}`）；AGENTS.md rule 25（新代码 import `_lib.arch`）。
- rdd-planner / rdd-builder 未来若采用 Analyzer Subset（per template "Future candidates"），可重用本 ADR + cross-stage spec 作决策模板。

### 负面 / 风险

- bash↔Python drift 风险（Oracle risk #1）：通过薄 wrapper + 双层断言（Python unit + 8 个现有 bats 不改）+ Oracle C1 env-var pattern 缓解。
- §5 越界阻断风险（Oracle risk #2）：在 spec + ADR 双重声明 "validation" 而非 "gate"；两层语义结构=hard / 完成=advisory 必须严格区分。
- 8 个现有 bats 隐藏耦合风险（Oracle risk #3）：重构前先读全部 8 个 bats 的精确断言（已读），保持 wrapper observable contract 逐字节不变；8/8 测试现已 0 改动全绿。

## Out of Scope

- **arch-done Phase 5 接线 `validate_document` 推迟**。本次只暴露 `validate_document` 作为 advisory helper。是否把 gap 完成度检查接入 arch-done gate 需独立 change（per `guide-design` 的 Phase 3 / ADR-0028 的 human-in-loop 原则）。
- rdd-planner / rdd-builder 的 Analyzer Subset 落地（template spec "Future candidates"）需各自独立 ADR + proposal。
- Verifier Subset 不受本次 change 影响（rdd-verifier v2.0 / ADR-0045 已实装并归档）。
- 不重写任何 markdown 内容措辞（保持人类策展的 idiomatic Chinese）。
- 不为 Analyzer Subset 创建 SHA-bound cache 或 staged context（永久 SKIP）。