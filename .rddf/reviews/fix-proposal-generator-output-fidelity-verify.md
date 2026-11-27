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
