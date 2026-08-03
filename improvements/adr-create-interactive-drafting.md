# adr-create-interactive-drafting

**优先级**: P1 | **来源**: 用户需求 2026-08-03 — 借鉴 grill-me 改进 adr-create (Oracle 审查修订 2026-08-03)
**阶段**: v2.1 | **分类**: arch-design
**类型**: feature

## 架构依据

- guide-arch Phase 2 (adr-create) 选项 1 目前纯手动：复制模板 → 填标题 → 人工编辑。SKILL.md 明确写「本阶段不提供自动化生成」（SKILL.md:150），ADR 质量完全依赖架构师手工
- 借鉴 grill-me（mattpocock/skills，skills.sh 实时 731.6K 安装）核心协议：一次一问 / 每问附推荐答案 / 事实自查 / 决策问用户 / 共识后才行动
- 已有 `adr_gate.sh` 脚本（adr-creation-architecture-gate, 2026-07-29 归档），但 **Phase 2 选项 1 执行路径尚未调用它**（归档 tasks.md 仅完成 1.1 脚本 + 1.2 测试，SKILL.md 接线未实现）— 本提案同时承担「门禁接线 + 分支处理 + 对话」
- ADR 是单决策文档（非多决策系统），完整 grill-me 决策树遍历属于过度设计 → 对话轮次控制在 3-5 轮

## 范围

- **In Scope**:
  - guide-arch SKILL.md Phase 2 选项 1 执行路径接线 `adr_gate.sh`：调用并按返回分类分发（ARCHITECTURE → 三段式对话；GOVERNANCE → 二次确认；IMPLEMENTATION → 阻断并给替代路径）
  - 三段式对话（仅 ARCHITECTURE 分支）：① **现状挖掘**（agent 自动扫描代码库 + 已有 ADR + 架构文档，生成现状摘要）→ ② **决策对话**（只问 3-5 个真正决策点，一次一问 + 推荐答案）→ ③ **草稿呈现**（对话中呈现完整 ADR 草稿）
  - 完整 ADR 草稿：覆盖模板全部 section（见下方 section 清单）
  - 确认后落盘 + `SKIP_ADR_CONFIRM=yes` 跳过确认（新环境变量，需文档 + 测试）
  - 纯 SKILL.md 指令块实现，零新增脚本（复用现有 adr_gate.sh）
- **Out Scope**:
  - 不修改 `adr_gate.sh` 门禁逻辑本身（关键词分类逻辑保留）
  - 不修改 ADR 模板格式（ADR-0000-template.md）
  - 不引入完整 grill-me 决策树遍历（ADR 单决策场景不需要）
  - 不 retroactive 修改现有 ADR 文件

**ADR 模板 section 清单**（ADR-0000-template.md 实际结构，草稿必须覆盖）：
- `## Context`（含 `**架构依据**` 子项）
- `## Decision`（含 `### 影响范围` + `### 备选方案` 子 section）
- `## Consequences`（含 `### 正面` + `### 负面 / 风险` + `### 后续待办` 子 section）
- `## References`
- 元数据行：`> **状态**` / `> **日期**` / `> **决策者**`（状态为元数据行，非 section）

## 关键场景

- GIVEN 用户选择「创建新 ADR」并描述议题, WHEN `adr_gate.sh` 判定为 ARCHITECTURE, THEN 自动进入三段式对话（无额外确认）
- GIVEN 用户选择「创建新 ADR」并描述议题, WHEN `adr_gate.sh` 判定为 GOVERNANCE, THEN 显示二次确认（推荐替代路径如 RELEASE.md/ci-cd.md/CONTRIBUTING.md），不进入对话
- GIVEN 用户选择「创建新 ADR」并描述议题, WHEN `adr_gate.sh` 判定为 IMPLEMENTATION, THEN 阻断并显示具体替代路径（docs/、.github/、tasks.md、roadmap.md 子任务）
- GIVEN 对话进入现状挖掘段, WHEN 代码库/已有 ADR 能回答的事实, THEN agent 自动查找，不抛给用户
- GIVEN 对话进入决策对话段, WHEN 需要用户拍板的决策点, THEN 一次一问 + 附推荐答案，等用户回应后继续
- GIVEN 用户回答完所有决策点, WHEN agent 生成完整草稿, THEN 在对话中呈现全部内容
- GIVEN 草稿呈现后, WHEN 用户确认, THEN 写入 `docs/adr/ADR-NNNN-<slug>.md`
- GIVEN 用户在对话中途输入 q/cancel, WHEN 中断信号, THEN 退出对话且不留半成品文件
- GIVEN `SKIP_ADR_CONFIRM=yes`, WHEN 草稿生成, THEN 跳过确认直接落盘

## 技术约束

- MUST 在 Phase 2 选项 1 执行路径中先调用 `adr_gate.sh "${TOPIC}"` 并按返回分类分发（ARCHITECTURE→三段式对话；GOVERNANCE→二次确认；IMPLEMENTATION→阻断并给替代路径）；对话指令块只在 ARCHITECTURE 分支后激活
- MUST 保留 grill-me 四原则：一次一问 / 附推荐答案 / 事实自查 / 决策问用户
- MUST 对话轮次控制在 3-5 轮（适配单决策场景）
- MUST 草稿覆盖 ADR 模板全部 section（按上文 section 清单）
- MUST 支持 `SKIP_ADR_CONFIRM=yes`（新环境变量，需在 AGENTS.md/env 文档登记 + bats 测试）
- MUST 对话中途取消不产生半成品文件
- MUST NOT 新增脚本文件（纯 SKILL.md 指令；复用现有 adr_gate.sh）
- SHOULD 现状挖掘复用 ADR-0016 handoff 契约字段（JSON: `adr_dir`/`architecture_dir`；bash 侧环境变量: `DISCOVERED_ADR_DIR`/`DISCOVERED_ADR_PATTERN`/`DISCOVERED_ARCHITECTURE_DIR`）

## 验收标准

- guide-arch SKILL.md Phase 2 选项 1 更新：`adr_gate.sh` 调用嵌入执行路径，三分支均有显式处理
- ARCHITECTURE 判定后自动进入对话，无手动干预
- GOVERNANCE 判定 → 二次确认后才允许；IMPLEMENTATION 判定 → 阻断并给出替代路径
- 对话中 agent 先给出现状摘要（代码挖掘结果），不问用户可查事实
- 每个决策点：一次一问 + 推荐答案
- 对话结束生成完整 ADR 草稿（覆盖 section 清单全部 4 顶层 + 5 子 section + 元数据行）
- 用户确认后文件写入 `docs/adr/ADR-NNNN-<slug>.md`
- `SKIP_ADR_CONFIRM=yes` 时跳过确认直接落盘（bats 测试覆盖）
- 中途取消 → 无半成品文件残留
- 无新增脚本文件（验证：仅 SKILL.md 变更）
- 新增/扩展 bats 测试覆盖门禁三分支 + confirm-skip 路径（如 test_adr_gate_flow.bats）
