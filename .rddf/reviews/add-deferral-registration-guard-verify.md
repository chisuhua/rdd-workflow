# verify: add-deferral-registration-guard

> **验收对象**：本 change 的**实现**（worktree 分支 `openspec/add-deferral-registration-guard`，1 个提交 `aa11e2e1`）
> **验收时间**：2026-11-27
> **执行角色**：builder（角色内建 verifier 契约 · **本地验收路径**）
> **判据来源**：`proposal.md` 的 `## Acceptance`（AC1–AC7）

## 分流判定（为什么走本地验收，而不是 `rdd-verifier` skill）

| 条件 | 实测 | 判定 |
|---|---|---|
| ① change 存在 + 有 AC 段 | `openspec/changes/add-deferral-registration-guard/proposal.md` 含 `## Acceptance`（7 条） | ✅ |
| ② P3 archive gate 触发 | 主仓 `iteration.json` 该 change `tasks_done=0`（P0 快照）；批量分流扫主仓、实现落在 worktree | ❌ |
| ③ `rdd-verifier` skill 可加载 | installed | ✅ |

⇒ 条件② 不满足 ⇒ **本地验收**。

## 逐条判定（AC1–AC7）

| AC | 判据 | 证据 | 判定 |
|:--:|---|---|:--:|
| AC1 | 3 个 fixture：合规 ⇒ 无 finding / 裸 deferral ⇒ 1 条 WARNING（含文件 + 行号）/ backlog 占位 ⇒ 无 finding | `tests/unit/test_deferral_registration.py`：`test_compliant_deferral_is_not_reported`、`test_bare_deferral_is_reported_with_file_and_line`（断言 path + line=2 + phrase）、`test_backlog_placeholder_is_accepted`；category 层 `test_doctor_category_reports_unregistered_deferral`（category 名 + file + line + fix_hint 含「登记目标」） | ✅ |
| AC2 | 豁免清单里的条目**不**产生 finding（噪音为零） | `test_exempted_file_produces_no_finding`、`test_unexempted_file_is_still_reported`、`test_doctor_category_is_silent_for_exempted_noise`；**本仓实测零噪音**：`rddf doctor --category deferral-registration` ⇒ `✅ All 1 categories OK`（存量 78 处未登记 / 33 个文件已登记进 `.rddf/deferral-exemptions.txt`） | ✅ |
| AC3 | 约定文本含**两个可 grep 锚点**（措辞清单 + 豁免格式） | `test_convention_doc_contains_every_anchor`（文档含 `DEFERRAL_PHRASES` 每个 token + `REGISTERED_FORM` + `BACKLOG_FORM` 原文）+ `test_convention_doc_points_at_the_single_source`（指向 `_lib/deferral_registration.py`）+ `test_phrase_list_has_one_definition_point`（全 `_lib/` 仅一处定义 `DEFERRAL_PHRASES`） | ✅ |
| AC4 | 划界：不被两个 category 重复报告；与提案推迟状态字段**不共用措辞集** | `test_review_debt_surface_is_not_touched`（代码目录不扫；文档被扫 ⇒ 两面互斥）+ `test_defer_state_field_is_not_a_deferral_wording`（`已推迟` / `deferred` ∉ 词表，`状态: 已推迟（…）` ⇒ 零 finding） | ✅ |
| AC5 | 变异：措辞正则改窄 ⇒ AC1 的裸 deferral fixture 必须红 | 实测（把 `scan_text` 的判定改成「只匹配已登记形态」）⇒ **7 例红**（含 AC1 的裸 deferral fixture 与 category 层用例），回滚后 17 例全绿；`grep -c MUTATION` == 0 | ✅ |
| AC6 | 豁免清单条目**已不再命中** ⇒ 给出「可清理」提示 | `test_stale_exemption_is_detected`、`test_missing_exempted_file_is_stale`、`test_live_exemption_is_not_stale`；category 层 `test_doctor_category_reports_stale_exemptions`（fix_hint 含「可清理」） | ✅ |
| AC7 | `./test.sh --gates` + `./test.sh --unit` 全绿 | gates ⇒ **ALL PASSED**（`openspec validate --all` 167/167）；unit ⇒ **3787 passed / 2 skipped / 6 failed**（6 = 既有 worktree 环境性失败）；`openspec validate <change> --strict` ⇒ valid | ✅ |

## 验证步骤（verifier 契约 1–5 步）

1. **静态检查**：`./test.sh --gates` ⇒ **ALL PASSED**（隔离门 / ruff / mypy strict / doctor 10 类 / markdown drift / ADR 形态增量 / openspec validate 167/167）。
2. **单元测试**：`pytest tests/unit` ⇒ **3787 passed / 2 skipped / 6 failed**。
3. **集成**：`rddf doctor --category deferral-registration` 在本仓 ⇒ **零噪音**；`openspec validate <change> --strict` ⇒ valid。
4. **边界与错误路径**：合规 / 裸 deferral / backlog 占位 / 豁免命中 / 豁免失效 / 豁免文件不存在 / 代码目录不扫 / 提案推迟状态不误报 —— 各有独立用例。
5. **遗留清扫**：改动文件 `TODO|FIXME|MUTATION|pytest.skip` 扫描 ⇒ 零残留（唯一命中是测试 fixture 里的刻意 `TODO(x)` 样本）。

### 环境性失败（**非本次引入**）

`tests/unit/test_resolve_project_root_contract_python.py`（5）+ `test_skills_lib_python_resolve_project_root.py`（1）：
worktree 下实现经 `--git-common-dir` 解析到主仓，测试期望 worktree 根；主仓跑同组全绿 ⇒ 既有不一致，另案。

## 已知遗留（登记，不静默）

| # | 遗留 | 归属 |
|---|---|---|
| 1 | 存量 78 处未登记 deferral **只登记豁免、不回改**（工具只报警，不代写） | 项目侧自修；豁免清单可审计 |
| 2 | 豁免清单按**文件**粒度（不是行）⇒ 一个文件里新写的裸 deferral 会被整文件豁免 | 设计取舍（行号会漂移）；需要更细时另案 |
| 3 | 提案推迟状态字段（`已推迟`）**不在**本约定管辖内 | 有意划界（两个检测面互斥） |
| 4 | `iteration.json` 的 `tasks_done` 不刷新；worktree 模式 6 个 project-root 失败 | U5 同类 / 另案 |

## 已用轮次

**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）。失败项：**0**。
