---
优先级: P3
来源: ADR-0062/0063 调研（2026-11-19）收口 ADR-0044 的 deferred follow-up
阶段: v4
分类: core-impl
类型: debt
主题: 死代码清理
---

## 架构依据

ADR-0044（v4 Wave 3 硬移除）的「deferred follow-up」承诺后续收口。2026-11-19 实测：推荐值已全部改为 `rdd-*`，但仍有**恒假判据 / 死配置 / 文档文案**三类残留。

**metis 修订（2026-11-19）**：原计划的「全仓 grep ⇒ 0」被否决 —— 它与已采纳的 `v4_residue_check.py` 决定冲突（该 checker 明确「只扫契约面，不扫注释与历史文档」），且会拉进 125 个测试文件与历史 docstring，属 scope creep。本 change 改为**接已有 checker 的 gate**，而不是重造一套全仓扫描。

## 范围

### In Scope

1. `pyrightconfig.json`：删除 3 个指向不存在目录的 `executionEnvironment` root（`skills/guide-arch` / `skills/guide-plan` / `skills/guide-ship`）。**不含** `skills/guide` 本身（由 `retire-guide-orchestrator` 处理）。
2. `_lib/workflow_synthesizer.py`：`_fallback_recommendation` docstring 的 `guide-ship` → `rdd-builder`（与实际代码对齐）。
3. `tests/integration/test_global_install_external_project.bats:349-350`：移除两条恒假的 `~/.agents/skills/guide-plan` / `guide-ship` 死分支。
4. `tests/scripts/check_wrap_grep.sh:11-13`：三条指向不存在目录的路径（`guide-arch` / `guide-plan` / `guide-ship`）。
5. `tests/unit/test_design_done_gate.sh:8-9`：`source skills/guide-design/scripts/design_done_check.sh`（路径不存在，测试恒跳过）。
6. `tests/unit/test_feedback_cli.py:24,42` + `tests/integration/test_feedback_cmd.bats`：**保留 1 条** `--from guide-design`（断言 legacy 值仍被接受），**新增 1 条** `--from rdd-builder`。不做纯替换 —— 纯替换会丢掉 legacy 兼容的唯一行为覆盖。
7. **`v4-residue` 纳入 doctor advisory gate**：`skills/rdd-doctor/scripts/doctor_main.py` 的 `advisory` 类别加入 `v4-residue`（当前 `structural` 10 类与 `advisory` 4 类都不含它 ⇒ checker 从未在 CI 跑过）。同时扩展 `v4_residue_check.py` 的 `_R2_PATTERN` 覆盖 `\bor guide-\w+` 形态，并加一条负向用例。

### Out of Scope

- `skills/guide/` 本体与 `skills/guide/scripts/scan-state.sh`（由 `retire-guide-orchestrator` 归档；原计划的 `scan-state.sh:669` 文案修改随之作废）。
- `_lib/schemas/iteration_schema.json` / `verifier_loop_schema.json` / `feedback_entry_schema.json` 的 legacy 枚举 —— 注释写明是为存量状态文件校验保留；与 `retire-guide-orchestrator` 的 schema 政策保持一致（保留 enum、只删代码路径）。
- `tests/**` 里对 `guide-*` 的历史断言与 docstring —— `v4_residue_check.py` 的已采纳口径明确不扫这些。
- `_lib/feedback_appender.py:34` 的 `VALID_SOURCES`、`_types.py:33-40` 的 intent 别名 —— 运行时兼容面，不是「残留」。
- `docs/migration/v3-to-v4.md` 与 ADR 历史正文 —— 永久保留。

## 关键场景

- **GIVEN** 一个 v4 项目跑 `rddf doctor --category v4-residue`，**WHEN** 代码里出现 `skill_use("guide-` 或 `or guide-` 形态，**THEN** 能报 WARNING。
- **GIVEN** 有人在 `pyrightconfig.json` 里加回不存在目录，**WHEN** 跑本 change 的 AC 检查，**THEN** 能报出来。

## 技术约束

- 不改任何 schema enum。
- 不改推荐逻辑。
- `v4-residue` 进 **advisory** 而非 structural（R2 本身是 WARNING，进 structural 也拦不住；advisory 先建 baseline）。
- 清理恒假判据后必须跑对应测试文件，确认不是「原本就红」。

## 验收标准

- [ ] AC-1: `pyrightconfig.json` 中不存在 `skills/guide-arch` / `skills/guide-plan` / `skills/guide-ship` 条目
- [ ] AC-2: `_lib/workflow_synthesizer.py` 的 `_fallback_recommendation` docstring 不再声称 fallback 指向 `guide-ship`
- [ ] AC-3: `tests/integration/test_global_install_external_project.bats` 不含 `~/.agents/skills/guide-plan` 与 `guide-ship`
- [ ] AC-4: `tests/scripts/check_wrap_grep.sh` 与 `tests/unit/test_design_done_gate.sh` 不再引用不存在的 `skills/guide-*` 路径
- [ ] AC-5: `tests/unit/test_feedback_cli.py` + `tests/integration/test_feedback_cmd.bats` 同时覆盖 `--from guide-design`（legacy 接受）与 `--from rdd-builder`（新值）
- [ ] AC-6: `python3 -m pytest tests/unit/test_v4_residue_check.py -q` 全绿；`bash skills/rdd-doctor/scripts/doctor.sh --category v4-residue` 可运行（不被 unknown-category 拒绝）
- [ ] AC-7: `v4_residue_check.py` 的 `_R2_PATTERN` 能命中 `or guide-plan` 形态（负向用例证明）
- [ ] AC-8: `python3 -m pytest tests/unit/ -q` + `bats tests/_lib/test_skill.bats tests/unit/test_design_done_gate.sh` 全绿
- [ ] AC-9: 全量门 `./test.sh --full --regression` ⇒ 未评估 0 + 新增失败 0
