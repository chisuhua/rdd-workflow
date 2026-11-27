# verify: fix-proposal-generator-output-fidelity —— 实现验收

> **验收对象**：本 change 的**实现**（worktree 分支 `openspec/fix-proposal-generator-output-fidelity`，5 个提交）
> **验收时间**：2026-11-27
> **执行角色**：builder（角色内建 verifier 契约 · **本地验收路径**）
> **判据来源**：`proposal.md` 的 `## Acceptance`（AC1–AC15，优先级 1 = 用户「每个改进都要带 TDD 测试」）

## 分流判定（为什么走本地验收，而不是 `rdd-verifier` skill）

| 条件 | 实测 | 判定 |
|---|---|---|
| ① change 存在 + 有 AC 段 | `openspec/changes/fix-proposal-generator-output-fidelity/proposal.md` 含 `## Acceptance`（15 条） | ✅ |
| ② P3 archive gate 触发（`tasks_done == tasks_total > 0`） | 主仓 `iteration.json` 该 change：`tasks_total=33`、**`tasks_done=0`**（P2 准备阶段写入的快照，实现后未刷新）⇒ `_is_eligible` 不满足 | ❌ |
| ③ `rdd-verifier` skill 可加载 | `rdd-skills.sh --json` ⇒ installed | ✅ |

⇒ 条件② 不满足 ⇒ **走本地验收**（并在下方「已知遗留」登记 `tasks_done` 陈旧 = U5 同类缺陷）。

## 逐条判定（AC1–AC15）

| AC | 判据 | 证据（测试文件 / 命令） | 判定 |
|:--:|---|---|:--:|
| AC1 | 纯表格 / 混排 / 带注解标题 / 表内逗号 / Out 段一次 | `tests/unit/test_generate_full_proposal_scope_table.py`（8 例）⇒ **先红**（0 条 / 被切碎）→ 绿；**变异**（表格识别退回只认 bullet）⇒ 3 例红 | ✅ |
| AC2 | 不可解析 ⇒ 保留原文 + stderr，无逗号碎片 | 同上 `test_unparseable_scope_is_preserved_verbatim`（先红 → 绿） | ✅ |
| AC3 | 既有用例零回归 | `test_generate_full_proposal.py` **27/27 通过**；其中 5 例**改写**（旧断言编码了被删除的退化行为，已在文件内注明） | ✅ |
| AC4 | 语料 golden snapshot + 形态标签 + 动态计数 | `test_generate_full_proposal_corpus.py`（2 例）；快照 305 份 / 74KB / 带 `generated_at` + `corpus_count`；**变异**（分类器改坏）⇒ 红；**真实触发**（improvement 正文改动）⇒ 红 → 刷新 → 绿（共 3 次，机制如设计） | ✅ |
| AC5 | 变异腿：退回只认 bullet ⇒ AC1 红 | 见 AC1（实测 3 例红后回滚） | ✅ |
| AC6 | `## 范围` / `## What Changes` 并存 ⇒ 取候选序靠前者 + 歧义告警 | `test_both_sections_present_prefers_range` / `test_only_english_section_present_is_used`（先红 → 绿） | ✅ |
| AC7 | 声明 delta 后：`acceptance-N` / `capability-N` / 恒真 WHEN 三类被拒；**未声明 ⇒ 不生成（不算失败）** | `test_spec_delta_generator_shape.py`（6 例，含 `test_no_delta_declaration_is_skip_not_failure`） | ✅ |
| AC8 | 载体 = 粗体头行（5 字段）⇒ 需求名语义化 + WHEN/THEN 等于作者文本 | `_md()` fixture + `test_wellformed_semantic_requirement_is_accepted` | ✅ |
| AC9 | `**delta**: modified <cap>` ⇒ `## MODIFIED` + `specs/<cap>/` + 逐字保留既有 Scenario + 追加作者场景 | `test_spec_delta_generator_modified.py::test_modified_target_is_emitted`；目标不存在 ⇒ 指名拒绝 | ✅ |
| AC10 | 判据单一真源 | `test_generator_and_guard_share_one_predicate_source`（两侧引用 `_lib/spec_requirement_form.py` 同一正则） | ✅ |
| AC11 | SKILL.md delta 契约三锚点 + 落点目录 | `test_rdd_builder_skill_contract.py`（2 例，先红 → 绿） | ✅ |
| AC12 | 变异腿：形态正则退回 ⇒ AC7 红 | 实测（`_lib/spec_requirement_form.py` 正则退回 ⇒ 2 例红），随后回滚 | ✅ |
| AC13 | 版本**语义化**比较 + `<1.7.0` 分支本地守卫 | `test_version_comparison_is_semantic_not_lexicographic` / `test_legacy_openspec_still_gets_local_guard` / `test_missing_openspec_cli_is_not_fatal`；**变异**（字符串比较）⇒ 红 | ✅ |
| AC14 | delta 拒绝 ⇒ 无空文件 / 无半成品 / 可重试；未声明 ⇒ 跳过且成功 | `tests/integration/test_phase0_partial_artifact.py`（3 例，含 `test_undeclared_delta_is_skipped_not_failed`） | ✅ |
| AC15 | 跨轴：同一 improvement 同触两轴 ⇒ 一次 P0 两份产物都正确 | 同上 `test_cross_axis_produces_both_artifacts` | ✅ |

## 验证步骤（verifier 契约 1–5 步）

1. **静态检查 / 编译**：`./test.sh --gates` ⇒ **ALL PASSED**（断言质量+隔离门 / ruff / mypy strict / doctor structural 10 类 / markdown drift / ADR 形态增量门 / `openspec validate --all` **164/164**）
2. **单元测试**：`pytest tests/unit` ⇒ **3697 passed / 2 skipped / 6 failed**（6 个失败见下「环境性失败」）
3. **集成 / 端到端**：`pytest tests/integration` ⇒ **195 passed**；`openspec validate <change> --strict` ⇒ **valid**
4. **边界与错误路径**：AC2（不可解析）/ AC7（三类退化形态）/ AC9（目标缺失）/ AC13（CLI 缺失 / 旧版本）/ AC14（拒绝后零残留 + 重试）均有专属用例
5. **遗留清扫复核**：`grep -rE "TODO|FIXME|XXX|pytest.skip|.only("` 在本次改动的 11 个文件 ⇒ **零残留**；变异标记 `MUTATION` ⇒ **0 处**（全部回滚）

## 全量回归（AGENTS.md 的 Archive 前门）

- `./test.sh --bats --regression` ⇒ **0 新增失败**（4 已知 = baseline）
- `pytest tests/unit + tests/integration` ⇒ 6 环境性失败（见下）+ 3892 passed

### 环境性失败登记（**非本次引入**）

`tests/unit/test_resolve_project_root_contract_python.py`（5 例）+ `test_skills_lib_python_resolve_project_root.py`（1 例）：
断言「实现解析到 worktree 根」，而实现经 `--git-common-dir` 解析到**主仓** ⇒ **只在 `git worktree` 下发生**。
证据：同一组测试在**主仓**跑 ⇒ **24 passed**；根解析代码路径不在本 change 的 diff 内
⇒ 属「worktree 模式下的既有不一致」，另案（根解析的 worktree 语义裁决）。

## 已知遗留（登记，不静默）

| # | 遗留 | 归属 |
|---|---|---|
| 1 | `iteration.json` 的 `tasks_done` 在实现后未刷新（`0/33`）⇒ `rdd-verifier` 批量分流不识别本 change | U5 `fix-builder-handoff-p2-lifecycle-truth`（同类缺陷：状态在错误时点写入） |
| 2 | worktree 模式下 6 个 project-root 测试失败（见上） | 另案（根解析语义） |
| 3 | 主 spec `generator-scope-extraction` 的 `## Purpose` 仍是归档占位（`openspec validate --all` WARNING，非本次引入） | 另案（存量 spec 债） |
| 4 | `validate_delta_targets.py` 的「目录名即 target」解析同步只做到**生成侧**（P0 预检）；P3 archive 前的复用未接线 | 本 change 的 design D-8 已声明接线点，**实现只完成生成侧**（AC 未覆盖 archive 侧） |

## 已用轮次

**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）。失败项：**0**（6 个环境性失败不计入 implementation_gap）。

---

# 附：立项产物验收（轮次 0 · 2026-11-27 · 实现前）

> 以下为 P1.5 阶段的报告原文（保留审计链；它只判定立项产物，不判定实现）。

## 判据来源（优先级 1 → 4）

| # | 来源 | 本次采用 |
|:--:|---|---|
| 1 | 用户本次明确给出的验收条件 | 「按这个顺序起 change」= 起 W1（U1+U2 合批）一个 change，且**每个改进都要带 TDD 测试** |
| 2 | `openspec/changes/fix-proposal-generator-output-fidelity/proposal.md` 的 `## Acceptance` | **15 条 AC**（AC1–AC15）逐条 |
| 3 | 本次变更自己声明的行为 | 改进草稿 15 条 AC + design.md 的 D-1~D-9 |
| 4 | ADR 的 Verification 章 | 不适用（无 ADR 变更；载体入口沿 ADR-0025 D6） |

## 逐条判定

### A 组 · 立项产物本身（本次可判）

| # | 判据 | 证据 | 判定 |
|:--:|---|---|:--:|
| A1 | change 骨架存在且结构合规 | `openspec/changes/fix-proposal-generator-output-fidelity/` = `proposal.md` + `design.md` + `tasks.md` + `specs/{generator-scope-extraction, spec-delta-generator-fidelity}/spec.md` | ✅ PASS |
| A2 | openspec 结构校验 | `openspec validate fix-proposal-generator-output-fidelity --strict` ⇒ `is valid`；`openspec validate --all` ⇒ **164 passed / 0 failed** | ✅ PASS |
| A3 | **MODIFIED 场景名守恒**（archive 前置，AC9/AC14 的目标判据） | 自写比对脚本：MODIFIED `generate-proposal-empty-section-fallback`（main 2 场景 → delta 3，missing=∅）、`generate-proposal-backward-compatible`（main 1 → delta 2，missing=∅）⇒ **missing = ∅** | ✅ PASS |
| A4 | delta 落点 = **按 capability 分目录**（design D-3） | `specs/generator-scope-extraction/spec.md`（MODIFIED 既有 capability）+ `specs/spec-delta-generator-fidelity/spec.md`（ADDED 新 capability）；**P0 自动生成的退化 delta 已删除** | ✅ PASS |
| A5 | proposal 的 AC 与改进草稿**逐条一致**（15/15，零漂移） | `proposal.md` 的 `## Acceptance` 15 条 ↔ 改进草稿 `## 验收标准` 15 条（AC 编号 1:1） | ✅ PASS |
| A6 | plan = **TDD 5 步 + 变异第 6 步** | `.rddf/plans/fix-proposal-generator-output-fidelity.md`：6 Task × 5 标准步（各 6）+ **3 个 Task 带 Step 6 变异验证**（Task2/4/5）；`Files:` 行 6；Header Goal/Architecture/TechStack 各 1 | ✅ PASS |
| A7 | tasks.md = 仓内 house style + AC 覆盖对照 | `## Task 1..6` + 每 Task 的 5(+1) 步 checkbox + 末尾 **AC 覆盖对照表**（AC1–AC15 → Task → 类型） | ✅ PASS |
| A8 | design.md 落定 4 项未决载体（metis 要求的裁决） | D-1 载体=**粗体头行**（与 ADR-0025 D6 的「头部」一致 + 纯 stdlib）；D-3 落点=**改**（新旧并存）；D-4 标题优先级=**保持现状候选序 + 锁定 + 提示**；D-5 版本探测=**新建语义化模块** | ✅ PASS |
| A9 | 守卫接线点裁决（metis：仓内无可执行调用方） | design D-8：**P0 生成时**本地预检（目标存在 + Scenario 守恒），P3 archive 前复用 | ✅ PASS |
| A10 | 语料回归判据形态（metis：白名单判别力为零） | design D-7 + AC4：**golden snapshot**（期望输出入库）+ 形态标签表 + 动态计数 + `generated_at` | ✅ PASS |
| A11 | 半成品陷阱被覆盖（metis：`> "$DELTA_FILE"` 留空文件） | design D-6 + AC14：临时文件 + 成功后 `mv`；拒绝 ⇒ 无空文件、无半成品、可重试 | ✅ PASS |
| A12 | 遗留清扫（TODO / 半截实现 / 占位符 / 临时日志） | `grep -rE "TBD\|TODO\|FIXME\|XXX\|待补\|implement later\|fill in details\|Similar to Task"` 命中 **1 处 = spec 正文里的字面量 `- (TBD)`**（那是 requirement 禁止输出的目标串，**非残留**）⇒ **零残留** | ✅ PASS |
| A13 | 改进草稿的审查载体（无载体 = 未审） | 合并稿头部「metis 结论（2026-11-27 · 本轮 1 轮覆盖本稿）」段，含 metis 3 blocker + 10 项 high/medium 的**逐条处置表**（已改 / design 裁决 / 跨轴集成） | ✅ PASS |
| A14 | 提案池与台账一致 | 合并稿已入 `improvement-approved.md`（P0 · 2026-11-27 · 已批准）；两份源草稿标「已合并」并**移出**提案池 ⇒ 不被重复拾取 | ✅ PASS |
| A15 | 交接面可判定 | `.planner-handoff.json`：`awaiting_builder: ["fix-proposal-generator-output-fidelity"]` + `recommended_route: complex`；`.rddf/state/builder/<change>.json`：`approval_status=approved`；iteration.json 已登记该 change | ✅ PASS |

### B 组 · 实现层 AC（**不在本次判定范围**，仅核对「有判据可判」）

AC1–AC15 在 proposal / 改进草稿 / plan / tasks 四处**编号一致且各有归属 Task**（A6/A7 已证）；
⇒ **实现开始后**逐条取证。**本次不判实现达标**（tasks 全未勾）。

## 验证步骤（verifier 契约 1–5 步）

1. **静态检查 / 编译**：`./test.sh --gates` ⇒ **ALL PASSED**（断言质量+隔离门 / ruff / mypy strict / doctor structural / markdown drift / ADR 形态增量门 / `openspec validate --all` 164 passed）
2. **单元测试**：`./test.sh --unit` ⇒ **3675 passed / 2 skipped**（本次未改实现 ⇒ 零回归）
3. **集成 / 端到端**：`openspec validate <change> --strict` ⇒ valid；`openspec validate --all` ⇒ 164/164；**MODIFIED 场景名守恒自写比对 ⇒ missing = ∅**
4. **边界与错误路径**：AC1/AC2（表格 / 混排 / 无条目 / 表内逗号）、AC6（标题并存）、AC8/AC9（载体缺失 / 目标缺失 / 场景缺失）、AC13（版本分支）、AC14（拒绝不留半成品）、AC15（跨轴）—— 判据与 plan Step 均已就位
5. **遗留清扫复核**：见 A12 ⇒ 零残留

## 失败项与路由

**无失败项**（本次交付 = 立项产物，实现尚未开始 ⇒ 不存在 implementation_gap / proposal_drift）。

## 已知遗留（登记，不静默）

| # | 遗留 | 归属 |
|---|---|---|
| 1 | 实现层 15 条 AC 未验证 | 下一阶段（P2 实施 + P3 archive gate） |
| 2 | **4 项 design 裁决已定稿**（D-1/D-3/D-4/D-5），但其中 D-3（落点目录改）属**契约面** ⇒ 需 **ADR Status Update**（architect 域） | architect / builder |
| 3 | `validate_delta_targets.py` 仓内**当前无调用方** ⇒ 本 change 需接线（design D-8） | 本 change Task 6 |
| 4 | 本仓 `openspec/changes/` **gitignored**（`git.openspec_tracked=false`）⇒ change 产物为**本地产物**，交付面 = 改进草稿 + plan + 本报告 | 已知约束 |

## 已用轮次

- 本地验收轮次：**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）
- 审查链消耗：oracle 1（治理面，PASS-WITH-NOTES）→ critic 1（arch 档，REJECT）→ critic 复审 1（APPROVE，mergeable: yes）；metis 批量轮 1（9 份草稿）+ 合并稿 1 轮
