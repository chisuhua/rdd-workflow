# 审稿记录 — docs/architecture 漂移同步（2026-11-20）

- **产物**：`docs/architecture/*.md` 9 份主题文档的漂移修正（37 处）
- **角色**：architect
- **审查者**：oracle（`审查域: 其他审查`）
- **判定**：`BLOCK`（5 BLOCKER + 5 SHOULD_FIX + 4 NITS）→ 全部处置后验证通过
- **预算**：oracle 1 轮（architect 行：只同步主题文档 / 改措辞 ⇒ 只 oracle，无需 critic）

## 意图检查点

- **意图陈述**：修 `docs/architecture/**` 里指向已退役对象的**活指令 / 当前态断言 / 计数漂移**；不动历史叙述、不动 `docs/adr/**`、不新建 ADR。
- **歧义判定**：无 ≥2 种合理解读（延续 `fix-v4-doc-drift-live-invocations` 与 `retire-spec-musts-pointing-at-retired-objects` 的同类工作，范围边界已由 ADR-0063 / ADR-0044 界定）⇒ 未调 metis，未问用户。
- **审查域**：非治理面（改的是项目内架构主题文档，非 `~/.config/opencode/**`）。

## oracle 逐条处置

### BLOCKER

| # | oracle finding | 核实 | 处置 |
|---|---|---|---|
| 1 | `improvement-check-mechanisms.md` 改「`rdd-planner` 选项 3」是**假契约** —— `rdd-planner` 无「从 GitHub issue 创建提案」菜单项；活路径是 `add-improve --from-issue` | **证实**：`grep -nE 'issue\|GitHub\|from-issue\|选项 3' skills/rdd-planner/SKILL.md` 只命中 `:269` 的 report-issue 异常出口；`skills/add-improve/scripts/from_issue.sh` 存在，`SKILL.md:177-183` 描述 3 种模式 | 改为「`add-improve --from-issue`（v4 直调；原 `guide-design` 选项 3 入口已随 ADR-0044 移除）」—— 覆盖 `:19` / `:20` / `:128` / `:130` |
| 2 | `multi-session.md:94` 改「`rddf guide`」错 —— 跨窗口观察是 `stage_guide` 职责，已随 ADR-0063 退役；保留消费者是 `rddf monitor` | **证实**：ADR-0063 决策 7「`rddf monitor` 与 `child_progress` 消费保留」+ V-10「`rddf monitor` 输出仍有 `Child Progress` 段」 | 改为「the event bus lets **`rddf monitor`** observe…（`stage_guide` 轮询已随 ADR-0063 退役）」 |
| 3 | `multi-session.md:100-171` 整段「Cross-Container Event Bus」描述已退役架构，漏检 | **证实**：段内含 `stage_guide` / `RDDF_GUIDE_SESSION_ENABLED` / `guide_intent_detected` / `rddf_session_hook_poll_events` | 段首加**退役横幅**（点明 `stage_guide` 架构 2026-11-19 随 ADR-0063 退役；事件总线本体与 `rddf monitor` 保留；后续读作历史设计，不照做） |
| 4 | `improvement-check-mechanisms.md:105` 的 `skills/guide-{arch,plan,design,ship}/scripts/*env_check.sh` 标 ✅ 但路径已硬移除（花括号形态逃逸正则） | **证实**：`ls skills/*/scripts/*env_check*` 只有 `rdd-arch/scripts/arch_env_check.sh` 与 `rdd-env-check/scripts/env_check.sh` | 改为「`skills/rdd-arch/scripts/arch_env_check.sh`（v4 仅 arch 保留 env_check；`guide-{plan,design,ship}` 已随 ADR-0043/0044 合并或移除）」 |
| 5 | `layer-0-progressive-context.md:14` mermaid `skill_use('guide')`（单引号形态逃逸） | **证实** | 改为「推荐入口：rddf guide CLI（ADR-0062）」 |

### SHOULD_FIX

| # | finding | 处置 |
|---|---|---|
| 1 | `v4-pipeline-data-flow.md:648` 我的替换文案「centralized per-skill in each SKILL.md description」与 ADR-0051 D1 及 ADR-0063 D8 冲突 | **采纳**：ADR-0063 决策 8 明说反触发 SSOT 载体迁至「ADR-0062 收敛后的单一推荐实现（`rddf guide` CLI 为其入口）」⇒ 改为该口径，不发明第三个落点 |
| 2 | `multi-session.md:62` 的 `skill_use("rddf-session current")` 也不存在；BINDING_LINES「全仓 0 命中」证据是假的（`docs/legacy/skills/guide/scripts/scan-state.sh` 仍在） | **部分采纳**：改为 `rddf sessions current`（`_lib/cli/sessions_cmd.py:86` 的 `if sub == "current"` 实证）；证据改为「`guide_cmd.py` 不调 `scan_session_binding`（`rddf-cli-completion.md:1503`）+ ADR-0063 D1」。⚠️ oracle 的「rddf-session skill 无 current」基于其 frontmatter（`:4` 写 5 子命令），但 `:34` 明确列了 `current` ⇒ **frontmatter 自身过期**，记 tail |
| 3 | `skills-and-handoff.md:83-88` 是**完全孤儿字段**（3 函数 + `plan_intake.sh` 全灭），判「部分退役」偏轻 | **采纳**：整段改为**过去式 2 行注记**（写清「曾用于…」「三函数与 plan_intake.sh 已随 ADR-0043/0044 移除」「字段仅存于 schema，无活消费者」），删除祈使 bullet |
| 4 | 计数漂移漏检两处：`extension-points.md:7` 与 `skills-and-handoff.md:3` 的「ships 17」 | **采纳**：`extension-points.md:7` → 26；`skills-and-handoff.md:3` → 「26 skills (19 of them `user-invocable: true`)」（实测 `grep -l 'user-invocable: true'` = 19，2 个 false，5 个未声明） |
| 5 | `workflow-phases.md` 漏 2 处同型：`:23` mermaid、`:445` 对照表 | **采纳**：两处均改为 `rddf guide` / `direct invocation` |

### NITS

| # | finding | 处置 |
|---|---|---|
| 1 | `agent-role-alignment.md:133-135` 不动对；`historical-evolution.md` 整份不动对；`improvement-check-mechanisms.md:127` 不动对，但 **`:130` 应随 `:128` 一起改**（现在时描述） | **采纳**：`:130` 已改（`:127` 保留为「原设计 ❌ 未实现」的历史标签） |
| 2 | 三机制诚实声明对；「(none) + 解释」优于硬填错误调用方；应列全集 | **采纳**：表头声明改为三机制；`rdd-workflow-writing-plans` 写「(none — plan file is produced by rdd-builder P1)」；补 `session-lesson-mining` 行（21 个 sub-skill 行 = 全集） |
| 3 | `overview.md:5` 把 `status` 归入「OpenSpec CLI verbs」需验证 | **核实后不动**：`openspec --help` 确有顶层 `status [options]  Display artifact completion status` ⇒ 原说法正确 |
| 4 | 计数口径不统一；`overview.md:138` 的「(formerly `guide-design`)」命中 grep 却未列入「不动」清单 | **采纳**：`overview.md:138` 补入「不动」清单（正确的历史括注）；本文档统一为 **37 处** |

## 实施中修正的判据缺陷

**守卫 `test_v4_doc_drift_contracts.bats:270` 用 `grep -v 'shim\|DEPRECATED\|compat'` 豁免兼容性矩阵的历史提及**。我的新措辞「已移除」不在豁免词内 ⇒ 该守卫变红（基线因原措辞含「shim」「DEPRECATED」而被豁免）。

- **处置**：文档措辞改为「已移除，无 compat shim」（语义不变，落在同一豁免内）。**未改 `tests/**`**（builder 面，architect 越界）。
- **记 tail**：守卫的豁免词表应扩展 `已移除 / retired / hard removal` 等更准确的措辞 —— 归 builder 面。

## 验证结果

| 判据 | 结果 |
|---|---|
| `./test.sh --gates` | **ALL PASSED**（isolation / ruff / mypy strict / rdd-doctor structural 10 类） |
| `bats test_v4_doc_drift_contracts.bats` | **19/19 ok**（含 `:270` 的「ALL docs/architecture/*.md 无活 guide-* 引用」） |
| `bats test_doctor_layout.bats` / `test_arch_discovery_contract.bats` | 全绿 |
| `pytest test_agent_role_alignment_doc.py test_arch_audit_check.py test_doc_contracts.py` | **36 passed** |
| 扩展模式全扫（`guide-\{` / `stage_guide` / `skill_use('guide')` / `ships \d+` / `skills/guide/` / `ac-verifier`） | 剩余命中**全部正当**（历史叙述 / 我的加注 / 退役横幅覆盖 / 正确的新数字） |

## 范围外发现（记 tail，未处理）

1. **`skills/rdd-session/SKILL.md:4` frontmatter 说「5 subcommands: list/show/resume/abandon/archive-history」，但 `:34` 列了 `current` / `progress` / `status`** —— frontmatter 与正文自相矛盾。属 `skills/**` 面（builder 管辖）。
2. **`skills/rdd-verifier/SKILL.md` 仍有 `skill_use("ac-verifier")`** —— `ac-verifier` skill 已于 2026-09-07 删除。属 `skills/**` 面。
3. **守卫豁免词表**（见上「实施中修正的判据缺陷」）—— 属 `tests/**` 面。
