---
优先级: P1
来源: 2026-09-09 文档与代码一致性审计（第 3 波）
阶段: default
分类: docs
类型: improvement
状态: ✅ 已实施 (2026-09-09, commit 0ba5ae4 "feat(change): fix-doc-drift-followup-3 — planner-approve + plan + tasks artifacts" + commit 2b39d6b "fix(doc): guide recommender + v3-to-v4 migration guide"; per feat-fix-archive-gaps-v2 phase-4 推进)
依赖: "本提案建立在已完成 `fix-doc-drift-v4-architecture` (commit f4d675b, 已 archived) + 待归档 `docs-v4-sync-followup-v2` 之上；不与前两批重叠。"
---
**优先级**: P1 | **来源**: 2026-09-09 文档与代码一致性审计（第 3 波）
**阶段**: default | **分类**: docs
**类型**: improvement
**依赖**: 本提案建立在已完成 `fix-doc-drift-v4-architecture` (commit f4d675b, 已 archived) + 待归档 `docs-v4-sync-followup-v2` 之上；不与前两批重叠。
**状态**: ✅ 已实施 (2026-09-09, commits 0ba5ae4 + 2b39d6b) — per feat-fix-archive-gaps-v2 phase-4 推进

## 架构依据

`fix-doc-drift-v4-architecture` (f4d675b) 覆盖了 8 个文档文件（README/USAGE/AGENTS/CHANGELOG/3 个 docs/architecture/）。
`docs-v4-sync-followup-v2` (Oracle-approved, 待归档) 覆盖了 6 个文档文件（ONBOARDING/improvement-check-mechanisms/INSTALL/skills-and-handoff/multi-project/extension-points）。

**两批都已归档/待归档后**，2026-09-09 第三轮审计（doctor + 3 agent 并行扫描）发现仍有 **12 个文件、35 处 active `skill_use("guide-*")` 或 `rdd-*` 描述漂移**未覆盖。最严重的是 **`skills/guide/SKILL.md`** —— 这是用户主入口的推荐器，**当前会让 AI 助手去调用 Wave 3 已删除的 `guide-ship`/`guide-design`/`guide-plan`**，每次调用都直接报错。

### 漂移清单（2026-09-09 第 3 轮审计）

| # | 文件 | 命中数 | 性质 | 严重度 |
|---|------|--------|------|--------|
| 1 | `skills/guide/SKILL.md` | 30+ | active `skill_use("guide-*")` invocations + stage list | **P0（CRITICAL）** |
| 2 | `skills/rdd-verifier/SKILL.md` | 8 | routing context 中 `guide-ship`/`guide-plan` | P1 |
| 3 | `skills/status/SKILL.md` | 5 | 描述 + `guide-ship.md` 文件引用（文件已删） | P1 |
| 4 | `skills/execute/SKILL.md` | 4 | 描述 + `$RDDF_EXECUTION_ROOT` 路由上下文 | P1 |
| 5 | `skills/rddf-session/SKILL.md` | 3 | `guide-plan`/`guide-ship` 在 phase routing | P1 |
| 6 | `skills/sync-hub/SKILL.md` | 1 | "被 guide-design 在 contract refresh 时调用" | P2 |
| 7 | `skills/add-improve/SKILL.md` | 1 | `skill_use("guide-design")` 实际调用 | P2 |
| 8 | `skills/feature/SKILL.md` | 1 | "run guide-plan once first" | P2 |
| 9 | `skills/deps/SKILL.md` | 1 | "被 guide-plan 在 propose 完成后自动调用" | P2 |
| 10 | `skills/openspec-gate/SKILL.md` | 1 | `skill_use("guide-plan")` 实际调用 | P2 |
| 11 | `docs/migration/v3-to-v4.md` | **缺失文件** | 被 `docs/ONBOARDING.md:375` 显式引用 | **P0（HIGH）** |
| 12 | `README.md` L13-19 | 1 | npm install 命令显示 v1.x/v2.0-beta，实际 v4.0.0 | P2 |

### 为什么这是 CRITICAL

**`skills/guide/SKILL.md`** 是 AI agent 调用 workflow 的入口：

```markdown
# 现状（guide/SKILL.md L143-145）
| 2 | design | `skill_use("guide-design")` | design 阶段（per ADR-0025）|
| 3 | plan   | `skill_use("guide-plan")`    | plan 阶段（per ADR-0024）|
| 4 | ship   | `skill_use("guide-ship")`    | ship 阶段（per ADR-0024）|
```

按 Wave 3 hard removal（ADR-0044），`guide-design`/`guide-plan`/`guide-ship` 三个 skill 已被硬删除。任何 AI agent 读这个 SKILL.md 后调用 `skill_use("guide-ship")` 都会立即报错并中止 workflow。

**`docs/migration/v3-to-v4.md`** 被 `docs/ONBOARDING.md:375` 显式引用作为迁移指南，但文件不存在 — 新用户按 onboarding 操作会 404。

## 范围

**In Scope（12 个文件，3 类修复）**:

### Phase A: P0 必修（2 项，会让用户/agent 流程坏掉）

A1. **`skills/guide/SKILL.md`**（30+ 处）— 全部 `guide-design`/`guide-plan`/`guide-ship` 替换为 `rdd-planner`/`rdd-builder`/`rdd-builder`，stage list 改为 4 阶段 + 旁路
A2. **创建 `docs/migration/v3-to-v4.md`** — 用户从 v3.0 → v4.0 迁移指南，至少覆盖：
- 阶段数变化（5 → 4）
- skill 重命名映射表（`guide-arch → rdd-arch` 等）
- `rdd-quick` 旁路路径何时使用
- removed skills 列表（`guide-design`/`guide-plan`/`guide-ship`/`guide-spec`）
- 引用 ADR-0043/0044/0047

### Phase B: P1 子技能 SKILL.md（5 项，影响子流程调用方）

B1. **`skills/execute/SKILL.md`** L3,48,146 — 改 `guide-ship` → `rdd-builder`
B2. **`skills/status/SKILL.md`** L3,173,321,479,492 — 改 `guide-ship` → `rdd-builder`，删除对 `guide-ship.md` 的死链引用
B3. **`skills/rddf-session/SKILL.md`** L108,312,378 — `guide-plan`/`guide-ship` → `rdd-builder`，phase routing 上下文
B4. **`skills/rdd-verifier/SKILL.md`** L3,32,88,101,103,213,220,328,353 — routing context 中 `guide-ship`/`guide-plan` → `rdd-builder`（保留 backwards-compat 标记）
B5. **`skills/rdd-env-check/SKILL.md`** L3 — phase 列表：`rdd-arch/guide-design/guide-plan/guide-ship` → `rdd-arch/rdd-planner/rdd-builder`

### Phase C: P2 子技能 SKILL.md（5 项，影响最小但仍不准确）

C1. `skills/add-improve/SKILL.md` L96 — `skill_use("guide-design")` → `skill_use("rdd-planner")`
C2. `skills/feature/SKILL.md` L5 — "run guide-plan once first" → "run rdd-builder once first"
C3. `skills/deps/SKILL.md` L3 — "被 guide-plan 调用" → "被 rdd-builder 调用"
C4. `skills/sync-hub/SKILL.md` L3 — "被 guide-design 在 contract refresh 时调用" → "被 rdd-planner 在 contract refresh 时调用"
C5. `skills/openspec-gate/SKILL.md` L56 — `skill_use("guide-plan")` → `skill_use("rdd-builder")`

### Phase D: README install 段（1 项）

D1. **`README.md` L13-19** — `npm install rdd-workflow` (v1.x) + `npm install rdd-workflow@2.0.0-beta` → `npm install rdd-workflow@4` 或仅保留 main branch install；标注当前 latest stable = v4.0.0

### Test additions（extend 既有 `tests/integration/test_v4_doc_drift_contracts.bats`）

- **Test 16**: `skills/guide/SKILL.md` 不含 active `skill_use("guide-*")` invocations
- **Test 17**: `skills/execute/SKILL.md` `skills/status/SKILL.md` `skills/deps/SKILL.md` `skills/add-improve/SKILL.md` `skills/feature/SKILL.md` `skills/sync-hub/SKILL.md` `skills/rddf-session/SKILL.md` `skills/openspec-gate/SKILL.md` `skills/rdd-env-check/SKILL.md` 不含 `guide-design`/`guide-plan`/`guide-ship`（除合法 backwards-compat 注释外）
- **Test 18**: `docs/migration/v3-to-v4.md` 文件存在且 ≥ 80 行
- **Test 19**: `README.md` L13-19 npm install 段不含 `v1.x` 或 `v2.0-beta` 字样

### Out of Scope（不与本提案重叠，已被前两批覆盖）

- README.md / USAGE.md / AGENTS.md / CHANGELOG.md — 已在 `fix-doc-drift-v4-architecture`
- docs/ONBOARDING.md / docs/architecture/* (除 v3-to-v4.md) — 已在 `docs-v4-sync-followup-v2`
- 历史性 prose 提及（如 `openspec/specs/archive-gate-verification/spec.md` 等 archived specs）— 故意保留作为 v3 演进记录
- `_lib/` 代码 docstring 内的 `guide-ship/scripts/ship_*.sh` 路径引用 — 属于 code-docstring-cleanup-v4-rename，独立提案
- USAGE.md 14 处 prose guide-* 提及（非 active `skill_use`）— 已在 `docs-v4-sync-followup-v2` Out of Scope

## 设计

### 命名映射（统一查询表）

| 旧名（已删） | 新名 | 备注 |
|-------------|------|------|
| `guide-arch` | `rdd-arch` | Stage 1 |
| `guide-design` | `rdd-planner` | Stage 2（per ADR-0025/0042） |
| `guide-plan` | `rdd-builder` | Stage 3 的 plan 子阶段（合并到 rdd-builder per ADR-0043） |
| `guide-ship` | `rdd-builder` | Stage 3 的 ship 子阶段（同上） |
| `guide-spec` | (removed) | v2.0 已删，无替代 |
| `guide` | `guide`（保留） | 推荐器本身不是阶段 skill，未删 |

### `skills/guide/SKILL.md` 关键改动示例

```diff
 # Stage 菜单 (示例 L143-145)
-| 2 | design | `skill_use("guide-design")` | design 阶段（per ADR-0025）|
-| 3 | plan   | `skill_use("guide-plan")`    | plan 阶段（per ADR-0024）|
-| 4 | ship   | `skill_use("guide-ship")`    | ship 阶段（per ADR-0024）|
+| 2 | planner | `skill_use("rdd-planner")` | planner 阶段（per ADR-0042）|
+| 3 | builder | `skill_use("rdd-builder")` | builder 阶段（6-phase P0→P3 per ADR-0043）|
+| 4 | verifier| `skill_use("rdd-verifier")` | verifier 阶段（per ADR-0034）|

 # 旁路选项
+| 5 | quick    | `skill_use("rdd-quick")`    | 小改动快速执行（per ADR-0047）|
```

### `docs/migration/v3-to-v4.md` 模板

```markdown
# v3.0 → v4.0 迁移指南

> 适用对象: 正在使用 rdd-workflow v3.0+ 五阶段架构 (`arch → design → plan → ship → verify`) 的项目，升级到 v4.0+ 四阶段架构 (`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`) + `rdd-quick` 旁路。
>
> 参考 ADR: ADR-0043 (v4 stage-merge) / ADR-0044 (Wave 3 hard removal) / ADR-0047 (rdd-quick bypass)

## 阶段数变化

| v3.0+ (5 stages) | v4.0+ (4 stages + bypass) | 变更说明 |
|------------------|---------------------------|---------|
| arch | rdd-arch | Stage 1 — 架构定义 (保留) |
| design | rdd-planner | Stage 2 — design + plan authoring 合并到 rdd-planner (per ADR-0025/0042) |
| plan | rdd-builder | Stage 3.1 — 内化为 rdd-builder P1 phase (per ADR-0043) |
| ship | rdd-builder | Stage 3.2 — 内化为 rdd-builder P2/P3 phase (per ADR-0043) |
| verify | rdd-verifier | Stage 4 — 保留为独立阶段 (per ADR-0034 + ADR-0045) |
| (新增) | rdd-quick | 旁路 — 小改动快速执行 (per ADR-0047) |

## Skill 重命名映射

| 旧 skill | 新 skill | 状态 |
|---------|---------|------|
| `guide-arch` | `rdd-arch` | 重命名 |
| `guide-design` | `rdd-planner` | 重命名 + 范围扩大 |
| `guide-plan` | (内化) | 删除，被 rdd-builder P1 吸收 |
| `guide-ship` | (内化) | 删除，被 rdd-builder P2/P3 吸收 |
| `rdd-verifier` | `rdd-verifier` | 保留 |
| (新增) | `rdd-quick` | 新增 |
| `guide` | `guide` | 推荐器保留 |

## Removed skills（不再可用）

- `guide-design` → 请改用 `skill_use("rdd-planner")`
- `guide-plan` → 请改用 `skill_use("rdd-builder")`
- `guide-ship` → 请改用 `skill_use("rdd-builder")`
- `guide-spec` → v2.0 已删除
- `ac-verifier` → v2.0 内联到 `rdd-verifier` (per ADR-0045)

## 工作流变更

v3.0: `arch → design → plan → ship → verify` (5 stages, 各自独立 skill)

v4.0: `rdd-arch → rdd-planner → rdd-builder → rdd-verifier` (4 stages)
       └─ `rdd-quick` 旁路（小改动直接走 TDD 5 步 + Oracle 验证）

## 升级步骤

1. 全局安装最新版: `bash install.sh --global`
2. 验证 skill 列表: `ls ~/.agents/skills/ | grep rdd-`
3. 替换 active change 中的 skill 调用:
   ```bash
   # 一次性替换所有 openspec/changes/*/proposal.md 和 openspec/changes/*/tasks.md
   find openspec/changes -name "*.md" -exec sed -i \
     -e 's/skill_use("guide-design")/skill_use("rdd-planner")/g' \
     -e 's/skill_use("guide-plan")/skill_use("rdd-builder")/g' \
     -e 's/skill_use("guide-ship")/skill_use("rdd-builder")/g' \
     -e 's/skill_use("guide-spec")/skill_use("rdd-arch")/g' \
     {} +
   ```
4. 跑 regression: `./test.sh --full --regression`
5. 可选: 注册 `rdd-quick` 旁路（如果项目有大量小改动）

## FAQ

**Q: 我现有 change 还是用 `guide-plan`，会失效吗？**
A: 是的。Wave 3 hard removal (ADR-0044) 后 `guide-*` skill 已物理删除。旧 change 会立即报错。请用上述 sed 命令批量替换。

**Q: `rdd-builder` 看起来工作量变大（plan+execute+archive 都在里面）？**
A: 是的。v4 把 plan/execute/archive 整合为内部 6-phase 状态机 P0→P3 (per ADR-0043)。每次 `skill_use("rdd-builder")` 会自动选择当前 phase，无需手动切换。

**Q: 我能用 `rdd-quick` 替代整个流程吗？**
A: 仅适合小改动（≤2 文件、≤3 任务）。详见 ADR-0047 §适用范围。

## 参考

- [ADR-0043: v4 stage-merge](docs/adr/ADR-0043-v4-architecture-stage-merge.md)
- [ADR-0044: Wave 3 hard removal of guide-*](docs/adr/ADR-0044-v4-stage-merge-wave3-hard-removal.md)
- [ADR-0047: rdd-quick bypass](docs/adr/ADR-0047-rdd-quick-bypass-path.md)
- [AGENTS.md](AGENTS.md) §关键约定
- [README.md](README.md) §v4.0+ 当前架构
```

## 影响

- **正向**：推荐器 `guide` 不再让 AI 误调已删 skill，新用户按 onboarding 不再 404
- **正向**：12 个 SKILL.md 描述与代码一致，AI agent 不会读到过时信息而走错流程
- **风险**：`rdd-verifier/SKILL.md` L88/101 等处混有 backwards-compat note 与 stale text，需小心区分（用 grep pattern 限制只改 active `skill_use` + 路由说明，保留合法 `evolved-from:` frontmatter）
- **兼容性**：纯文档变更，无代码改动，无破坏性变更

## 验收

- [ ] **AC-1**: `grep -nE 'skill_use\("(guide-arch|guide-design|guide-plan|guide-ship|guide-spec)"\)' skills/guide/SKILL.md` 返回 0 hits
- [ ] **AC-2**: `grep -nE 'skill_use\("guide-' skills/execute/SKILL.md skills/status/SKILL.md skills/deps/SKILL.md skills/add-improve/SKILL.md skills/feature/SKILL.md skills/sync-hub/SKILL.md skills/rddf-session/SKILL.md skills/openspec-gate/SKILL.md skills/rdd-env-check/SKILL.md skills/rdd-verifier/SKILL.md` 返回 0 hits（除合法 backwards-compat 注释）
- [ ] **AC-3**: `docs/migration/v3-to-v4.md` 文件存在，行数 ≥ 80，含 5 个 H2 段（阶段数变化 / Skill 重命名 / Removed skills / 工作流变更 / 升级步骤）+ FAQ + 参考
- [ ] **AC-4**: `README.md` L13-19 npm install 段不含 `v1.x` 或 `v2.0-beta`，标注 `latest stable = v4.0.0`
- [ ] **AC-5**: `tests/integration/test_v4_doc_drift_contracts.bats` 新增 Test 16-19（4 个新 test case），共 19 个测试全 PASS
- [ ] **AC-6**: pre-patch-fail verification：stash 12 个文件 + 运行 bats → Test 16/17/18/19 全部 FAIL → unstash
- [ ] **AC-7**: `./test.sh --full --regression` 不引入新失败（与 `KNOWN_FAILURES.txt` baseline 对比）
- [ ] **AC-8**: `bash skills/rdd-doctor/scripts/doctor.sh` 不新增 CRITICAL（CRITICAL 当前 6 个，本提案完成后应 ≤ 6）

## 后续 (follow-up)

- 代码 docstring 清理（`_lib/gate.py` / `_lib/review_debt_checker.py` / `_lib/close_issues.py` / `_lib/cleanup_plan_handoff.py` / `_lib/post_archive_cleanup.sh` 中 `guide-ship/scripts/ship_*.sh` 路径）— 独立提案 `code-docstring-cleanup-v4-rename`
- USAGE.md 14 处 prose guide-* 提及清理 — 已在 `docs-v4-sync-followup-v2` 跟踪
- pre-commit hook: 检测新文件含 `skill_use("guide-` 立即报错 — 防御未来 drift

## 与其他 proposal 的关系

- **依赖（必须先归档）**:
  - `fix-doc-drift-v4-architecture` (f4d675b, 已 archived) — 提供 test_v4_doc_drift_contracts.bats 基础结构
  - `docs-v4-sync-followup-v2` (Oracle-approved, 待归档) — 提供 ONBOARDING/INSTALL 等文件的更新基础，本提案在其上继续
- **不与以下重复**:
  - `sync-agents-md-five-stage.md` (P1, 2026-08-28) — 覆盖 AGENTS.md 阶段表，本提案不碰 AGENTS.md
  - `changelog-usage-sync.md` (P1, 2026-08-28) — 覆盖 USAGE.md 版本 banner 自动化，本提案只修 README install 段
  - `update-agents-module-map.md` — 覆盖 AGENTS.md 模块图，与本提案不冲突
- **feature fragment 归属**:
  - 建议追加为 `feat-fix-archive-gaps-v2` 的 `phase-4` 段（该 feature 当前 phase_refs = phase-1/2/3，phase-3 实施完成后留 slot 给本文档修复）
  - 或者新建 `feat-fix-doc-drift-wave3.md`（更准确体现"doc drift 第 3 波"语义）
