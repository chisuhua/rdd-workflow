# fix-spec-v3-naming-sync Implementation Plan (P0-1)

> **For agentic workers:** Implement this plan task-by-task, following the TDD 5-step structure below. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让活规范 `openspec/specs/skill-role-model/spec.md` 里 rdd-arch 的 owns 陈述与 `skills/rdd-arch/SKILL.md`
及 `ADR-0048` 决策 1c **三方一致**，并补上第一道能发现这类漂移的**归属断言**。

**Architecture:** 三处改动 ——
① **spec delta**（`openspec/changes/fix-spec-v3-naming-sync/specs/skill-role-model/spec.md`）：`## MODIFIED Requirements`；
② **主 spec**（`openspec/specs/skill-role-model/spec.md`）：把同一段改过来（归档时 delta 再应用一次 ⇒ 幂等）；
③ **守卫**（`tests/integration/test_v4_doc_drift_contracts.bats`）：「活规范清单」+ 归属断言。

> ⚠️ **本项不做**：不删 `:15` / `:23` 的 `guide-arch` 改名历史注记（它们带 `<!-- v4-residue:allow=rename-history -->`
> 合法豁免，doctor `v4-residue` 显式放行）；不做 guide-* 零命中断言；不改任何 SKILL.md 的 owns（实现已正确）。

**Tech Stack:** Markdown（spec + delta）、bats（守卫）、openspec CLI（validate）。

---

## File Structure

### Production Code (MODIFY)

| File | Responsibility |
|---|---|
| `openspec/specs/skill-role-model/spec.md` | `Requirement: skill-role-boundaries-accurate` 段的 Scenario 标题 + THEN 断言（**2 行**） |

### Delta (CREATE)

| File | Responsibility |
|---|---|
| `openspec/changes/fix-spec-v3-naming-sync/specs/skill-role-model/spec.md` | `## MODIFIED Requirements` —— 归档时由 `openspec archive` 应用到主 spec |

### Tests (MODIFY)

| File | Responsibility |
|---|---|
| `tests/integration/test_v4_doc_drift_contracts.bats` | 新增「活规范归属断言」检查（清单 + 断言 + 变异验证） |

---

## Pre-flight

- [ ] **Step 0.1: 记录当前基线事实（供改后对照）**

```bash
S=openspec/specs/skill-role-model/spec.md
grep -c 'owns ADR + roadmap' $S
grep -c 'roadmap.md' $S
grep -c 'guide-arch\|guide-design\|guide-plan\|guide-ship' $S
```

Expected（2026-11-24 实测）: `owns ADR + roadmap` = **1**；`roadmap.md` = **1**；guide-* = **2**
（两处都在 `<!-- v4-residue:allow=rename-history -->` 标注的下一行 ⇒ 合法豁免，**不得删**）。

- [ ] **Step 0.2: 核对三方权威来源（改写依据）**

```bash
grep -n 'owns:' -A 4 skills/rdd-arch/SKILL.md
grep -n 'roadmap.md' skills/rdd-arch/SKILL.md
grep -n '决策 1c' -A 6 docs/adr/ADR-0048-v4-stage-merge-revision.md
```

Expected: `owns:` = `docs/adr/ADR-*.md` + `docs/architecture/*.md` + `.rddf/state/.arch-handoff.json`；
`roadmap.md` 出现在 **`not_owns:`**；ADR-0048 决策 1c 明写「`role.boundaries.owns` 移除 roadmap 相关」。

---

### Task 1: 写 spec delta（MODIFIED Requirements）

- [ ] **Step 1.1: 写 delta**

`openspec/changes/fix-spec-v3-naming-sync/specs/skill-role-model/spec.md`：

```markdown
# skill-role-model Specification Delta

## MODIFIED Requirements

### Requirement: skill-role-boundaries-accurate

<Requirement 正文 —— 与主 spec 改后逐字一致>

#### Scenario: rdd-arch owns ADR + theme doc

- GIVEN the `rdd-arch` SKILL.md
- WHEN checking `role.boundaries.owns`
- THEN it contains `docs/adr/ADR-*.md`, `docs/architecture/*.md` and `.rddf/state/.arch-handoff.json`
```

> ⚠️ **delta 的 Requirement 名必须与主 spec 的完全一致**（`skill-role-boundaries-accurate`），
> 否则 `openspec archive` 认不出要改哪一条 Requirement。
>
> ⚠️ **delta 正文用 `- GIVEN/- WHEN/- THEN`（连字符）**，与主 spec 现有写法一致。

---

### Task 2: 改主 spec（与 delta 逐字一致）

- [ ] **Step 2.1: 改 Scenario 标题**

`:135` `#### Scenario: rdd-arch owns ADR + roadmap` → `#### Scenario: rdd-arch owns ADR + theme doc`

- [ ] **Step 2.2: 改 THEN 断言**

`:139` `- THEN it contains \`docs/adr/ADR-*.md\` and \`roadmap.md\` (matching the existing "职责边界" section)`
→ `- THEN it contains \`docs/adr/ADR-*.md\`, \`docs/architecture/*.md\` and \`.rddf/state/.arch-handoff.json\` (matching the existing "职责边界" section)`

- [ ] **Step 2.3: 逐字核对**

```bash
diff <(sed -n '/^### Requirement: skill-role-boundaries-accurate/,/^### Requirement: skill-role-human/p' openspec/specs/skill-role-model/spec.md) \
     <(sed -n '/^### Requirement: skill-role-boundaries-accurate/,/^### Requirement: skill-role-human/p' openspec/changes/fix-spec-v3-naming-sync/specs/skill-role-model/spec.md)
```

Expected: 无差异（delta 与主 spec 该段逐字一致）。

---

### Task 3: 守卫（活规范归属断言）

- [ ] **Step 3.1: 在测试顶部维护「活规范清单」**

```bash
ACTIVE_ROLE_SPECS=(
  openspec/specs/skill-role-model/spec.md
)
```

注释须写明：**新增活规范时追加，历史快照不追加**（历史快照的 guide-* 是当时正确的记录）。

- [ ] **Step 3.2: 新增断言**

对清单内每份 spec：
- 不得出现把 roadmap 归给 rdd-arch 的表述（Scenario 标题或 owns 断言里出现 `roadmap` 即红）；
- rdd-arch 的 owns 断言里的 3 项必须与 `skills/rdd-arch/SKILL.md` 的 `owns:` **逐项一致**（正向断言 ⇒ 漂移立刻红）。

> ⚠️ **不做 guide-* 零命中断言** —— 清单内 spec 允许带 `<!-- v4-residue:allow=rename-history -->` 的改名历史注记；
> 本守卫与 doctor `v4-residue` **不抢判据**（前者查归属、后者查豁免标注）。

- [ ] **Step 3.3: 变异验证**

往 Scenario 标题加回 `+ roadmap` ⇒ 守卫必须红；改回 ⇒ 必须绿。

- [ ] **Step 3.4: 跑该 bats 文件**

```bash
bats tests/integration/test_v4_doc_drift_contracts.bats
```

---

### Task 4: 收口验证

- [ ] **Step 4.1: `openspec validate --all`** ⇒ 0 ERROR（含新增 delta）
- [ ] **Step 4.2: `rddf doctor --category v4-residue`** ⇒ 对该 spec 无新增 finding（豁免标注未被破坏）
- [ ] **Step 4.3: 逐条勾回 `proposal.md` 的 10 条 AC**
- [ ] **Step 4.4: 全量回归门** `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression`
- [ ] **Step 4.5: 归档** `bash skills/rdd-builder/scripts/phase3_archive.sh fix-spec-v3-naming-sync`

---

## 回滚

还原主 spec 的 2 行 + 删除 delta + 移除新增守卫。纯文档，无状态文件、无代码路径。

## 不做（明确排除）

- 删除 `:15` / `:23` 的 `guide-arch` 改名历史注记（合法豁免，doctor `v4-residue` 放行）
- `openspec/specs/` 下其余 47 份 capability spec（历史快照）
- 修改任何 SKILL.md 的 `role.boundaries`（实现已正确，本项只让 spec 追上实现）
- guide-* 零命中断言（会误伤合法豁免）

