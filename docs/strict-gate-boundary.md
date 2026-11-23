# STRICT_*_GATE 环境变量边界澄清

**版本**: v2（2026-11-23 修订：补「v4 实现状态」列 + 标注 v3 已消失的门）
**日期**: 2026-11-23
**关联**: ADR-0018, ADR-0019, ADR-0025, ADR-0030

> ⚠️ **v1（2026-08-15）的问题**：本文档是 v3 三阶段（`arch → design → plan → ship`）时代的产物，
> 列出的门控里有 **4 个在 v4 已无实现**（`STRICT_DESIGN_GATE` / `STRICT_PROPOSAL_COVERAGE` /
> `STRICT_CODE_GATE` / `RDDF_REQUIRE_HUB_APPROVAL`），另 1 个**只有文档没有代码**
> （`STRICT_CONTRACT_GATE`）⇒ v1 的 CI 配置示例照抄会得到「设了但不生效」的假象。
> v2 补「实现状态」列并把死门标出。

## STRICT_*_GATE 矩阵（v4 实现状态）

**实现状态判定口径**：`_lib/` + `skills/` 下的 `.sh` / `.py` 里有**读取点**（`os.environ` /
`${VAR}`）才算「有代码」；只在 `.md` 里出现 = 「仅文档」。**有代码 ≠ 生效** ——
还要看该代码是否在**生产路径**上被调用（见下方「`_lib/gate.py` 的机制未接线」）。

| Env Var | v4 阶段 | 引用 | 控制检查 | 启用时效果 | 实现状态 |
|---------|---------|------|---------|-----------|---------|
| `STRICT_ARCH_GATE` | arch-done | ADR-0018 | arch_quality_gate 4 个检查 | warning → error | ✅ **生效** `_lib/arch_quality_gate.py` ← `skills/rdd-arch/SKILL.md:595` |
| `STRICT_DEPS_GATE` | plan-done | add-cross-repo-deps-orchestration | 跨仓库依赖阻塞检测 | warning → error | ✅ **生效** `_lib/cross_repo_gate.py` ← `skills/rdd-builder/scripts/phase1_5_deps.sh` |
| `STRICT_ROADMAP_REFS_GATE` | — | roadmap fragment 引用校验 | roadmap refs 校验 | warning → error | ✅ **生效** `_lib/cli/roadmap_cmd.py` · `skills/roadmap/scripts/roadmap_validate_fragments.sh` |
| `STRICT_TASKS_GATE` | ship-done | 归档前 tasks 完成度 | tasks 完成度 | warning → error | ✅ **生效** `_lib/archive.sh` ← `skills/rdd-builder/scripts/phase3_archive.sh` |
| `STRICT_AC_GATE` | ship-done | 归档前 AC 覆盖 | AC 校验 | warning → error | ✅ **生效** `_lib/archive.sh` · `skills/rdd-builder/scripts/phase3_archive.sh` |
| `STRICT_FEATURE_VALIDATION` | plan-done | feature fragment 校验 | feature 一致性 | warning → error | ✅ **生效** `skills/propose/scripts/propose_change.py` |
| `STRICT_CHANGE_GATE` | plan-done | ADR-0019 | change_alignment 3 个检查 | warning → error | ⚠️ **有代码但未接线**（在 `_lib/gate.py:385-387`，见下） |
| `STRICT_PROPOSE_GATE` | plan-done | 历史 propose-quality-autohook | propose_quality_check | warning → error | ⚠️ **有代码但未接线**（在 `_lib/gate.py:390`） |
| `STRICT_DESIGN_GATE` | ~~design-done~~ | ADR-0025 | design_proposal_review 2 层审查 | warning → error | ❌ **无代码**（`design-done` 阶段随 ADR-0043 stage-merge 消失） |
| `STRICT_PROPOSAL_COVERAGE` | ~~design-done~~ | AGENTS.md §21 | theme coverage | warning → error | ❌ **无代码** |
| `STRICT_CODE_GATE` | ship-done | 「未来扩展」占位 | — | — | ❌ **从未实现**（v1 文档写作「v2.3+ 可能引入」） |
| `RDDF_REQUIRE_HUB_APPROVAL` | ~~design-done~~ | ADR-0031 | Hub Issue 未 Approved 阻断 | 阻断 | ❌ **无代码**（见下「已消失的门」） |
| `STRICT_CONTRACT_GATE` | ship-done | add-contract-lint-ci-gate | Breaking-Change 契约 lint 阻断 | warning → error | ⚠️ **仅文档**：`skills/contract-check/SKILL.md:10` 与 `skills/sync-hub/SKILL.md:55` 提到，**无代码读取**；`contract-check` 的实际分级靠 `SKIP_CONTRACT_GATE` / 默认 exit 码 |

### `_lib/gate.py` 的机制未接线（`STRICT_CHANGE_GATE` / `STRICT_PROPOSE_GATE`）

`_lib/gate.py` 定义了 `_DEFAULT_CHECKS`（按 `arch_done` / `plan_done` / `ship_done` 分组）
与 `GateMechanism` 类，但 **`GateMechanism` 在生产代码里零命中**（`_lib/gate.py:404` 是唯一定义处）
—— 没有任何 skill / CLI 在生产路径上实例化它，**只有测试 import**
（`tests/unit/test_gate.py` · `tests/integration/test_gate_transition.py`）。

⇒ 后果：`STRICT_CHANGE_GATE` / `STRICT_PROPOSE_GATE` 的**检查代码存在**，
但**设了环境变量也不会被触发**（`_lib/change_alignment.py` 也只被 `_lib/gate.py` import，
无其它调用方；doctor 的 category 列表里没有 change-alignment）。

⚠️ 这与「无代码」是**不同严重度**的问题 —— 前者是代码没写，后者是代码写了但没人调用。

## 已消失的门（v3 → v4）

### `STRICT_DESIGN_GATE` + `RDDF_REQUIRE_HUB_APPROVAL`

**v3 设计**（本文档 v1 保留）：
- `STRICT_DESIGN_GATE=yes` — **本地**设计审查（2 层内容审查 + 5 段格式 + ADR 引用）
- `RDDF_REQUIRE_HUB_APPROVAL=yes` — **跨项目** Hub Issue 状态检测
- 两者独立生效（不互斥）；`RDDF_REQUIRE_HUB_APPROVAL=yes` 时检测 `**分类**: cross-repo-federation` 自动挂起

**v4 现状**：**两者都没有实现**。
- `STRICT_DESIGN_GATE` 在 `_lib/` / `skills/` 中零读取点 —— `design-done` 阶段已随 ADR-0043
  stage-merge 并入 `rdd-planner`（v4 的阶段出口是 `planner-done`，见
  `skills/rdd-planner/scripts/planner_stage_exit.sh`）。
- `RDDF_REQUIRE_HUB_APPROVAL` 的唯一实现载体是 `skills/guide-design/scripts/approve_proposal.sh`
  （ADR-0031 的「跨项目人类兜底」硬阻断）—— 该脚本已随 v4 stage-merge 移除
  ⇒ **ADR-0031 的核心承诺「跨项目提案 AI 不可自动批准」当前无代码兑现**。
  ADR-0031 声称的集成测试 `tests/integration/test_strict_human_approval.bats` 也不存在。

⇒ 该门是**待裁决**项（重实现 vs 退役并标注 superseded），详见
`.rddf/reviews/docs-alignment-debt-audit-2026-11-23.md` §四·五 #31。

## 边界澄清

### 1. `STRICT_CHANGE_GATE` vs `STRICT_DEPS_GATE`

**场景**: 都是 plan-done 阶段的门控升级

**边界**:
- `STRICT_CHANGE_GATE=yes` — **单仓库** change 提案与架构对齐（ADR-0019）
  ⚠️ 当前**不生效**（机制未接线，见上）
- `STRICT_DEPS_GATE=yes` — **跨仓库**依赖图分析（✅ 生效）

**冲突解决**:
- 两者独立生效（同时启用时检查并集）
- `STRICT_DEPS_GATE` 不修改 `STRICT_CHANGE_GATE` 行为
- 实现位置**不同**：
  - `STRICT_CHANGE_GATE` → `_lib/gate.py:385-387` 注册 3 个 Check
    （`change_adr_refs_valid` / `change_no_contradiction` / `change_task_traceability`）
  - `STRICT_DEPS_GATE` → `_lib/cross_repo_gate.py::check_cross_repo_deps_blocked`
    （**不在 `_lib/gate.py` 的 Check 注册表里**；v1 文档写的 `cross_repo_deps_unblocked`
    这个 Check 名在代码中不存在）

### 2. `STRICT_CONTRACT_GATE` 与其他 GATE 的关系

**场景**: ship-done 阶段

**边界**:
- `STRICT_CONTRACT_GATE=yes` — 契约 lint 阻断（**⚠️ 当前仅文档，无代码读取**）
- `STRICT_AC_GATE=yes` — 归档前 AC 覆盖（✅ `_lib/archive.sh` 有实现）
- `STRICT_TASKS_GATE=yes` — 归档前 tasks 完成度（✅ `_lib/archive.sh` 有实现）

**未来扩展**:
- `STRICT_CODE_GATE`（控制 ship_done code-level checks）—— 至今未实现

## 推荐 CI 配置（v4 实况）

> ⚠️ **前提**：env var 必须在**执行该门的那条路径**上生效。
> `STRICT_ARCH_GATE` 的读取点在 `skills/rdd-arch/scripts/arch_quality_report.sh`
> （由 `skills/rdd-arch/SKILL.md:595` source）⇒ 它在 **rdd-arch skill 流程**里触发，
> **不在 `rddf arch` CLI 里**（`rdd_arch_cmd.py` 不 import `arch_quality_gate`）。

```yaml
# .github/workflows/test.yml —— 只列**确实生效**的门
jobs:
  arch-validation:
    env:
      STRICT_ARCH_GATE: 'yes'          # ✅ 生效（rdd-arch skill 的 arch_quality_report.sh）
    steps:
      - run: pytest tests/unit/test_arch_quality_gate.py

  plan-validation:
    env:
      STRICT_DEPS_GATE: 'yes'           # ✅ 生效（rdd-builder P1.5，跨仓库项目）
    steps:
      - run: pytest tests/unit/test_cross_repo_gate.py

  ship-validation:
    env:
      STRICT_AC_GATE: 'yes'             # ✅ 生效（_lib/archive.sh 归档门）
      STRICT_TASKS_GATE: 'yes'          # ✅ 生效（_lib/archive.sh 归档门）
    steps:
      - run: rddf archive
```

> ⚠️ **不要**设 `STRICT_DESIGN_GATE` / `RDDF_REQUIRE_HUB_APPROVAL` / `STRICT_PROPOSAL_COVERAGE`
> —— 设了也不生效（无读取点），只会造成「以为门开着」的错觉。
>
> ⚠️ `STRICT_CHANGE_GATE` / `STRICT_PROPOSE_GATE` 当前**同样不生效**（`_lib/gate.py` 的
> `GateMechanism` 未在生产路径接线，见上）—— 与「无代码」的三个区别在于：**接线后可生效**。

## 命名规范

| 模式 | 含义 | 示例 | v4 状态 |
|------|------|------|---------|
| `STRICT_*_GATE` | 阶段门控升级（参考 ADR-0018 模式） | `STRICT_ARCH_GATE`, `STRICT_DEPS_GATE`, `STRICT_ROADMAP_REFS_GATE`, `STRICT_TASKS_GATE`, `STRICT_AC_GATE`, `STRICT_FEATURE_VALIDATION` | ✅ 6 个生效 |
| `STRICT_*_GATE`（未接线） | 同上，但机制未在生产路径调用 | `STRICT_CHANGE_GATE`, `STRICT_PROPOSE_GATE` | ⚠️ 代码在、触发不到 |
| `STRICT_*_COVERAGE` | 主题覆盖度（参考 AGENTS.md §21） | `STRICT_PROPOSAL_COVERAGE` | ❌ 唯一实例无实现 |
| `RDDF_REQUIRE_*` | 跨项目强制门控 | `RDDF_REQUIRE_HUB_APPROVAL` | ❌ 唯一实例无实现 |
| `SKIP_*` | 绕过机制（高级，谨慎） | `SKIP_CONTRACT_GATE` | ⚠️ 仅 `SKIP_CONTRACT_GATE` 有代码命中（`skills/rdd-doctor/scripts/checks/bypass_audit_check.py`，且只是**审计计数**不是**读取该变量**）；v1 文档列的 `SKIP_DESIGN_HANDOFF` / `SKIP_CONTENT_REVIEW` / `SKIP_ADR_CONFIRM` **全仓零命中** |

**注**: `RDDF_REQUIRE_*` 是 v3 引入的跨项目强制门控模式；其唯一实例当前无实现，
新增该模式的门之前应先确认上一个是否落地。

## 提案冲突避免规则

1. **同阶段多个 STRICT_*_GATE**：定义阶段门控的"独立维度"（如 contract 检查 vs deps 检查）
2. **跨阶段门控**：使用 `RDDF_REQUIRE_*` 命名（避免与现有模式冲突）
3. **新增 STRICT_*_GATE 流程**：
   1. 写入本文档
   2. 注册到**已接线的**门机制（`_lib/arch_quality_gate.py` / `_lib/cross_repo_gate.py` /
      `_lib/archive.sh` 等）—— ⚠️ 不要只注册进 `_lib/gate.py`：它的 `GateMechanism`
      当前没有生产调用方，注册进去等于不生效
   3. 加单元测试（参照 STRICT_ARCH_GATE 测试模式）
   4. 更新 CI 配置示例
   5. **验证触发链**：确认该 env var 在**生产路径**上被读取（grep 读取点 + 确认调用方在
      skill/CLI 的执行链上），否则在「实现状态」列如实标 ⚠️/❌
