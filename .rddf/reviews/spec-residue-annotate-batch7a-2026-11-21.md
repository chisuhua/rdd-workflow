# spec 残留处置台账 — Phase 1 第七批（7a，2026-11-21）

> 定位：change `annotate-spec-residue-dead-blocks-batch7a`。**整块已死**的 Requirement ⇒
> `RETIRED` 注记 + `allow=history` 标注，**零原文改动**。
> **9 块 / 11 行 / 3 份**。批 7 拆 7a / 7b（7b 含局部改写与 rewrite）。
> `line` 列是**改前**行号。

## 1. 逐行处置

| file | line | requirement | disposition | code | 证据 |
|---|---|---|---|---|---|
| `openspec/specs/roadmap-proposal-guidance/spec.md` | 69 | guide-design preflight 显示 roadmap 主题覆盖率 | ANNOTATE（注记 ①） | `history` | `skills/rdd-planner/SKILL.md` 的阶段标题只有 `## Phase 0: roadmap-bootstrap`（:78）与 `## Phase Exit`（:264），无 preflight 阶段；全文无「主题覆盖率」判据 |
| 同上 | 71 | 同上（正文） | ANNOTATE | `history` | 同上 |
| 同上 | 103 | guide-design Phase 2 菜单新增按主题创建选项 | ANNOTATE（注记 ②） | `history` | 菜单交互无对应物；能力**已迁移**到 `add-improve` from-roadmap 模式（`skills/add-improve/SKILL.md:177-187` + `scripts/from_roadmap.py`） |
| 同上 | 105 | 同上（正文） | ANNOTATE | `history` | 同上 |
| `openspec/specs/roadmap-incremental/spec.md` | 8 | arch-done-roadmap-sync | ANNOTATE（注记 ③） | `history` | `skills/rdd-arch/SKILL.md:553`「原 Phase X Roadmap Sync 已完全删除，不再调用 `roadmap_incremental_update.sh`」；该脚本不存在；增量能力现由 `rdd-planner` Phase 0 roadmap-bootstrap 承担 |
| 同上 | 11 | 同上（Scenario） | ANNOTATE | `history` | 同上 |
| 同上 | 132 | thin-wrapper-standalone-skill | ANNOTATE（注记 ④） | `history` | `skills/populate-roadmap-from-arch/` 目录不存在；入口 `roadmap_incremental_update.sh` 与 `scripts/populate.sh` 均不存在；等价能力由 `rddf roadmap` CLI 提供（`_lib/cli/roadmap_cmd.py:90`） |
| 同上 | 137 | 同上（Scenario） | ANNOTATE | `history` | 同上 |
| `openspec/specs/openspec-version-degradation/spec.md` | 8 | CLI 版本检测与降级 | ANNOTATE（注记 ⑤） | `history` | `OPENSPEC_DAG_AVAILABLE` 在 `_lib/` / `skills/` / `.github/` 全仓 0 命中；承载它的 `plan_intake.sh` 不存在 |
| 同上 | 13 | 同上（Scenario） | ANNOTATE | `history` | 同上 |
| 同上 | 19 | 同上（Scenario） | ANNOTATE | `history` | 同上 |

**合计 9 块 / 11 行 / 3 份**（`allow=history` × 11，`RETIRED` 注记 × 5）。

## 2. 注记形态（本批确立为首选）

```
<命中行>
<!-- v4-residue:allow=history -->
> **已退役（2026-11-21）**：<该 Requirement 专属的退役说明 + 依据>
```

- 标注**紧跟命中行**（独占一行）⇒ 豁免该行；
- 注记**只在该 Requirement 的第一个命中行后插一次**（批 5 的「同一块重复插注记」教训）；
- 注记文本**不含退役名** ⇒ 自身不命中、不需二次标注。

**与批 5 先例的两形态对比**：

| 形态 | NOTE 含退役名？ | 标注位置 | 采用者 |
|---|---|---|---|
| 批 5 先例（`complete-project-yaml-config-gaps:203`） | 是 | NOTE **之后**（NOTE 自我豁免） | 历史形态 |
| **本批** | **否** | **命中行之后** | ✅ **首选** |

本批形态更优：allow 落在被豁免的命中行正下方，NOTE 不含旧名因而不需要「自我介绍后再自我豁免」的绕圈；
且**追溯性不丢** —— 零原文改动保留了含旧名的命中行原文，读者 grep 旧名仍命中原文。

## 3. 范围两次收缩（本批最重要的判断）

### 收缩一（critic 第 1 轮）：`plan-done-quality-gate` 移出

我原判「整块已死」。critic 取证否掉：`run_plan_checks`（`skills/propose/scripts/propose_quality_check.py:234-243`）
的函数体就是 `return run_all_checks(...)`；`run_all_checks` 被 `_lib/gate.py:39` 导入，并在
**v4 plan_done 门注册表**（`:388-394`）中以 `propose_quality_checks` 检查项**活跃注册**
（默认 warning 级、`STRICT_PROPOSE_GATE` 升级），`tests/unit/test_gate.py:295` 有活断言
⇒ 它是「**已注册未接线**」，不是「已死」⇒ 归 7b（改指形态）。

### 收缩二（critic 第 2 轮）：`spec-validation-gates` 整份移出

我原判「整块已死（漏网）」，NOTE 里写两个校验器「**无生产调用方**」。critic 取证否掉：
`.github/workflows/test.yml:113-127` 的 CI job「Spec validation gate (baseline + delta targets)」
对**每个** active change 跑 `skills/propose/scripts/validate_baseline.py` +
`skills/_lib/validate_delta_targets.py`，任一失败 ⇒ `exit 1`（阻断）；`skills/propose/SKILL.md:552-558`
的活 bash 流程也对每个新 change 调 `validate_baseline.py`。

⇒ 该 Requirement 的**核心判据（对每个 active change 跑两个校验器、失败即阻断）今天仍为真**，
只是 actor 从 v3 plan-done 门换成 CI 的 spec validation gate ⇒ **属改指，不是注记** ⇒ 整份 3 块 / 4 行移出。

## 4. 三轮 critic 的共同教训（写进 7b 的前置纪律）

| 轮 | 我的错误断言 | critic 如何否掉 |
|---|---|---|
| 1 | 「轻量模式判定在 `_lib/ship_execution_mode.sh:97`」 | 那是 **WAVE 串并行**判定，注释明写「it says nothing about the execution mode」；轻量模式判定是 `_lib/builder_deps.py::decide_execution_mode` |
| 2 | 「`validate_baseline.py` 不存在」 | 只查了 `_lib/` 根目录 ⇒ 实际在 `skills/propose/scripts/` |
| 3 | 「两者文件仍在却**无生产调用方**」 | 只 grep 了 `*.py` / `*.sh` ⇒ **漏了 CI 的 `.github/workflows/*.yml` 与 `skills/*/SKILL.md` 里的 bash 流程** |

⇒ **纪律**：「落点存在 / 不存在 / 无调用方」这类断言必须**全仓** grep（含 `.yml` / `.yaml` / `.md`），
且必须指到**行为载体**的 `file:line`，不能只凭「路径存在」或「句子形态像」。

## 5. 实测数字

| 指标 | 改前 | 改后 |
|---|---|---|
| 未豁免 | 36 处 / 29 块 / 12 份 | **25 处 / 20 块 / 10 份** |
| 含已豁免 | 319 / 170 / 44 | **319 / 170 / 44（不变）** |
| 已登记豁免 | 283 | **294** |
| `stale` / `invalid` / `ignored` / `fence_rejected` / `in_fence` | 0 / 0 / 0 / 0 / 0 | **0 / 0 / 0 / 0 / 0** |
| `doctor --category v4-residue` | 29 WARNING | **20 WARNING** |
| `openspec validate --all` ERROR | 11 | **11** |
| **零原文改动** | — | ✅ 3 份的原有行逐行相同（只多出 11 标注 + 5 注记） |

### 为什么含已豁免不变（与批 6 相反）

| 处置 | 未豁免 | 含已豁免 | 本批/批 6 |
|---|---|---|---|
| **标注**（`allow`） | −N | **不变**（token 还在，只是被标记） | 本批（−11 / 不变） |
| **改指**（换 token） | −N | **也 −N**（token 真的消失） | 批 6（−6 / −6） |

## 6. ⚠️ 本批顺带发现的既有判据缺口

**`openspec validate` 的文本输出不显示 `requirements[N]` 这类 issue** —— 只有 `--json` 才报。

⇒ 批 3/4/5 的「validate 逐字节相同」判据**没有覆盖** `very long` 增量
（批 5 在 `skills/rdd-doctor/SKILL.md` 记录过这个副作用，但验证口径漏了它）。

本批改用 `--json` 比对 issue 多重集，实测新增 **4 条** `requirements[N]: very long`：

| Requirement | 改前 | 改后 |
|---|---|---|
| roadmap-proposal-guidance[3] guide-design preflight 显示 roadmap 主题覆盖率 | 215 | **543** |
| roadmap-proposal-guidance[4] guide-design Phase 2 菜单新增按主题创建选项 | 107 | **539** |
| roadmap-incremental[0] arch-done-roadmap-sync | 239 | **655** |
| openspec-version-degradation[0] CLI 版本检测与降级 | 333 | **624** |

（`roadmap-incremental[5] thin-wrapper-standalone-skill` = 142 **不变** —— 它的注记落在 **Scenario 区**，
而 `extractRequirementBody` 遇第一个 header 即 break ⇒ Scenario 不计入 Requirement 正文长度。）

## 7. 记 tail（范围外）

1. **批 7b（21 行 / 9 份）** —— `annotate` 14 / **改指** 6 / `rewrite` 1
   （`state-management:65+72-75` 是 rewrite 唯一候选；`plan-done-quality-gate` 2 块与
   `spec-validation-gates` 3 块是改指形态）。⚠️ **动手前必须重新全仓核实每行的「已死 / 仍活」断言**。
2. **`general/spec.md`（4 行 / 2 块）** —— 测试锁定 + 断言漂移，三方联动专项。
3. **`openspec validate` 判据缺口** —— 把 `test_*.py` / 验收流程里的 validate 比对从「文本输出」
   改为「`--json` 的 issue 多重集」；并复核批 3/4/5 是否已悄悄新增 very long。
4. **delta 形态垃圾结构** / **围栏示例与 schema 脱节** —— 各自专项。
5. `_lib/cross_repo_gate.py:5` 的陈旧注释（提到已不存在的 `plan_done_gate.sh`）—— backlog。

## 8. 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | REJECT（2 BLOCKER + 3 SF） | BLOCKER-1 `plan-done-quality-gate` 移出；BLOCKER-2 NOTE 全文进 proposal + 措辞区分「不存在」/「无调用方」 |
| critic 第 2 轮（复审） | REJECT（1 新 BLOCKER + 1 SF） | B-NEW：CI 在调两个校验器 ⇒ `spec-validation-gates` 整份移出；SF 「7 条 NOTE」旧数已改 5 条 |
| critic 第 3 轮（复审，用户批准） | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 1 SF + 1 NIT） | SF：tasks T0.6 残留已证伪的取证断言 ⇒ 已删；NIT：proposal AC-3「4 份」⇒ 已改 3 份 |

## 9. 回滚

- 台账 / 测试：`git revert <sha>`（tracked）。
- spec 改动：`openspec/` gitignored ⇒ 回滚凭据 = `/tmp/opencode/specs-b7a-before/`（3 份改前快照）
  + `/tmp/opencode/specs-backup-b7a-<ts>/`（165 份整树）+ T0 的 18 组 validate 输出。
