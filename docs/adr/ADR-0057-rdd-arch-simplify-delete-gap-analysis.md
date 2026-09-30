# ADR-0057: rdd-arch 简化为 ADR + theme doc 双工件；删除 gap-analysis 协议

> **状态**: 已采纳
> **日期**: 2026-09-30
> **决策者**: rdd-workflow maintainer
> **supersedes**: ADR-0046 §1, §2 (arch-analyzer protocol subset 范围), ADR-0046 §Decision table rows 1-2
> **取代**: ADR-0046（整体被本 ADR 替代）
> **关联**: ADR-0028 (role-model per phase), ADR-0048 (v4 stage-merge revision), ADR-0051 (skill description convention)

## Context

ADR-0046（2026-09-07）确立 rdd-arch gap-analysis 的 5-section 输出契约（`docs/architecture/*-gap-analysis.md` 模板）和 `_lib/arch/protocol.py` 数据层。从 v2.0.8 到 v4.1，rdd-arch 通过该协议支持 1 个 gap-analysis 实例（multi-project-ai-collaborative-development）。

实际运行 6 个月后，三条证据指向 gap-analysis 在 rdd-workflow 是 YAGNI（You Aren't Gonna Need It）：

1. **架构文档类型已重叠**：rdd-workflow 在 `docs/architecture/` 维护 17 个主题快照文档（如 workflow-photos.md），README Doc Map 表格已显式列出每个主题的 Primary ADRs。这些文档承担"当前架构快照 + 组合叙事"角色。gap-analysis 的 §1 (目标架构) + §2 (当前架构) + §5 (参考资料 ADR 列表) 与 theme doc 实质重叠。
2. **写路径膨胀**：rdd-arch 当前维护 3 种工件类型（ADR + theme doc + gap-analysis），但 gap-analysis 没有提供前两者覆盖不到的价值。其 §3 (差距清单) + §4 (补齐路径) 在工程上属于迁移路线图——这正是 rdd-planner 拥有 `.rddf/roadmap/phases/*.md` 和 `.rddf/improvements/*.md` 的领域（per AGENTS.md + ADR-0048）。
3. **维护负担不对称**：gap-analysis 的 §3+§4 是 per-change 的迁移计划，而 theme doc 是 per-topic 的持续快照。两者的写触发器不同——混在一个工件里，要么 §3+§4 在 change 后陈旧（违反 ADR-0028 single-write-path 精神），要么 §1+§2+§5 被频繁变更打散（破坏稳定性）。

ADR-0046 §Out of Scope 已声明"arch-done Phase 5 接线 validate_document 推迟"。本会话已满足该 deferred wiring（`check_gap_analyses_advisory()` in `arch_done_gate.sh`，见阶段 1 提交 `e16cd54`），但更深的简化是删除整个协议。

**架构依据**:
- ADR-0028 §role.boundaries — rdd-arch 不写 roadmap/phases/improvements（rdd-planner owns）；rdd-planner 不写 docs/adr/、docs/architecture/（rdd-arch owns）。gap-analysis 当前把 phase 接入文档中越界。
- ADR-0048 §Decision 1 — rdd-arch 完全脱离 roadmap（roadmap 由 rdd-planner 独占）。gap-analysis §3+§4 的"路线图"内容违反此边界精神。
- ADR-0051 §Decision — skill description 字段约定正触发条件 + 单一职责。rdd-arch 当前 description 提到 3 种工件，违反单一职责。

### 关键观察（来自 oracle/metis 联合分析）

| 维度 | 当前 | 简化后 |
|------|------|--------|
| rdd-arch 工件类型 | 3（ADR + theme doc + gap-analysis）| 2（ADR + theme doc） |
| 写路径 | 3 独立写路径 | 2 写路径，符合 ADR-0028 |
| 用户认知负担 | "何时用 ADR / theme doc / gap-analysis" | "决策用 ADR，描述用 theme doc" |
| gap-analysis §3+§4 迁移目标 | rdd-planner `.rddf/roadmap/phases/*.md` + `.rddf/improvements/*.md` | 单一权威迁移工件 |
| rdd-arch SKILL.md 行数 | 763 | 预计 ~450 |
| 测试套件 | 含 11 gap-analysis 集成 + 29 protocol 单元 | 净减 ~25 测试 |

## Decision

**rdd-arch 简化为双工件模型**：ADR（atomic decision record）+ theme doc（topic current-state snapshot）。删除 gap-analysis 作为独立工件类型。

### 影响范围

- **In Scope**:
  - 删除 `_lib/arch/protocol.py`（5-section 契约 + ValidationReport + 3 纯函数）
  - 删除 `_lib/arch/__init__.py`（暴露 protocol 函数）
  - 删除 `skills/rdd-arch/scripts/arch_gap_analysis.sh`（5-section wrapper）
  - 删除 `tests/unit/test_arch_protocol.py`（29 测试）
  - 删除 `tests/integration/test_arch_gap_analysis_extraction.bats`（11 测试）
  - 简化 `arch_done_gate.sh`：删除 `check_gap_analyses_advisory()`
  - 简化 `arch_audit_check.py`：删除 `_check_gap_analyses()` 子检查（保留 ADR inventory + arch-handoff + theme doc existence 3 个子检查）
  - 简化 `arch_quality_gate.py`：删除 gap-analysis check 项
  - 简化 `arch_env_check.sh`：删除 gap-analysis 发现逻辑
  - 重写 `skills/rdd-arch/SKILL.md`：从 5 phase（setup/adr-create/architecture/arch-validation/arch-done）改为 4 phase（setup/adr-create/arch-validation/arch-done）；扩 `role.boundaries.owns` 到 `docs/architecture/*.md`；删除 Phase 3 (architecture gap-analysis 阶段)；删除所有 gap-analysis 菜单引用
  - 更新 `tests/unit/test_arch_audit_check.py`：删除 6 个 gap-analysis 子测试
  - 更新 `tests/unit/test_arch_quality_gate.py`：删除 gap-analysis 相关测试
  - 写新 ADR（ADR-0058，per Stage 1A-1）把"gap-analysis 能力迁移到 rdd-planner"记录下来
  - 迁移现有 1 个 gap-analysis 实例：`docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md` → 内容拆分到对应 theme doc + `.rddf/improvements/*.md` + `.rddf/roadmap/objectives/*.md`
- **Out Scope**:
  - rdd-planner 端的具体实施（Stage C，独立 commit）
  - openspec change proposal 模板（gap-analysis 的迁移清单本质上是 improvement 提案，可自然迁移）
  - 第三方项目用户文档（外部 rdd-workflow 消费者不读 gap-analysis 模板——这是内部工件）
  - 不删除 ADR-0046 历史（标记 superseded_by ADR-0057）

### 备选方案

| 备选 | 理由 |
|------|------|
| **A. 删除 gap-analysis + 简化到双工件**（本 ADR）| YAGNI 原则；写路径从 3 减到 2；rdd-arch description 单一职责化；现有 1 个实例可迁移；ADR-0046 + ADR-0048 + ADR-0051 三方一致支持 |
| B. 保留 gap-analysis 但约束为"未来方向段"扩展到 theme doc | 不删 `protocol.py`；仅把它从独立工件降级为 theme doc 的可选段落——保留 5-section 契约 + 8 个 bats 锁定。但 theme doc 已经有 `target_state` 隐式表达，gap-analysis 不提供增量价值，反而增加 theme doc 模板复杂度 |
| C. 创建 `rddf planner migrate-from-gap-analysis` 工具自动迁移内容 | 自动化迁移 1 个文件是杀鸡用牛刀；人工迁移成本 < 30 分钟；CLI 维护负担 > 收益 |
| D. 创建独立 `rdd-arch-audit` 技能承载 gap-analysis 能力 | 3 次被否决（per oracle + metis prior conversations）：新技能扩散、与 ADR-0043 v4 stage-merge 简化方向冲突 |

**采纳 A**：备选 B/C/D 都不解决 §3+§4 的迁移路线图越界问题，且与 ADR-0048 + ADR-0028 + ADR-0051 三方一致。备选 A 是唯一同时满足"single write-path"和"语义分工清晰"的方案。

## Consequences

### 正面

- **写路径从 3 减到 2**：符合 ADR-0028 single-write-path 精神。rdd-arch 不再拥有"路线图"内容（迁给 rdd-planner），严格边界清晰。
- **rdd-arch SKILL.md 简化**：删除 Phase 3 (architecture gap-analysis) 整个阶段（~180 行），新增 theme doc 创建流程。SKILL.md 总行数预计从 763 降到 ~450。
- **rdd-arch description 单一职责**：当前 description 提到 ADR + roadmap + arch quality gate 3 个职责；删除 gap-analysis 后聚焦到 ADR authoring + arch quality gate 两个职责，符合 ADR-0051 单一职责原则。
- **测试套件精简**：删 11 gap-analysis 集成 + 29 protocol 单元测试，净减 ~25 测试 → 测试运行更快、CI 反馈更清晰。
- **theme doc 角色明确化**：当前 theme doc 同时承担"现状快照"和"组合叙事"角色；gap-analysis 删除后，theme doc 单一承担现状 + 组合（per Oracle 之前分析的"per-theme architecture README index"），是 rdd-arch 的真正核心工件。
- **gap-analysis 能力不丢失**：通过 Stage C 迁移到 rdd-planner（`.rddf/roadmap/phases/*.md` 的 `target_state` + `fill_path` 字段 + `add-improvement --source-arch-gap` CLI），用户获得更结构化的迁移规划入口。
- **新手认知简化**："决策用 ADR，描述用 theme doc"——二元选择优于三元选择。

### 负面 / 风险

- **现有 1 个 gap-analysis 实例需手动迁移**：人工拆分内容到 theme doc + improvements + objectives。如果失败，Hub-Spoke federation 的规划可能丢失。**缓解**：迁移 checklist（Stage B-1 至 B-5）+ 原文件 30 天归档期（`.archive/`）+ 人工 review（30 分钟成本）。
- **ADR-0046 部分失效**：ADR-0046 §1-§2 涉及 protocol.py + arch_gap_analysis.sh 的决定被本 ADR 替代。**缓解**：ADR-0046 头部加 `superseded_by: ADR-0057`（per prior conversation settled 的 ADR 不可变原则），保持历史完整性。
- **现有 ADR/文档引用 gap-analysis 模板**：AGENTS.md、USAGE.md、多个 ADR（0018/0016/0030/0031/0046/0048/0003/0006）正文提及"5-section gap-analysis"。**缓解**：保留文本引用（标注"已废弃 per ADR-0057"）；不破坏向后兼容性，因为这些只是说明性文字，不是 import 或 API 调用。
- **测试覆盖短期下降**：删除 ~40 测试，新 ~15 测试覆盖 rdd-planner 新增能力（Stage C）。净减 25 测试，但 arch 端 ADR + handoff + theme doc 检查仍完整覆盖。**缓解**：rdd-planner 新增的 phase schema + add-improvement 测试弥补覆盖损失。
- **rdd-arch 测试套件（arch_audit_check 等）已经依赖 gap-analysis 结构**：删 `_check_gap_analyses` 会改变 doc.sh 输出。**缓解**：arch_audit_check 输出从 18 个 sub-checks 减到 17 个；doctor `test_doctor_main.py` 已经更新到 18（per prior commit），需再次减到 17 并同步测试。
- **rdd-planner 是否准备好接收 gap-analysis 能力**：Stage C 是否顺利决定此 ADR 的可行性。**缓解**：阶段 B（迁移现有 gap-analysis）和阶段 C（rdd-planner 增强）独立 commit，便于回滚；若 Stage C 失败，gap-analysis 仍可在 archive 中找到（人工咨询）。

### 后续待办

- [ ] **Stage B-1 至 B-5**: 迁移现有 gap-analysis 实例到 theme doc + improvements + objectives（独立 commit，预计 0.5 天）
- [ ] **Stage C-1 至 C-7**: rdd-planner 吸收 gap-analysis 能力（`add-improvement --source-arch-gap` CLI + phase `target_state` + `source_adr` 字段 + planner-handoff 新字段）（独立 commit，预计 1.5-2 天）
- [ ] **未来**: 当 theme doc 数量超 30 时评估 theme doc 自身的健康度（drift 检测）；可能引入 rdd-arch 内部的 `rddf arch inventory` 工具（per prior conversation Tier A 提议）

## References

- `docs/adr/ADR-0046-arch-analyzer-protocol-subset.md` — superseded（5-section 输出契约 + protocol.py 数据层）
- `docs/adr/ADR-0028-role-model-per-phase.md` — single-write-path 边界（rdd-arch 不写 roadmap）
- `docs/adr/ADR-0048-v4-stage-merge-revision.md` — rdd-arch 完全脱离 roadmap
- `docs/adr/ADR-0051-skill-description-convention.md` — skill description 单一职责
- `docs/adr/ADR-0054-objective-tracking.md` — rdd-planner 现有 objective 工件（gap-analysis §3+§4 的迁移目标之一）
- `docs/superpowers/specs/cross-stage-protocol-template.md` — Analyzer Subset spec（仍可作为 rdd-arch 内其他 deterministic 检查的设计模板，但 gap-analysis 不再是其实例）
- `_lib/arch/protocol.py` — 待删除（197 行）
- `skills/rdd-arch/scripts/arch_gap_analysis.sh` — 待删除（125 行）
- `docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md` — 待迁移（Stage B）