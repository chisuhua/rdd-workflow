## Context

**背景**: 2026-08-03 user request 复盘发现 guide-arch Phase 2 (adr-create) 选项 1 的执行路径存在「质量 = 人工手写」瓶颈。SKILL.md:150 明确写「本阶段不提供自动化生成」，ADR 质量完全依赖架构师从空白模板手工填写（详见 `improvements/adr-create-interactive-drafting.md` 架构依据）。前序归档 `2026-07-29-adr-creation-architecture-gate` 已交付 `adr_gate.sh` 门禁脚本（ARCHITECTURE/GOVERNANCE/IMPLEMENTATION 三分类 + `SKIP_ADR_GATE=yes`），但**仅完成 1.1 脚本 + 1.2 测试，SKILL.md 接线未实现**——本提案承担「接线 + 分支处理 + 3-5 轮对话」。

**当前状态**:
- `skills/guide-arch/scripts/adr_gate.sh`（31 行）已就绪：3 分类 + `SKIP_ADR_GATE` 旁路
- `tests/integration/test_adr_gate.bats`（4 cases）已就绪：3 分类回归 + SKIP_ADR_GATE 旁路
- `docs/adr/ADR-0000-template.md` 50 行：4 顶层 section + 5 子 section + 3 元数据行结构稳定
- `skills/guide-arch/SKILL.md` Phase 2 选项 1（lines 211-244）当前为「复制模板 → 填标题 → 编辑占位符」纯手动流程

**约束**:
- MUST 纯 SKILL.md 指令块实现，零新增脚本（验证：仅 `skills/guide-arch/SKILL.md` 变更 + 新增 bats 测试）
- MUST 复用现有 `adr_gate.sh`，不修改其分类逻辑
- MUST 不修改 `ADR-0000-template.md` 模板格式
- MUST 对话轮次控制在 3-5 轮（ADR 单决策场景，不引入完整 grill-me 决策树）
- MUST 保留 grill-me 四原则：一次一问 / 每问附推荐答案 / 事实自查 / 决策问用户
- MUST 支持 `SKIP_ADR_CONFIRM=yes` 跳过确认（与既有 `SKIP_ADR_GATE=yes` 语义独立）
- MUST 现状挖掘复用 ADR-0016 handoff 契约（环境变量 `DISCOVERED_ADR_DIR`/`DISCOVERED_ADR_PATTERN`/`DISCOVERED_ARCHITECTURE_DIR`）
- MUST 中途取消（q/cancel）不留半成品文件（原子写：temp + rename）
- MUST 走 plan-driven 实施 (TDD 5 步)，与既有 rdd-workflow change 流程一致

## Goals / Non-Goals

**Goals**:
- 实施 `improvements/adr-create-interactive-drafting.md` 范围 In Scope 列出的所有项（3 分支接线 + ARCHITECTURE 三段式对话 + `SKIP_ADR_CONFIRM`）
- 草稿覆盖 ADR-0000 模板全部 4 顶层 section + 5 子 section + 3 元数据行
- 新增/扩展 bats 测试覆盖 3 分支分发 + confirm-skip 路径 + cancel-cleanup（建议文件名 `test_adr_gate_flow.bats`）
- 不破坏既有 `adr_gate.sh` 行为（4 现有测试保持 green）
- 不破坏 `SKIP_ADR_GATE=yes` 旁路

**Non-Goals**:
- 不在 OpenSpec `specs/` 中创建 capability delta（此为 rdd-workflow 自指改进，留给 plan 阶段 spec fill 决策）
- 不修改 `adr_gate.sh` 门禁逻辑（保留关键词分类）
- 不修改 `ADR-0000-template.md` 模板
- 不引入完整 grill-me 决策树遍历（ADR 单决策场景过度设计）
- 不 retroactive 修改现有 ADR 文件
- 不在 plan 阶段生成 `tasks.md` / `design.md` / `specs`（设计阶段 Out of Scope 明确项）

## Decisions

### 决策 1: 三分支 dispatch 完全在 SKILL.md 中以 case 块实现

ARCHITECTURE 触发三段式对话；GOVERNANCE 触发二次确认（推荐 RELEASE.md/ci-cd.md/CONTRIBUTING.md 替代）；IMPLEMENTATION 触发阻断并显示 docs/、.github/、tasks.md、roadmap.md 子任务替代路径。dispatch 入口为 `case "${GATE_CLASS}" in` 紧跟 `adr_gate.sh "${TOPIC}"` 之后。理由：保持单一执行路径可读，调用者只需匹配门禁输出，无需重读分类逻辑。

### 决策 2: ARCHITECTURE 分支采用三段式对话（现状挖掘 → 决策对话 → 草稿呈现）

- **段 1 现状挖掘**: agent 自动调用 `ls ${DISCOVERED_ADR_DIR}/${DISCOVERED_ADR_PATTERN}` + `find ${DISCOVERED_ARCHITECTURE_DIR}` + `grep -l '<keyword>' docs/adr/` 生成 3 段式摘要（已有相关 ADR / 架构文档 / 代码模式），**不向用户提问可查事实**
- **段 2 决策对话**: 严格 3-5 轮；每轮「一次一问 + 附推荐答案」；推荐答案可由用户接受（y）/ 改写（输入新文本）/ 跳过（s）
- **段 3 草稿呈现**: 完整 ADR 草稿一次性呈现到对话（含全部 4 顶层 + 5 子 section + 3 元数据行），等用户确认

理由：完整 grill-me 决策树遍历对单决策 ADR 属过度设计（3-5 轮足够覆盖「Context 模糊点」「Decision 备选」「Consequences 风险」三类核心歧义）；保留四原则确保对话质量不下滑。

### 决策 3: SKIP_ADR_CONFIRM 与 SKIP_ADR_GATE 语义独立

- `SKIP_ADR_GATE=yes`（既有）→ 跳过架构影响力门禁分类，直接按 ARCHITECTURE 处理
- `SKIP_ADR_CONFIRM=yes`（新增）→ 跳过草稿呈现后的用户确认步骤，直接落盘

两个 env var 独立判定（AND 关系），允许组合使用。理由：覆盖两类独立用例——(a) 信任门禁分类（CI/批处理场景）vs (b) 信任草稿质量（用户已 review 完对话）。文档同步登记到 AGENTS.md 关键约定。

### 决策 4: 落盘采用 temp + rename 原子写 + 取消守卫

对话中途用户输入 `q`/`cancel`/`exit` → 立即退出对话，**不写任何文件**（连 temp 都不留）；用户确认落盘前先写 `${NEW_ADR}.tmp`，原子 `mv` 到最终路径；中途失败 `trap` 清理 temp。理由：避免 ADR-0017 rddf-session 半成品文件污染 `docs/adr/`（归档脚本会扫描并误判为 orphan）。

### 决策 5: 现状挖掘复用 ADR-0016 handoff 契约，不新增环境变量

`DISCOVERED_ADR_DIR` / `DISCOVERED_ADR_PATTERN` / `DISCOVERED_ARCHITECTURE_DIR` 已由 `discover-arch-artifacts.sh` 在 Phase 1 Step 5 写入，Phase 2 可直接读取。零新增 env var、零新契约字段。理由：保持现状挖掘与 Phase 1 列表展示共用同一发现路径，避免「Phase 2 看到的目录 ≠ Phase 1 看到的目录」类 bug。

### 决策 6: 测试策略——结构化 grep + 行为 bats 混合

- **结构化 grep**（bats）：断言 SKILL.md 包含三段式对话全部关键短语（"现状挖掘"/"决策对话"/"草稿呈现"/`SKIP_ADR_CONFIRM`/三 case 分支）
- **行为 bats**（`test_adr_gate_flow.bats`）：覆盖三分支 dispatch 路径 + confirm-skip env var 识别 + 取消清理（用 mock `read` 返回 `q` 验证无文件写入）
- 既有 `test_adr_gate.bats` 4 cases 不变（回归护栏）

理由：SKILL.md 是 Markdown 文档，行为测试只能通过 `read` mock 间接覆盖；结构化 grep 提供「指令块确实存在」的强保证。两者互补。

## Risks

- **对话轮次失控**: 3-5 轮上限未硬约束 → agent 可能误扩到 6+ 轮 → 在 SKILL.md 显式写「超过 5 轮强制 break 并询问用户是否继续」
- **现状挖掘误报**: `grep -l` 命中无关 ADR → 在段 1 摘要前加「仅展示与本议题直接相关的（标题或 Context 包含本议题关键词）」过滤
- **草稿模板覆盖不全**: 4 顶层 + 5 子 + 3 元数据行遗漏 → bats 静态断言草稿必须包含全部 12 个锚点字符串
- **半成品文件残留**: 对话中途 cancel 未清理 temp → 强制 `trap 'rm -f ${NEW_ADR}.tmp' EXIT ERR` + 测试用 mock `read` 验证
- **`SKIP_ADR_CONFIRM` 与既有 `SKIP_ADR_GATE` 混淆**: 开发者误读语义 → AGENTS.md 关键约定表 + SKILL.md 注释双重标注各自作用域
- **零脚本约束边界**: 未来若需要 Bash 函数测试 → 接受在 SKILL.md 中以 `bash <<EOF` heredoc 暴露可测函数（不创建独立 .sh 文件）

## Open Questions

- 决策对话超过 5 轮时是否提供「导出当前进度到文件 + 退出」选项？本次不实现，留作 v2.1 follow-up
- ARCHITECTURE 分支的对话状态是否需要 rddf-session 持久化（断线恢复）？本次不实现（ADR 单次会话即可）
