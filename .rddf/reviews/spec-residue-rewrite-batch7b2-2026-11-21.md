# spec 残留处置台账 — Phase 1 第七批（7b-2，2026-11-21）

> 定位：change `rewrite-spec-residue-batch7b2`。
> **12 行 / 4 份** —— 判据核心仍为真（或需纠正），但机制形态已变 ⇒ **改写**判据正文 + Scenario。
> **本批必然改原文**（与 7b-1 的「零原文改动」不同）。

## 1. 逐行处置

### A. `skeleton-planning` / `planned-status-lifecycle`

| 行 | 改前 | 改后 | 依据 |
|---|---|---|---|
| 11 | `...SHALL be: planned → proposed → in_worktree → completed → archived. A change in planned status SHALL NOT be eligible for guide-ship execution.` | `...SHALL be: planned → proposed → in_worktree → review → completed → archived. A change in planned status SHALL NOT be classified executable.` | `_lib/iteration/schema.py:41` 枚举含 `review`；`_lib/discover_ship_changes.py:212-213` 的分类口径 |
| 22 | `#### Scenario: Skeleton change excluded from guide-ship` | `#### Scenario: Skeleton change not classified as executable` | 同上 |
| 23 | `- **WHEN** guide-ship scans active changes` | `- **WHEN** ship-candidate discovery scans active changes` | `_lib/discover_ship_changes.py::discover` |
| **24**（配套） | `- **THEN** changes with planned status SHALL NOT appear in the execution candidate list` | `- **THEN** changes without design.md SHALL NOT be flagged executable` | critic BLOCKER-1：分类由**工件完整性**驱动（`:89` `artifact_complete = proposal and design`） |
| **25**（配套） | `- **AND** only proposed status changes are eligible for worktree creation` | `- **AND** only artifact-complete changes (proposal.md + design.md, _lib/discover_ship_changes.py) are eligible for worktree creation` | critic BLOCKER-1：原句**为假**（`proposed` 但工件不全 ⇒ `needs_planning`，不 eligible） |

### B. `spec-validation-gates` / CI spec-validation gate

| 行 | 改前 | 改后 | 依据 |
|---|---|---|---|
| 149 | `### Requirement: guide-plan.md plan-done gate MUST validate all active changes` | `### Requirement: CI spec-validation gate MUST validate all active changes` | `.github/workflows/test.yml:113-127` |
| 151 | `The Phase 4 plan-done gate in skills/guide-plan.md MUST invoke both` | `The CI spec-validation gate (.github/workflows/test.yml) MUST invoke both` | 同上 |
| **153**（配套） | `before writing .rddf/state/.plan-handoff.json. If ANY change fails validation,` | `If ANY change fails validation,` | 该文件在 v4 **无 writer** |
| **154**（配套） | `the gate MUST block plan-done and exit 1.` | `the gate MUST exit 1.` | 同上 |
| 156 | `#### Scenario: plan-done gate blocks when one change fails validation` | `#### Scenario: gate blocks when one change fails validation` | — |
| 158 | `- **WHEN** guide-plan reaches Phase 4 plan-done` | `- **WHEN** the CI spec-validation gate runs` | — |
| **162**（配套删除） | `- **AND** .rddf/state/.plan-handoff.json MUST NOT be written` | **删除** | 假判据 |
| 165 | `#### Scenario: plan-done gate proceeds when all changes pass validation` | `#### Scenario: gate proceeds when all changes pass validation` | — |
| 167 | `- **WHEN** guide-plan reaches Phase 4 plan-done` | `- **WHEN** the CI spec-validation gate runs` | — |
| **169**（配套删除） | `- **THEN** the gate MUST write .rddf/state/.plan-handoff.json` | **删除**（与 `exit 0` 合并为 `THEN the gate MUST exit 0`） | critic BLOCKER-2：CI 从不写 plan-handoff |

⚠️ **只提 CI 不提 propose 流程**是刻意的：`skills/propose/SKILL.md:552-558` 只对**新建的** change 跑、
且只跑 `validate_baseline.py`（无 delta targets）、还是半实现伪代码（`:562` TODO 自述）⇒
满足「**all** active changes × 双校验器 × exit 1」的只有 CI 的 job。

### C. `state-management` / `iteration-json-planned-status`

| 行 | 改前 | 改后 | 依据 |
|---|---|---|---|
| 65 | `The status SHALL be set by propose (--skeleton mode) and SHALL be transitioned to proposed by guide-plan fill phase.` | `The status SHALL be set by propose (--skeleton mode), and SHALL be transitioned to proposed when the change is approved at rdd-builder P0 (skills/rdd-builder/scripts/phase0_approval.sh).` | `phase0_approval.sh:252` 逐字 `store.set_status(data, name, "proposed")` |
| 73 | `- **WHEN** guide-plan fill successfully creates design.md and tasks.md for a planned change` | `- **WHEN** an approved change is registered by rdd-builder P0 approval` | 同上 |
| **75**（配套删除） | `- **AND** the transition SHALL be recorded in the event log` | **删除** | `_lib/iteration/store.py:677-683` 的 `set_status` → `add_or_update_change`，**无 event log 写入**；`phase0_approval.sh` 全文 0 处 event |

### D. `rfc-rddf-project-yaml-config-i10` / `acceptance-3`（**删除整块**）

删除 L24-31（`### Requirement: acceptance-3` + 其 Scenario，8 行）。

**依据**：判据「`git.openspec_tracked: false` 时强制轻量模式」**被 v4 反证** ——
`_lib/builder_deps.py:42 decide_execution_mode(file_count, task_count, risk_keywords)` **不看** `git.openspec_tracked`；
同主题**正确**判据已存在于 `complete-project-yaml-config-gaps`（「`git.openspec_tracked` SHALL NOT influence the execution mode」）。
整份 spec 是 delta 形态工件（15 个 Requirement 全名 `acceptance-1..15`）⇒ 删掉这一块不破坏其余结构
（实测 `openspec validate` 仍 valid）。

## 2. 实测数字

| 指标 | 改前 | 改后 |
|---|---|---|
| 未豁免 | 16 处 / 11 块 / 5 份 | **4 处 / 2 块 / 1 份**（只剩 `general/spec.md`） |
| 含已豁免 | 319 / 170 / 44 | **307 / 161 / 42** |
| 已登记豁免 | 303 | **303（不变）** |
| `stale` / `invalid` / `in_fence` / `fence_rejected` | 0 / 0 / 0 / 0 | **0 / 0 / 0 / 0** |
| `openspec validate --all --json` 的 issue 多重集 | 224 条 | **224 条（新增 0 / 消失 0）** |
| `very long` | 62 条 | **62 条（未新增）** |
| `validate --all` ERROR | 11 | **11** |
| `doctor --category v4-residue` | 11 WARNING | **2 WARNING** |

⚠️ **含已豁免的 −12 处 / −9 块 / −2 份**：rewrite 与删除都让 token **真的消失**
（与 7b-1 的「标注 ⇒ 含已豁免不变」不同）。
−9 块 = A 2 + B 3 + C 2 + D 2；−2 份 = `rfc-rddf`（删掉唯一命中）+ 另一份完全退出。

⚠️ **A 组改后反而短了 1 字符**（459 → **458**）⇒ 不跨 500（critic 的焦点 3 担忧已解除）。

## 3. 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **REJECT**（2 BLOCKER + 2 SF + 1 NIT） | **BLOCKER-1**（A 组 L24-25 与分类机制矛盾 + 两套坐标系）⇒ 已同步改写 L24-25 为 artifact 口径、L11 尾巴缩成 `classified executable`。**BLOCKER-2**（B 组 L169 plan-handoff 残留）⇒ 已删。**SF-1**（`lib/` → `_lib/`）⇒ 已改。**SF-2**（A 会跨 500）⇒ 短措辞，实测 458。**NIT**（常数以实测为准）⇒ 已回填 4/2/1 + 307/161/42。 |

⚠️ critic 的**通过项**：C 组（删 event log 正确）、D 组（删除 vs 注记的取舍成立）、
焦点 2（块数算术）、焦点 4（C 组自洽）。

## 4. Phase 1 状态

**Phase 1 只剩 `general/spec.md` 的 4 行 / 2 块**（测试锁定 + 断言漂移，三方联动专项）。

## 5. 记 tail（范围外）

1. **`general/spec.md`（4 行 / 2 块）** —— `:145-146` 被 `tests/unit/test_doc_contracts.py:67-68` 的子串断言锁定
   （必须含 `guide-arch` / `guide-plan`）；`:127-128` 对 ADR-0001 的断言已漂移 ⇒ 需「改测试 → 改文档 → 改 spec」三方联动。
2. **`rfc-rddf` 的其余 14 个 `acceptance-N`** —— delta 形态垃圾结构专项。
3. 既有 62 条 `very long` —— 接受并冻结（`fix-spec-very-long-verification-gap` 的守卫阻止新增）。

## 6. 回滚

- 台账 / 测试：`git revert <sha>`（tracked）。
- spec 改动：`openspec/` gitignored ⇒ 回滚凭据 = `/tmp/opencode/specs-b7b2-before/`（4 份改前快照）
  + `/tmp/opencode/specs-backup-b7b2-<ts>/`（165 份整树）。
