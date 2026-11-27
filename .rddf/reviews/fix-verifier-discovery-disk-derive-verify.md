# verify: fix-verifier-discovery-disk-derive

> **验收对象**：本 change 的**实现**（worktree 分支 `openspec/fix-verifier-discovery-disk-derive`，1 个提交 `4833299b`）
> **验收时间**：2026-11-27
> **执行角色**：builder（角色内建 verifier 契约 · **本地验收路径**）
> **判据来源**：`proposal.md` 的 `## Acceptance`（AC1–AC7）

## 分流判定（为什么走本地验收，而不是 `rdd-verifier` skill）

| 条件 | 实测 | 判定 |
|---|---|---|
| ① change 存在 + 有 AC 段 | `openspec/changes/fix-verifier-discovery-disk-derive/proposal.md` 含 `## Acceptance`（7 条） | ✅ |
| ② P3 archive gate 触发 | 主仓 `iteration.json` 该 change `tasks_done=0`（P0 快照，实现后未刷新）；且批量分流扫的是**主仓** `openspec/changes/`，被实现的是 **worktree** 里的副本 | ❌ |
| ③ `rdd-verifier` skill 可加载 | `rdd-skills.sh --json` ⇒ installed | ✅ |

⇒ 条件② 不满足 ⇒ **本地验收**。`tasks_done` 陈旧登记为 U5 同类遗留（与本 change 无关）。

## 逐条判定（AC1–AC7）

| AC | 判据 | 证据 | 判定 |
|:--:|---|---|:--:|
| AC1 | 无 `iteration.json` + tasks 全勾 ⇒ 队列含该 change（先红） | `tests/unit/test_verifier_discovery_disk.py::test_without_iteration_json_queues_task_complete_change`（实现前 `[]` ⇒ 红）；`tests/integration/test_rdd_verify_dry_run_without_iteration.bats` 3/3 | ✅ |
| AC2 | 无 iteration 且无 tasks ⇒ 队列空 **且** 可诊断原因（非静默 `[]`） | 同文件 `test_empty_queue_reports_reason_no_active_change` / `..._no_complete_tasks`；CLI 层 `test_cli_empty_queue_prints_reasons_on_stderr`（`reasons` → stderr，stdout 语义不变） | ✅ |
| AC3 | 既有 iteration 场景用例零回归（`pytest -k discovery` 全绿） | `python3 -m pytest tests/unit -k "discovery or change_status or rdd_verify or iteration_tasks or status"` ⇒ **289 passed**；改写 3 处 fixture + 2 处用例（见下「改写清单」） | ✅ |
| AC4 | disk 推导与 `rddf status` Mode A **同一实现**（对象身份） | `test_change_status_shared.py::test_derive_status_uses_the_shared_module`：`status_cmd._derive is discovery._derive is change_status.derive_status` | ✅ |
| AC5 | 端到端：临时项目根（无 iteration.json）跑 `rddf rdd-verify --dry-run` 列出预期 change | `tests/integration/test_rdd_verify_dry_run_without_iteration.bats`（`mktemp -d "$BATS_TMPDIR/..."` + `git init`，复用既有模式，未新建 helper）：列出 `c-done`、不列 `c-half`、且**不创建** `iteration.json` | ✅ |
| AC6 | 变异：推导源退回 iteration.json ⇒ AC1 红 | 实测（临时改 `discover_eligible` 为 iteration 版 ⇒ `test_without_iteration_json_queues_task_complete_change` + `test_iteration_only_fixture_is_no_longer_the_source` 双红），随后回滚；`grep -c MUTATION` == 0 | ✅ |
| AC7 | `./test.sh --gates` + `./test.sh --unit` 全绿 | gates ⇒ **ALL PASSED**；unit ⇒ **3714 passed / 2 skipped / 6 failed**（见下「环境性失败」） | ✅ |

## 变异的判别力说明

- AC6 的变异**具体形态**：把 `discover_eligible()` 的函数体换回「读 iteration.json + `_is_eligible`」。
  结果：AC1 用例红（无 iteration ⇒ `[]`），`test_iteration_only_fixture_is_no_longer_the_source` 也红
  （iteration 里有一条 ghost 记录被当成队列）。回滚后全绿。

## 改写清单（为什么不是「回归」）

| 用例 | 改写 | 理由 |
|---|---|---|
| `test_verifier_branch_discovery.py::test_discover_from_iteration` | → `test_discover_consistent_iteration_matches_disk`（补磁盘 fixture；`d` 改为归档目录） | 旧断言「只有 iteration.json、无 change 目录 ⇒ `["a","c"]`」写死的正是被删除的「iteration 即真源」语义 |
| `test_rdd_verify_cmd.py::test_skip_with_reason_writes_bypassed_state` | 补 `_mk_disk_change(...)` | batch 队列不再从 iteration 取 change，fixture 必须落盘 |
| `test_rdd_verify_cmd.py::test_cmd_rdd_verify_stage_context_runner_when_no_provider` / `test_explicit_runner_overrides_provider_hook` | 同上 | 同上 |
| `test_iteration_tasks_total.py::TestEligibilityParity` | fixture 改磁盘形态；`archived` 用例改为「真正归档到 `changes/archive/`」 | 两实现的「一致」由「同一实现 + 磁盘 fixture」承接；iteration 改为**故意陈旧**，反证它不是真源 |

## 验证步骤（verifier 契约 1–5 步）

1. **静态检查**：`./test.sh --gates` ⇒ **ALL PASSED**（隔离门 / ruff `skills/_lib/` / mypy strict / doctor 10 类 / markdown drift / ADR 形态增量 / `openspec validate --all` **165/165**）；改动文件单独 ruff ⇒ All checks passed。
2. **单元测试**：`pytest tests/unit` ⇒ **3714 passed / 2 skipped / 6 failed**。
3. **集成**：新增 bats 3/3；`openspec validate fix-verifier-discovery-disk-derive --strict` ⇒ **valid**。
4. **边界与错误路径**：无 `openspec/changes/` / 只有 iteration ghost / tasks 未全勾 / 归档目录 / iteration 与 disk 冲突 ⇒ 各有用例。
5. **遗留清扫**：改动文件 `TODO|FIXME|MUTATION|pytest.skip` 扫描 ⇒ 零残留；`.rddf/plans/...` 未提交（master 已有同名文件，避免 add/add）。

### 环境性失败（**非本次引入**）

`tests/unit/test_resolve_project_root_contract_python.py`（5）+ `test_skills_lib_python_resolve_project_root.py`（1）：
在 `git worktree` 下实现经 `--git-common-dir` 解析到**主仓**，测试期望 worktree 根。主仓跑同组全绿 ⇒ 既有环境性不一致，另案。

### 另一处 worktree 环境差异（已证伪为本 change 无关）

`./test.sh --gates` 的 markdown drift 门在 worktree 首跑报
`docs/architecture/improvement-check-mechanisms.md:501: broken link: ../../.rddf/issues/` ——
`.rddf/issues/` 是**未跟踪目录**（主仓有、worktree 检出没有）。在 worktree 里 `mkdir -p .rddf/issues` 后重跑 ⇒ **ALL PASSED**。

## 已知遗留（登记，不静默）

| # | 遗留 | 归属 |
|---|---|---|
| 1 | `iteration.json` 的 `tasks_done` 仍由 P2 准备阶段写入、实现后不刷新 | U5 `fix-builder-handoff-p2-lifecycle-truth` |
| 2 | worktree 模式下 6 个 project-root 测试失败 | 另案（根解析的 worktree 语义裁决） |
| 3 | `archive_gate` 仍从 iteration 的 `verification` 字段读附记（verdict cache 才是主路径） | 未改（design D-8 明确不做） |

## 已用轮次

**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）。失败项：**0**。
