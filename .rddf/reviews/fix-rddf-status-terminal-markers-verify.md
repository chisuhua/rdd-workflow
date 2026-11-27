# verify: fix-rddf-status-terminal-markers

> **验收对象**：本 change 的**实现**（worktree 分支 `openspec/fix-rddf-status-terminal-markers`，1 个提交 `9efe65cd`）
> **验收时间**：2026-11-27
> **执行角色**：builder（角色内建 verifier 契约 · **本地验收路径**）
> **判据来源**：`proposal.md` 的 `## Acceptance`（AC1–AC7）

## 分流判定（为什么走本地验收，而不是 `rdd-verifier` skill）

| 条件 | 实测 | 判定 |
|---|---|---|
| ① change 存在 + 有 AC 段 | `openspec/changes/fix-rddf-status-terminal-markers/proposal.md` 含 `## Acceptance`（7 条） | ✅ |
| ② P3 archive gate 触发 | 主仓 `iteration.json` 该 change `tasks_done=0`（P0 快照）；批量分流扫主仓、被实现落在 worktree | ❌ |
| ③ `rdd-verifier` skill 可加载 | installed | ✅ |

⇒ 条件② 不满足 ⇒ **本地验收**。

## 逐条判定（AC1–AC7）

| AC | 判据 | 证据 | 判定 |
|:--:|---|---|:--:|
| AC1 | `已落地` / `已拆分` / `已取代` 三个 token 判终态（修复前红） | `tests/unit/test_improvement_status_markers.py::test_registry_completion_tokens_are_terminal`（4 参数例）—— 实现前 `TERMINAL_MARKERS` 不存在 ⇒ ImportError（红）；实现后终态 + 标签 `已落地`/`已作废`/`已作废` | ✅ |
| AC2 | 既有终态 token 全部零回归 | 同文件 `test_existing_terminal_tokens_stay_terminal`（11 个 token）+ `test_open_tokens_stay_non_terminal`（10 个）+ `test_every_terminal_marker_is_reachable_through_the_classifier`；既有 `test_dashboard_improvement_status.py` 57 例仍绿 | ✅ |
| AC3 | 已归档/已批准但状态非终态 ⇒ 进 stale 告警面（且不进 pending） | `tests/unit/test_collect_pending_stale.py`：`test_archived_with_stale_status_is_reported_not_hidden`、`test_approved_with_stale_status_is_reported`、`test_terminal_status_stays_silent`（终态不报 stale）、`test_status_view_shows_the_stale_entry`（`rddf status` stdout 可见） | ✅ |
| AC4 | 破损 front matter ⇒ 字段级定位（行号 + 原文） | 同文件 `test_broken_front_matter_reports_line_and_source` ⇒ 错误含 `front-matter line N` 且含 `状态` 那一行原文；实现见 `_lib/state_reader.py::_front_matter_error`（`problem_mark.line + 2` 换算） | ✅ |
| AC5 | 终态词表**单一真源**（复制第二份即红） | 同文件 `test_help_renders_every_terminal_marker`（`rddf status --help` 输出含 `TERMINAL_MARKERS` 每个 token）+ `test_vocabulary_has_no_second_definition_point`（`_lib/**.py` 中除 `improvement_status.py` 外无第二处含 `已落地`/`已拆分`/`已取代`，也无第二个 `*TERMINAL*MARKER*` 常量） | ✅ |
| AC6 | 变异：过滤顺序退回「先过滤后判状态」⇒ AC3 红 | 实测（临时把 `if name in approved or name in archived_names: continue` 提到分类之前）⇒ **4 例红**（archived stale / approved stale / registry token / status 视图），随后回滚；`grep -c MUTATION` == 0 | ✅ |
| AC7 | `./test.sh --gates` + `./test.sh --unit` 全绿 | gates ⇒ **ALL PASSED**（`openspec validate --all` 165/165）；unit ⇒ **3749 passed / 2 skipped / 6 failed**（6 个为既有 worktree 环境性失败） | ✅ |

## 变异腿的判别力说明

变异形态：`collect_pending()` 里把「archived/approved 过滤」提到「状态分类」之前（= 旧顺序）。
结果：AC3 的 4 个用例同时变红 —— 证明「stale 可见」这一行为**依赖过滤顺序**，
不是被别的断言顺带覆盖的。回滚后全绿，`MUTATION` 计数 0。

## 验证步骤（verifier 契约 1–5 步）

1. **静态检查**：`./test.sh --gates` ⇒ **ALL PASSED**（隔离门 / ruff / mypy strict / doctor 10 类 / markdown drift / ADR 形态增量 / openspec validate 165/165）；改动文件 ruff 单跑 ⇒ All checks passed。
2. **单元测试**：`pytest tests/unit` ⇒ **3749 passed / 2 skipped / 6 failed**。
3. **集成**：`openspec validate fix-rddf-status-terminal-markers --strict` ⇒ **valid**。
4. **边界与错误路径**：终态 + 已归档（不报 stale）、非终态 + 已归档/已批准（报 stale）、破损 front matter（字段级定位）、真待办（仍进 pending）、词表每个 token 可达 —— 各有独立用例。
5. **遗留清扫**：改动文件 `TODO|FIXME|MUTATION|pytest.skip` 扫描 ⇒ 零残留。

### 环境性失败（**非本次引入**）

`tests/unit/test_resolve_project_root_contract_python.py`（5）+ `test_skills_lib_python_resolve_project_root.py`（1）：
worktree 下实现经 `--git-common-dir` 解析到主仓，测试期望 worktree 根；主仓跑同组全绿 ⇒ 既有不一致，另案。

## 已知遗留（登记，不静默）

| # | 遗留 | 归属 |
|---|---|---|
| 1 | `iteration.json` 的 `tasks_done` 仍不刷新 | U5 |
| 2 | worktree 模式下 6 个 project-root 测试失败 | 另案 |
| 3 | 既有 improvement 的状态行**不回填**（只读面） | 项目侧自修（proposal 的 Out of Scope 明确） |
| 4 | 「19 条 pending 里 13 条已落地」是历史实测值，本次未复测真实仓的差值 | 复测留作 objective 的 done-when 判据（真实仓 pending 数与人工对账差值 ≤ 1） |

## 已用轮次

**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）。失败项：**0**。
