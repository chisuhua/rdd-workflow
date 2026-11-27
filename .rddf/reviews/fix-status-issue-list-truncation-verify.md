# verify: fix-status-issue-list-truncation

> **验收对象**：本 change 的**实现**（worktree 分支 `openspec/fix-status-issue-list-truncation`，1 个提交 `80499f4d`）
> **验收时间**：2026-11-27
> **执行角色**：builder（角色内建 verifier 契约 · **本地验收路径**）
> **判据来源**：`proposal.md` 的 `## Acceptance`（AC1–AC7）

## 分流判定（为什么走本地验收，而不是 `rdd-verifier` skill）

| 条件 | 实测 | 判定 |
|---|---|---|
| ① change 存在 + 有 AC 段 | `openspec/changes/fix-status-issue-list-truncation/proposal.md` 含 `## Acceptance`（7 条） | ✅ |
| ② P3 archive gate 触发 | 主仓 `iteration.json` 该 change `tasks_done=0`（P0 快照）；批量分流扫主仓、实现落在 worktree | ❌ |
| ③ `rdd-verifier` skill 可加载 | installed | ✅ |

⇒ 条件② 不满足 ⇒ **本地验收**。

## 逐条判定（AC1–AC7）

| AC | 判据 | 证据 | 判定 |
|:--:|---|---|:--:|
| AC1 | 6 条 stale issue ⇒ **6 条全部列出**，标题计数 == 实际列出 | `tests/unit/test_status_issue_list_not_truncated.py::test_six_issues_are_all_listed`（构造 6 条已归档 + 非终态状态行 ⇒ 断言 6 行 `- stale-` 且标题含 `6 improvement issue(s)`、无「还有」行）；修复前只列 5 ⇒ 红 | ✅ |
| AC2 | issue > 阈值 ⇒ **明示**未展开数与去处，标题不暗示全列 | 同文件 `test_beyond_limit_announces_the_remainder`（30 条 ⇒ 列 20 + 「还有 10 条未展开」+ `rddf dashboard` + 标题含「列出前 20」） | ✅ |
| AC3 | 状态摘要超长 ⇒ `…` 结尾且 `「」`/`**` 成对 | 同文件 `test_long_status_snippet_is_trimmed_at_a_safe_boundary`（`「` 落在 40 字窗口内、`」` 落在窗口外 ⇒ 朴素 `raw[:40]` 必留半截引号）+ `test_snippet_never_leaves_a_half_open_quote` + `test_short_status_snippet_is_untouched` | ✅ |
| AC4 | 既有 status / dashboard 用例零回归 | `python3 -m pytest tests/unit -k "status or dashboard or improvement_status" -q` 全绿；全量 unit **3758 passed / 2 skipped / 6 failed**（6 = 既有 worktree 环境性） | ✅ |
| AC5 | 摘要清洗**单一真源**（复制第二份即红） | 同文件 `test_snippet_cleaner_is_the_shared_one`（`dashboard.clean_status_snippet is improvement_status.clean_status_snippet`）+ `test_no_second_cleaner_definition`（`_lib/` 内 `def clean_status_snippet` 仅一处） | ✅ |
| AC6 | 变异：渲染退回 `[:5]` 且去明示行 ⇒ AC1/AC2 红；摘要退回硬切 ⇒ AC3 红 | 实测**两条变异同时施加** ⇒ 3 例红（`test_six_issues_are_all_listed` / `test_beyond_limit_announces_the_remainder` / `test_long_status_snippet_is_trimmed_at_a_safe_boundary`），回滚后 9 例全绿；`grep -c MUTATION` == 0 | ✅ |
| AC7 | `./test.sh --gates` + `./test.sh --unit` 全绿 | gates ⇒ **ALL PASSED**（`openspec validate --all` 165/165）；`openspec validate fix-status-issue-list-truncation --strict` ⇒ **valid** | ✅ |

## 变异腿的判别力说明

| 变异 | 形态 | 变红的用例 |
|---|---|---|
| ① 渲染 | `for err in snapshot.errors[:5]`（无明示行） | AC1（6 条只列 5）+ AC2（无「还有 N 条」） |
| ② 摘要 | `(status or '').strip()[:40]` 硬切 | AC3（留下半截 `「`） |

两条变异**同时**施加 ⇒ 3 例红 ⇒ 三条判据各自有判别力（不是被同一条断言顺带覆盖）。

## 验证步骤（verifier 契约 1–5 步）

1. **静态检查**：`./test.sh --gates` ⇒ **ALL PASSED**（隔离门 / ruff / mypy strict / doctor 10 类 / markdown drift / ADR 形态增量 / openspec validate 165/165）；改动文件 ruff 单跑 ⇒ All checks passed。
2. **单元测试**：`pytest tests/unit` ⇒ **3758 passed / 2 skipped / 6 failed**（6 = 既有 worktree 环境性失败）。
3. **集成**：`openspec validate <change> --strict` ⇒ **valid**（requirement 正文 479 字 ⇒ 未触发 >500 的 very-long 告警，也**未增长** very-long 债）。
4. **边界与错误路径**：issue 数为 0（整段不出现）、issue ≤ 阈值（全列）、issue > 阈值（明示余量）、短摘要（不加 `…`）、长摘要（`…` + 成对标记）。
5. **遗留清扫**：改动文件 `TODO|FIXME|MUTATION|pytest.skip` 扫描 ⇒ 零残留。

### 环境性失败（**非本次引入**）

`tests/unit/test_resolve_project_root_contract_python.py`（5）+ `test_skills_lib_python_resolve_project_root.py`（1）：
worktree 下实现经 `--git-common-dir` 解析到主仓，测试期望 worktree 根；主仓跑同组全绿 ⇒ 既有不一致，另案。

## 已知遗留（登记，不静默）

| # | 遗留 | 归属 |
|---|---|---|
| 1 | `iteration.json` 的 `tasks_done` 仍不刷新 | U5 |
| 2 | worktree 模式下 6 个 project-root 测试失败 | 另案 |
| 3 | CppTLM 侧 6 条**已归档但状态行陈旧**的 improvement 未回填（工具只指路） | 项目侧自修（U4 的 Out of Scope 明确） |
| 4 | 阈值 20 是工程取舍（>20 明示未展开，全量在 dashboard） | 已由测试钉住；若将来要更大/更小，须同步改测试与 spec |

## 已用轮次

**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）。失败项：**0**。
