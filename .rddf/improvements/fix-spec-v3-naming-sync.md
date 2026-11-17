---
优先级: P2
priority: P2
来源: 2026-11-17 文档审查 P1-7 —— 从 fix-doc-drift-residual 拆出：它需要 spec delta，
  与其余 tech-debt 项的交付形态不同
阶段: phase-2
分类: spec-drift
类型: spec-drift
状态: draft

生成时间: 2026-11-17
roadmap_ref:
---

# fix-spec-v3-naming-sync

**主题**: 规范与现实一致

> **立项理由（为什么单独一条）**：本项要改 `openspec/specs/**`（能力 spec），产生 **spec delta**；
> 而 `fix-doc-drift-residual` 的其余五项是文档/守卫直改、不产生 delta。混在一条 change 里，
> archive gate 无法判定「这条 change 到底该不该有 spec delta」。拆开后两者各自可归档。

## 架构依据

### 现状（2026-11-17 实测）

`openspec/specs/skill-role-model/spec.md` 仍用 v3 命名，8 处：

| 位置 | 内容 | 与 v4 的矛盾 |
|---|---|---|
| `:10` | 「The 4 `guide-*` SKILL.md files (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`)」 | v4 的 4 个阶段 skill 是 `rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier` |
| `:15`, `:22` | `WHEN skill_use("guide-arch") (or any phase skill)` | 同上 |
| `:133-135` | `Scenario: guide-arch owns ADR + roadmap` / `GIVEN the guide-arch SKI…` | **与 ADR-0048 直接矛盾**：rdd-arch 已完全脱离 roadmap，roadmap 由 rdd-planner 独占 |

`guide-*` 在 v4.0 已被**硬删除**（ADR-0044）。所以这份 spec 描述的是**已经不存在的 skill**，
而且其中一个 Scenario 断言了一个被 ADR-0048 推翻的归属关系。

### 为什么它没被现有守卫发现

`test_v4_doc_drift_contracts.bats` 的 guide-* 守卫扫的是 `skills/**` 与 `docs/architecture/**`
（本轮实测：扩到 `openspec/specs/` 会命中 48 份文件 / 223 处）。所以这份 spec 的 8 处
**从未被任何断言扫到** —— 它漂了整整一个主版本（v3 → v4）。

### 为什么范围只限 `skill-role-model`

`openspec/specs/` 下 guide-* 共 48 处分布在 48 份 capability spec 里。全改等于重写 48 个 capability
的 spec delta —— 与本项的真实诉求（「本仓角色模型的规范描述与现实一致」）不成比例。
其余 47 份属历史 change 的 spec 快照，它们的 guide-* 是**当时正确**的记录，不改。

判据：`skill-role-model` 是**活规范**（它约束当前 SKILL.md 的 frontmatter），其余是**历史快照**。
只有活规范的过期才是缺陷。

## 范围

**In Scope**：
- `openspec/specs/skill-role-model/spec.md` 的 v3 → v4 命名同步（8 处）
- 该 spec 的 `Scenario: guide-arch owns ADR + roadmap` 按 ADR-0048 重写
- 守卫：把 guide-* 检查扩到「活规范」清单（当前只有 `skill-role-model`，清单显式化以便未来扩）

**Out of Scope**：
- `openspec/specs/` 下其余 47 份 capability spec（历史快照，guide-* 是当时正确记录）
- `skills/**` / `docs/**` 的 guide-*（已由 `fix-doc-drift-residual` 覆盖）
- 修改 `rdd-arch` 的 owns 或任何 SKILL.md frontmatter（本项只改规范文本）

## Why

活规范描述不存在的 skill，是本仓最贵的一类漂移：读者按 spec grep `guide-arch` 会 0 命中
（因为 skill 已删），于是要么以为 spec 作废、要么以为 skill 丢了。而其中那条 Scenario
断言 `guide-arch owns ADR + roadmap` 更是**直接与 ADR-0048 的已签批决策相反**——
规范与决策互相矛盾时，读者无法判断以谁为准。

## What Changes

1. `:10` 的「4 个 `guide-*`」→ v4 四个阶段 skill（`rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier`），
   并注明 `rdd-quick` 是旁路（不计入 4 阶段）。
2. `:15` / `:22` 的 `skill_use("guide-arch")` → `skill_use("rdd-arch")`。
3. `:133-135` 的 `Scenario: guide-arch owns ADR + roadmap` 重写为
   **`Scenario: rdd-arch owns ADR + theme doc（不含 roadmap）`** —— 按 ADR-0048：
   rdd-arch 的 owns 是 `docs/adr/ADR-*.md` + `docs/architecture/*.md` + `.rddf/state/.arch-handoff.json`；
   roadmap 归 `rdd-planner`。
4. 守卫：`test_v4_doc_drift_contracts.bats` 增加「活规范清单」检查 ——
   对 `openspec/specs/skill-role-model/spec.md` 断言 guide-* 零命中；
   清单以变量形式写在测试顶部，注明「新增活规范时追加，历史快照不追加」。

## Acceptance

- [ ] `grep -c "guide-arch\|guide-design\|guide-plan\|guide-ship" openspec/specs/skill-role-model/spec.md` = 0
- [ ] `grep -n "rdd-quick" openspec/specs/skill-role-model/spec.md` 至少 1 处，且明确它是旁路（不计入 4 阶段）
- [ ] `grep -c "owns ADR + roadmap" openspec/specs/skill-role-model/spec.md` = 0；且新 Scenario 标题含 `owns ADR` 且**不含** `roadmap`
- [ ] 新 Scenario 的 Given/When/Then 与 `skills/rdd-arch/SKILL.md` 的 `role.boundaries.owns` 一致（三项提到即可，逐字相等无要求）
- [ ] `openspec validate skill-role-model --strict` 通过（若 CLI 可用；不可用则记录并用手工逐段核对替代）
- [ ] 守卫：「活规范清单」内的文件 guide-* 零命中；变异验证：往该 spec 加一处 `guide-arch` ⇒ 红
- [ ] **不误伤历史快照**：`grep -rc "guide-arch" openspec/specs/ --include=*.md | grep -v skill-role-model` 的非零命中保持不变（本项不改它们），且守卫不把它们算成失败
- [ ] `git diff --stat openspec/specs/` 只含 `skill-role-model/spec.md`
- [ ] 本项产生 spec delta：`openspec/changes/<name>/specs/skill-role-model/spec.md` 存在且与主 spec 的改动一致

## Capabilities

- 读者：`skill-role-model` spec 可以直接按 v4 命名 grep 到对应 skill
- 作者：新增 skill 时，角色模型的规范描述不再是「4 个 guide-*」，无需自行翻译
- 维护者：活规范清单显式化，未来新增活规范时知道要把它加进守卫

## Impact

- **受影响文件**：`openspec/specs/skill-role-model/spec.md`（8 处 + 1 个 Scenario 重写）、`tests/integration/test_v4_doc_drift_contracts.bats`（活规范清单守卫）
- **回归风险**：低 —— 只改一份 spec 的措辞与一个 Scenario；风险在「改错归属」（须对照 ADR-0048）
- **前置依赖**：`ADR-0048`（rdd-arch 脱离 roadmap）是重写 Scenario 的依据；`ADR-0043/0044`（v4 阶段与 guide-* 硬删除）
- **估算**：~1 小时

## 审稿记录

**metis 第 1 轮（2026-11-17，作为 `fix-doc-drift-residual` 的一部分受审）**：

| finding | 处置 |
|---|---|
| 「P1-7 需要 spec delta，与其余 10 条 AC 生命周期不同，混在一起会永远 archive 不干净」 | ✅ **采纳** → 本项从 `fix-doc-drift-residual` 拆出，成为独立 improvement |
| 「AC『`openspec/specs/` 全目录 guide-* 零命中』实测 223 处 / 48 份，与『P1-7 需一条 spec delta』差两个数量级」 | ✅ **采纳（实测 48 份确认）**：本项范围只限 `skill-role-model`，并在 Out of Scope 写明「其余 47 份是历史快照，其 guide-* 是当时正确记录」 |
| 「`Scenario: guide-arch owns ADR + roadmap` 与 v4 矛盾（ADR-0048）」 | ✅ 采纳：What Changes #3 按 ADR-0048 重写该 Scenario，并写明新 owns 的 3 项 |
