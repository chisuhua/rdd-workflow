# v3.0 → v4.0 迁移指南

> **适用对象**: 正在使用 rdd-workflow v3.0+ 五阶段架构 (`arch → design → plan → ship → verify`) 的项目，升级到 v4.0+ 四阶段架构 (`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`) + `rdd-quick` 旁路。
>
> **参考 ADR**: [ADR-0043](../adr/ADR-0043-rdd-workflow-v4-stage-merge.md) (v4 stage-merge) / [ADR-0044](../adr/ADR-0044-v4-stage-merge-wave3-hard-removal.md) (Wave 3 hard removal) / [ADR-0047](../adr/ADR-0047-rdd-quick-bypass-path.md) (rdd-quick bypass)
>
> **升级目标版本**: `v4.0.0` (当前 latest stable per `package.json`)

## 阶段数变化

v3.0+ 五阶段模型 (`arch → design → plan → ship → verify`) 在 v4.0+ 合并为四阶段。`design` 与 `plan` + `ship` 阶段的内化是最大变化：

| v3.0+ (5 stages) | v4.0+ (4 stages + bypass) | 变更说明 |
|------------------|---------------------------|---------|
| arch | rdd-arch | Stage 1 — 架构定义 (保留, slim 化) |
| design | rdd-planner | Stage 2 — design + plan authoring 合并到 rdd-planner (per ADR-0025/0042) |
| plan | rdd-builder | Stage 3.1 — 内化为 rdd-builder P1 phase (per ADR-0043) |
| ship | rdd-builder | Stage 3.2 — 内化为 rdd-builder P2/P3 phase (per ADR-0043) |
| verify | rdd-verifier | Stage 4 — 保留为独立阶段 (per ADR-0034 + ADR-0045 自包含 LLM 验证) |
| (新增) | rdd-quick | 旁路 — 小改动快速执行 (per ADR-0047) |

**核心变化**: `plan` + `ship` 两个 stage skill (`guide-plan` / `guide-ship`) 已合并为单一 `rdd-builder` skill，**内部 6-phase 状态机 P0→P3** 自动选择当前 phase（approval → plan → deps → archive）。

## Skill 重命名映射

| 旧 skill (v3.0+) | 新 skill (v4.0+) | 状态 |
|---------|---------|------|
| `guide-arch` | `rdd-arch` | **重命名** (per ADR-0042) |
| `guide-design` | `rdd-planner` | **重命名 + 范围扩大** (proposal authoring + review + defer) |
| `guide-plan` | (内化) | **删除**，被 rdd-builder P1 吸收 |
| `guide-ship` | (内化) | **删除**，被 rdd-builder P2/P3 吸收 |
| `rdd-verifier` | `rdd-verifier` | 保留 (per ADR-0034) |
| (新增) | `rdd-quick` | **新增** (per ADR-0047) |
| `guide` | `guide` | 推荐器保留 (推荐 v4 阶段) |
| `ac-verifier` | (内联) | **删除**，v2.0 内联到 rdd-verifier (per ADR-0045) |

## Removed skills (不再可用)

以下 skills 已在 Wave 3 hard removal 中物理删除（per ADR-0044）。任何 `skill_use(...)` 调用会立即失败：

- ❌ `guide-design` → 请改用 `skill_use("rdd-planner")`
- ❌ `guide-plan` → 请改用 `skill_use("rdd-builder")`
- ❌ `guide-ship` → 请改用 `skill_use("rdd-builder")`
- ❌ `guide-spec` → v2.0 已删除，请用 `skill_use("rdd-arch")` 或 `skill_use("rdd-planner")`
- ❌ `ac-verifier` → v2.0 内联到 `rdd-verifier` (per ADR-0045)，无需单独调用

## 工作流变更

### v3.0+ (旧)

```
arch → design → plan → ship → verify
         ↓        ↓      ↓
       提案审查   生成计划  执行+归档
```

每个 stage 各自独立 skill（`guide-arch` / `guide-design` / `guide-plan` / `guide-ship` / `rdd-verifier`），AI 需要手动选择下一个 stage。

### v4.0+ (新)

```
rdd-arch → rdd-planner → rdd-builder → rdd-verifier
                          └─ 6-phase internal: P0 (approval) → P1 (plan) → P1.5 (deps) → P2 (execute) → P2.5 (review) → P3 (archive)
                                       └─ verifier retry loop (P3 → P1 or P2, max 3)
                                          │
rdd-quick (旁路) ──── 直接 TDD 5 步 + Oracle 验证，绕过 openspec change + worktree
```

**关键差异**:

1. **rdd-builder 是复合 stage** — 调用一次内部 6-phase 自动流转，无需 AI 手动分阶段切换
2. **rdd-verifier 在 archive 前自动跑**（per ADR-0034 spec §3.4 Phase 3 pre-call）— 失败回 builder P1/P2 retry（max 3 per ADR-0034 §8）
3. **rdd-quick 旁路** — 小改动无需 openspec change，直接原地 TDD 5 步 + Oracle 验证（per ADR-0047）

## 升级步骤

### 1. 全局安装最新版

```bash
# 推荐:全局安装 (跨项目可用)
bash ~/.agents/rdd-workflow/install.sh --global

# 或项目级安装
bash /path/to/rdd-workflow/install.sh /path/to/project
```

验证安装：

```bash
ls ~/.agents/skills/ | grep rdd-
# 期望: rdd-arch, rdd-planner, rdd-builder, rdd-verifier, rdd-quick
ls ~/.agents/skills/ | grep guide-
# 期望: 只有 guide 推荐器; guide-arch/design/plan/ship 应不存在
```

### 2. 替换 active change 中的 skill 调用

打开所有 `openspec/changes/*/proposal.md` 和 `openspec/changes/*/tasks.md`，用 `sed` 批量替换：

```bash
# 一次性替换所有 openspec/changes/*/proposal.md 和 openspec/changes/*/tasks.md
find openspec/changes -name "*.md" -exec sed -i \
  -e 's/skill_use("guide-design")/skill_use("rdd-planner")/g' \
  -e 's/skill_use("guide-plan")/skill_use("rdd-builder")/g' \
  -e 's/skill_use("guide-ship")/skill_use("rdd-builder")/g' \
  -e 's/skill_use("guide-spec")/skill_use("rdd-arch")/g' \
  {} +
```

如果有用 `guide-design.md` / `guide-plan.md` / `guide-ship.md` 的 SKILL.md 引用，一并替换：

```bash
find skills/ -name "SKILL.md" -exec sed -i \
  -e 's|`guide-design.md`|`rdd-planner.md`|g' \
  -e 's|`guide-plan.md`|`rdd-builder.md`|g' \
  -e 's|`guide-ship.md`|`rdd-builder.md`|g' \
  {} +
```

### 3. 跑 regression 验证

```bash
./test.sh --full --regression
```

期望: 没有新失败（与 `tests/KNOWN_FAILURES.txt` baseline 对比）。

### 4. 跑 rdd-doctor 验证文档一致性

```bash
bash skills/rdd-doctor/scripts/doctor.sh
```

期望: CRITICAL 不超过升级前基线（v4.0+ 当前基线 = 6 CRITICAL）。

### 5. (可选) 注册 `rdd-quick` 旁路

如果项目有大量小改动（≤2 文件 + ≤3 任务），推荐启用 `rdd-quick` 旁路：

```bash
# 查看 rdd-quick 用法
skill_use("rdd-quick")
```

详见 [ADR-0047](../adr/ADR-0047-rdd-quick-bypass-path.md) 适用范围。

## FAQ

**Q: 我现有 change 还是用 `guide-plan`，会失效吗？**

A: 是的。Wave 3 hard removal (ADR-0044) 后 `guide-*` skill 已物理删除。旧 change 会立即报错。请用上述 sed 命令批量替换。

**Q: `rdd-builder` 看起来工作量变大（plan+execute+archive 都在里面）？**

A: 是的。v4 把 plan/execute/archive 整合为内部 6-phase 状态机 P0→P3 (per ADR-0043)。每次 `skill_use("rdd-builder")` 会自动选择当前 phase，无需手动切换。

**Q: `rdd-verifier` 跟 v3.0+ 一样吗？**

A: 大部分一样，但 v2.0 内联了 `ac-verifier` (per ADR-0045)。`rdd-verifier` 现在自包含 LLM 验证，无需 `AC_LLM_*` 配置。

**Q: `rdd-quick` 是什么？什么时候用？**

A: `rdd-quick` 是 v4.0+ 新增的小改动快速执行旁路（per ADR-0047）。适用于 ≤2 文件 + ≤3 任务的小改动，无需 openspec change + worktree，直接原地 TDD 5 步 + Oracle 验证。**不适用于**架构变更、跨项目协同、复杂多文件改动。

**Q: 我能用 `rdd-quick` 替代整个流程吗？**

A: 仅适合小改动。详见 [ADR-0047](../adr/ADR-0047-rdd-quick-bypass-path.md) §适用范围。

**Q: v3.0+ 五阶段模型完全废弃了吗？**

A: 5-stage 架构（`arch → design → plan → ship → verify`）在 v4.0+ 已合并为四阶段（per ADR-0043/0044）。Wave 3 hard removal 已删除 `guide-design`/`guide-plan`/`guide-ship` 三个 skill。**没有自动回滚路径**——如果需要 v3 兼容，必须保留旧 skill 的镜像分支。

**Q: CHANGELOG.md / USAGE.md / AGENTS.md 同步了吗？**

A: 已通过 `fix-doc-drift-v4-architecture` (f4d675b, 2026-09-08 archived) + `docs-v4-sync-followup-v2` (Oracle-approved, 待归档) + `fix-doc-drift-followup-3` (本提案) 三批同步。当前 master 分支的 CHANGELOG/USAGE/AGENTS 已正确描述 v4 模型。

**Q: ADR-0043/0044/0047 在哪里看？**

A:
- [ADR-0043 v4 stage-merge](../adr/ADR-0043-rdd-workflow-v4-stage-merge.md)
- [ADR-0044 Wave 3 hard removal](../adr/ADR-0044-v4-stage-merge-wave3-hard-removal.md)
- [ADR-0047 rdd-quick bypass](../adr/ADR-0047-rdd-quick-bypass-path.md)

## 参考

- [ADR-0043: v4 stage-merge](../adr/ADR-0043-rdd-workflow-v4-stage-merge.md)
- [ADR-0044: Wave 3 hard removal of guide-*](../adr/ADR-0044-v4-stage-merge-wave3-hard-removal.md)
- [ADR-0047: rdd-quick bypass](../adr/ADR-0047-rdd-quick-bypass-path.md)
- [AGENTS.md](../../AGENTS.md) §关键约定 (项目地图)
- [README.md](../../README.md) §v4.0+ 当前架构
- [USAGE.md](../../USAGE.md) §四阶段架构表
- [spec 2026-09-04-rdd-workflow-v4-architecture-stage-merge.md](../../superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md) (设计稿)