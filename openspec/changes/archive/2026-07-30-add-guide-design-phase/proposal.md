## Why

当前三阶段架构 (`arch` → `plan` → `ship`) 把"提案创建 + 审批"塞在 `arch` 阶段的 Phase 5.5,导致三个架构缺陷:

1. **Phase 5.5 是设计异味** — `.5` 命名就是信号。Phase 5 门控通过后本应 `arch-done`,但附加了一个"半阶段"做提案审批。两种入口路径(Phase 1 菜单 vs Phase 5 门控)使代码产生条件分支,流程不线性。

2. **`add-improve` 无归属** — 它是一个独立 skill,不归 `arch` 也不归 `plan`,但它的输出必须经过 `arch` Phase 5.5 审批。`add-improve` 产生的提案 → `proposal-suggestions.md` → 必须再调用 `arch` 才能转移到 `proposal-approved.md`。

3. **推荐器把未审批提案路由到错误阶段** — `guide` 推荐器(两个实现: `guide_cmd.py` Python + `scan-state.sh` bash)对"有未审批提案"的状态推荐 `guide-plan`,但 `guide-plan` 只读 `proposal-approved.md`,无法消费未审批提案。未审批提案的正确去向是审批阶段。

提案管理(`add-improve` 创建 → 审查 → 批准/拒绝/延迟 → 交接给 plan)是独立于"架构定义"(ADR/roadmap/差距分析)的活动,应该是一级阶段。

## What Changes

### 新增 (NEW)

- **新增阶段 `guide-design`**:介于 `arch` 和 `plan` 之间,回答"要改什么才能到那里?"
  - 接收 arch 输出(ADR/roadmap/差距分析)
  - 内置 `add-improve` 作为子技能
  - 拥有提案全生命周期(创建 → 审查 → 批准/拒绝/延迟)
  - 输出 `proposal-approved.md` 作为 plan 阶段的输入契约
- **新增 handoff**:`.rddf/state/.design-handoff.json` (v1 schema,含 `design_complete_at`、`proposals_reviewed`、`all_proposals_have_decision`、`version` 四个字段)
- **新增 schema**:`skills/_lib/schemas/design_handoff_schema.json`
- **新增 rddf-session 类型**:`stage_design` (parent=stage_arch; stage_plan 的 parent 改为 stage_design)

### 修改 (MODIFIED)

- **`skills/guide-arch/SKILL.md`**:删除 Phase 5.5 全部内容,顶部(frontmatter 之后、Phase 1 之前)插入 deprecation notice。`arch-done` 门控只检查"ADR ≥ 1 + roadmap.md 存在",输出不再含提案计数,改为 `💡 Next: skill_use("guide-design")`
- **`skills/guide-plan/scripts/plan_intake.sh`**:在 arch-handoff 检查**之后**新增 design-done 门控。`SKIP_ARCH_HANDOFF=yes` 同时跳过 arch + design 检查;`check_direct_create_fallback`(有归档 change 的存量项目)同样豁免 design 门控
- **`skills/_lib/cli/guide_cmd.py` + `skills/guide/scripts/scan-state.sh`**:两个扫描器同步改为 4-state(`arch → design → plan → ship`),保留全部现有优先级分支(ADR<1 恢复、stale plan-handoff、无 roadmap.md、worktree 状态),仅将"未审批提案"路由从 `guide-plan` 改为 `guide-design`
- **`skills/rddf-session/scripts/rddf_session_pkg/_types.py`**:`_VALID_KINDS` + `_KIND_ALIAS` 增加 `stage_design`
- **`skills/_lib/schemas/sessions_schema.json`**:kind 枚举增加 `stage_design`,goal.intent 枚举增加 `guide-design`(additive 扩展,version 保持 1,既有数据兼容)
- **`skills/rddf-session/scripts/rddf_session_hooks.sh`**:`parent_kind_map` 增加 `stage_design: stage_arch`,修改 `stage_plan: stage_arch → stage_design`

### 迁移 (MIGRATED,搬移 + 重命名)

- `skills/guide-arch/scripts/arch_proposal_review.sh` → `skills/guide-design/scripts/design_proposal_review.sh`(函数重命名 `arch_proposal_review` → `design_proposal_review`,调用契约变化,逻辑不变)
- `skills/guide-arch/scripts/approve_proposal.sh` → `skills/guide-design/scripts/approve_proposal.sh`
- **老路径文件内容替换为 ~10 行 deprecated shim**(包装函数形式,非立即执行),杜绝双份代码并存
- `skills/add-improve/` → 文档层面归属 `guide-design`(代码不动,只改 SKILL.md 引用)

### 弃用 (DEPRECATED)

- `guide-arch` Phase 5.5 路径:老脚本位置保留 shim,输出统一警告文本(见 spec.md "deprecation-text" Scenario 为唯一 source of truth),shim 在 v2.1.x 全部 patch 版本保留,v2.2.0 移除

## Capabilities

### New Capabilities

- `workflow-design-phase`: Design 阶段状态机——接收 arch handoff,内嵌 `add-improve`,执行提案审查,通过 design-done 门控(所有提案有决策),输出 `proposal-approved.md` 供 plan 消费
- `design-handoff-contract`: `.rddf/state/.design-handoff.json` schema v1

### Modified Capabilities

- `workflow-architecture-phase`: arch 阶段不再包含提案审查子阶段;`arch-done` 契约只检查 ADR ≥ 1 + roadmap.md
- `workflow-plan-phase`: plan intake 新增 design-done 门控(硬切换,默认强制;`SKIP_ARCH_HANDOFF=yes` 与 direct-create fallback 豁免)
- `workflow-guide-recommender`: 双扫描器(Python + bash)同步升级为 4-state,保留全部现有优先级分支
- `workflow-session-management`: sessions schema kind/intent 枚举扩展(additive,version=1 不变)

### Removed Capabilities

- (无) — 老脚本路径以 shim 形式保留至 v2.2.0

## Impact

- **新增代码**: ~600 行 (guide-design/SKILL.md ~250 + scripts/ ~80 + schema ~30 + write_design_handoff.{py,sh} ~60 + plan_intake 新增 ~40 + 双扫描器改动 ~60 + session 三处 ~30 + shim ~20)
- **修改代码**: ~150 行 (guide-arch -100 + guide-plan +40 + 双扫描器 +60/-40 + session ~30 + add-improve/guide 引用 ~20)
- **搬移 + 重命名代码**: ~250 行 (Phase 5.5 脚本从 arch 移到 design)
- **文档改动**: ~300 行 (README/AGENTS/USAGE/ONBOARDING/proposal-format×2 + 新增 docs/v2-design-phase-guide.md ~200-300 行 + proposal-suggestions.md 头注释 + CHANGELOG)
- **新增测试**: ~35-40 个 (~9 Python unit + ~28 bats integration),另更新 4 个既有结构性测试(test_proposal_defer.bats)
- **向后兼容**: **硬切换** — 存量项目(有 arch-handoff 无 design-handoff)调用 `guide-plan` 将被拒绝并提示先运行 `guide-design`;逃生口为显式 `SKIP_ARCH_HANDOFF=yes`(同时跳过两个门控)或 direct-create fallback;README/AGENTS.md 顶部 banner 与门控同 commit 落地
- **ADR 处理**: 不动 ADR-0003(用户决策 2026-07-30)。ADR-0003 §三阶段描述将与代码漂移,作为已知风险接受;docs(AGENTS.md/README)将描述四阶段
- **迁移成本**: 中
- **风险**: 中 — 硬切换对存量项目是 breaking change,依赖 banner + 清晰错误提示缓解
- **来源**: 2026-07-30 架构讨论(用户决策);Oracle + Metis 双重审查后修订