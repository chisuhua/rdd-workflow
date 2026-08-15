# STRICT_*_GATE 环境变量边界澄清

**版本**: v1
**日期**: 2026-08-15
**关联**: ADR-0018, ADR-0019, ADR-0025, ADR-0030

## 现有 STRICT_*_GATE 矩阵

| Env Var | 阶段 | 引用 | 控制检查 | 启用时效果 |
|---------|------|------|---------|----------|
| `STRICT_ARCH_GATE` | arch-done | ADR-0018 | arch_quality_gate 4 个检查 | warning → error |
| `STRICT_CHANGE_GATE` | plan-done | ADR-0019 | change_alignment 3 个检查 | warning → error |
| `STRICT_DESIGN_GATE` | design-done | ADR-0025 | design_proposal_review 2 层审查 | warning → error |
| `STRICT_PROPOSE_GATE` | plan-done | 历史 propose-quality-autohook | propose_quality_check | warning → error |
| `STRICT_PROPOSAL_COVERAGE` | design-done | AGENTS.md §21 | theme coverage | warning → error |

## Hub-and-Spoke 提案新增（ADR-0030 衍生）

| Env Var | 提案 | 阶段 | 控制检查 | 优先级 |
|---------|------|------|---------|--------|
| `RDDF_REQUIRE_HUB_APPROVAL` | add-strict-human-approval-for-cross-repo-changes (Step 1.5) | design-done | Hub Issue 未 Approved 阻断 | P1 |
| `STRICT_CONTRACT_GATE` | add-contract-lint-ci-gate (Step 5) | ship-done | Breaking-Change 契约 lint 阻断 | P1 |
| `STRICT_DEPS_GATE` | add-cross-repo-deps-orchestration (Step 6) | plan-done | 跨仓库依赖阻塞检测 | P1 |

## 边界澄清

### 1. `STRICT_DESIGN_GATE` vs `RDDF_REQUIRE_HUB_APPROVAL`

**场景**: 都是 design-done 阶段的门控升级

**边界**:
- `STRICT_DESIGN_GATE=yes` — **本地**设计审查（2 层内容审查 + 5 段格式 + ADR 引用）
- `RDDF_REQUIRE_HUB_APPROVAL=yes` — **跨项目** Hub Issue 状态检测

**推荐组合**:
```bash
# 单仓库项目：仅 design 审查
export STRICT_DESIGN_GATE=yes

# 多仓库 / 跨项目项目：两者都启用
export STRICT_DESIGN_GATE=yes
export RDDF_REQUIRE_HUB_APPROVAL=yes
```

**实现机制**:
- 两个 env var 独立生效（不互斥）
- `RDDF_REQUIRE_HUB_APPROVAL=yes` 时检测 `**分类**: cross-repo-federation` 自动挂起
- 未设 `RDDF_REQUIRE_HUB_APPROVAL` 时，cross-repo 提案仅按 `STRICT_DESIGN_GATE` 规则

### 2. `STRICT_CHANGE_GATE` vs `STRICT_DEPS_GATE`

**场景**: 都是 plan-done 阶段的门控升级

**边界**:
- `STRICT_CHANGE_GATE=yes` — **单仓库** change 提案与架构对齐（ADR-0019）
- `STRICT_DEPS_GATE=yes` — **跨仓库**依赖图分析

**冲突解决**:
- 两者独立生效（同时启用时检查并集）
- `STRICT_DEPS_GATE` 不修改 `STRICT_CHANGE_GATE` 行为
- 实施时 `_lib/gate.py` 注册 2 个独立 Check：
  - `cross_repo_deps_unblocked` (env_var=STRICT_DEPS_GATE)
  - `change_adr_refs_valid` 等 (env_var=STRICT_CHANGE_GATE)

### 3. `STRICT_CONTRACT_GATE` 与其他 GATE 的关系

**场景**: ship-done 阶段

**边界**:
- `STRICT_CONTRACT_GATE=yes` — 契约 lint 阻断
- **同阶段无其他 STRICT_*_GATE**（当前 ship 阶段无 quality gate）

**未来扩展**:
- v2.3+ 可能引入 `STRICT_CODE_GATE`（控制 ship_done code-level checks）

## 推荐 CI 配置

```yaml
# .github/workflows/test.yml (多仓库项目)
jobs:
  arch-validation:
    env:
      STRICT_ARCH_GATE: 'yes'
    steps:
      - run: pytest tests/unit/test_arch_quality_gate.py

  plan-validation:
    env:
      STRICT_CHANGE_GATE: 'yes'
      STRICT_DEPS_GATE: 'yes'  # 跨仓库项目
    steps:
      - run: rddf plan-done-check

  design-validation:
    env:
      STRICT_DESIGN_GATE: 'yes'
      RDDF_REQUIRE_HUB_APPROVAL: 'yes'  # 跨仓库项目
    steps:
      - run: rddf design-done-check

  ship-validation:
    env:
      STRICT_CONTRACT_GATE: 'yes'  # 跨仓库项目
    steps:
      - run: rddf contract-check --strict
```

## 命名规范

| 模式 | 含义 | 示例 |
|------|------|------|
| `STRICT_*_GATE` | 阶段门控升级（参考 ADR-0018 模式） | `STRICT_ARCH_GATE`, `STRICT_CHANGE_GATE`, `STRICT_DESIGN_GATE`, `STRICT_PROPOSE_GATE`, `STRICT_CONTRACT_GATE`, `STRICT_DEPS_GATE` |
| `STRICT_*_COVERAGE` | 主题覆盖度（参考 AGENTS.md §21） | `STRICT_PROPOSAL_COVERAGE` |
| `RDDF_REQUIRE_*` | 跨项目强制门控（新增模式） | `RDDF_REQUIRE_HUB_APPROVAL` |
| `SKIP_*` | 绕过机制（高级，谨慎） | `SKIP_DESIGN_HANDOFF`, `SKIP_CONTENT_REVIEW`, `SKIP_ADR_CONFIRM` |

**注**: `RDDF_REQUIRE_*` 是新引入模式，专用于跨项目强制门控，避免与 `STRICT_*_GATE` 现有命名冲突。

## 提案冲突避免规则

1. **同阶段多个 STRICT_*_GATE**：定义阶段门控的"独立维度"（如 contract 检查 vs deps 检查）
2. **跨阶段门控**：使用 `RDDF_REQUIRE_*` 命名（避免与现有模式冲突）
3. **新增 STRICT_*_GATE 流程**：
   - 1. 写入本文档
   - 2. 在 `_lib/gate.py` 注册独立 Check
   - 3. 加单元测试（参照 STRICT_ARCH_GATE 测试模式）
   - 4. 更新 CI 配置示例
