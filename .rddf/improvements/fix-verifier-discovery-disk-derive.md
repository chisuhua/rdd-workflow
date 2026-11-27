---
优先级: P1
来源: 2026-11-26 oracle 审查（治理面 batch，RW-3 裁决 = 方案 B「disk 化」）+ 2026-11-27 critic 复审确认（不与归档决策冲突）
阶段: phase-3
分类: cli-tooling
类型: improvement
状态: 已归档（2026-11-27 · change `2026-11-27-fix-verifier-discovery-disk-derive` · 7/7 AC pass · 验收报告 `.rddf/reviews/fix-verifier-discovery-disk-derive-verify.md`）
主题: verifier 批量分流队列改为 disk 推导 —— 不再依赖 iteration.json（与「iteration 是流程记账」的既决方向同向）
---

**优先级**: P1 | **来源**: 2026-11-26 oracle 审查裁决（方案 B）+ critic 复审 | **阶段**: phase-3 | **分类**: cli-tooling | **类型**: improvement

## metis 结论（2026-11-27 · 本轮 1 轮覆盖 9 份草稿 · 载体=头部段）

- **「抽共享模块 or 直接复用」二选一未裁决** ⇒ AC4 不能写成「看起来一样」⇒ 改为**对象身份断言**（同一函数对象）。
- 端到端用例的临时项目根应**复用既有 bats 模式**（`$BATS_TMPDIR`），禁新建 helper。
- 「以 disk 为准」的**提示通道**未定 ⇒ 钉 **stderr**（不污染 stdout 视图）。
- 已改：AC4 对象身份断言；AC5 复用既有模式；关键场景 3 补 stderr。


**主题**: verifier 批量分流队列改为 disk 推导 —— 不再依赖 iteration.json

## 架构依据

**已归档的决策（不得推翻）**：`openspec/changes/archive/2026-11-17-register-change-in-iteration/proposal.md:71` 明文 AC：
「`iteration.json` 缺失时**不创建**半成品文件（断言文件仍不存在）」。同篇实现 `phase0_approval.sh:227-230`
只 WARN、不创建。⇒ **「P0 创建 iteration.json」这条路是关闭的**。

**既决的方向**：`4661096a`（`rddf-status-based-on-improvements`）宣布「iteration.json 是**流程记账**，
不是改进提案的维护真源」；`_lib/cli/status_cmd.py:26-30` 的 Mode A 已改读 `openspec/changes/*/tasks.md`
+ `.rddf/state/builder/<name>.json` 做 disk 推导。⇒ **方向是远离 iteration.json**。

**剩下的唯一失效面**（oracle 定位）：`_lib/verifier/discovery.py:32-45` 的 `discover_eligible()` 读 iteration.json，
缺文件时**静默返回 []** ⇒ `_lib/cli/rdd_verify_cmd.py:475-483` 的**批量**分流队列永远空、exit 0；
而 per-change 的 `--stage` 路径（`:442-452`）不依赖 iteration.json ⇒ **批量能力单边失效**。

⇒ 本提案走 **方案 B（disk 化）**：把批量队列的推导源改为 disk，与 `rddf status` Mode A **同源同法**
⇒ 真源数量**减少**（verifier 队列不再依赖 iteration），不制造第三个真源。

## delta 载体（P0 生成输入）

**delta**: modified verifier-lifecycle
**语义要求**: Verifier queue SHALL discover implemented task-complete non-archived changes | The verifier queue SHALL be derived from disk — each `openspec/changes/<name>/tasks.md` task counter plus that change's on-disk status — and MUST NOT consult `iteration.json`. A change is eligible when it is not archived, its disk status is `in_worktree` or `completed`, and its tasks are all checked with a non-zero total. Because `iteration.json` is procedural bookkeeping, a missing file MUST NOT empty the queue and a stale entry MUST NOT override disk; the derivation SHALL share one implementation with `rddf status` Mode A instead of keeping a second copy. | A task-complete change without iteration.json is queued | no `.rddf/state/iteration.json` exists, one change's tasks.md is 100% checked, and the batch verifier queue is scanned | that change is returned as a verification candidate ;; rddf rdd-verify SHALL execute real batch verification | `rddf rdd-verify` SHALL perform AC verification for each eligible change per the self-contained agent protocol (ADR-0045) unless a current valid verdict cache exists. It SHALL persist the verdict, classify failed acceptance criteria, and return a non-success exit code when any change fails, errors, or reaches the retry limit. An empty queue MUST be a successful no-op only when the queue is genuinely empty, and the reason for the emptiness MUST be reported on stderr as a named cause instead of a silent empty list. | An empty queue reports a diagnosable reason | no active change has complete tasks and `rddf rdd-verify --dry-run` runs | it exits 0 with an empty queue and stderr names the cause (no active change / no task-complete change)

## 范围

**In Scope**:

- `_lib/verifier/discovery.py::discover_eligible()`：改为从 disk 推导 —— 扫 `openspec/changes/*/tasks.md`
  + `.rddf/state/builder/<name>.json` + `.rddf/state/verifier/.ac-verdict-<name>.json`，套用现有 `_is_eligible` 规则
  （`tasks_done == tasks_total > 0` 且状态属 `in_worktree` / `completed`）；
- `_lib/cli/rdd_verify_cmd.py`：批量循环的**写回侧**落点决策 —— `update_iteration_summary`（`:496`）在无 iteration.json 时
  写哪（落 `.rddf/state/verifier/` 的 verdict cache = 既有产品侧单一写入者，**不新建**文件）；
- `discover_eligible()` 缺输入时给**可诊断原因**（不再静默 `[]`）；
- 复用 `_lib/cli/status_cmd.py` 的 Mode A 推导逻辑（**同源**，不复制第二份）；必要时把该逻辑抽到共享模块；
- 回归用例：无 iteration.json 的项目里，能被判定 eligible 的 change **出现在** `rddf rdd-verify --dry-run` 输出里。

**Out of Scope**:

- **不**在 P0 创建 iteration.json（推翻归档 AC ⇒ 本提案明确不走这条路）；
- **不**改 `_lib/iteration/**` 与 `phase0_approval.sh` 的登记路径（归档 AC 保持原样）；
- 不改 `_is_eligible` 的判据语义（`tasks_done == tasks_total > 0` 等）—— 只换**推导源**；
- 不改 `rddf status` 的视图（Mode A 已 disk 化，本次只是让 verifier 复用它）。

## 关键场景

1. 项目**无** `iteration.json` + 有 1 个 tasks 全勾的 change ⇒ `rddf rdd-verify --dry-run` 列出它（当前列 0 个）。
2. 项目**有** iteration.json 且与 disk 一致 ⇒ 队列与现状**等价**（无回归）。
3. iteration.json 与 disk **不一致**（陈旧）⇒ 以 **disk** 为准（与 `rddf status` Mode A 同源），并给一行提示（**stderr**，不污染 stdout 视图）。
4. 项目既无 iteration.json 也无 tasks.md ⇒ 队列为空，且 stderr 给出**可诊断**原因（当前静默）。

## 技术约束

- **不得**制造第三个真源：推导逻辑与 `rddf status` Mode A **同源**（抽共享模块或直接复用）；
- 写回侧落点必须是**既有**单一写入者（`.rddf/state/verifier/.ac-verdict-<name>.json`）⇒ 不新建并行状态文件；
- 兼容性：iteratio.json 存在时**行为不变**（回归用例覆盖）；
- 不改归档 AC（`register-change-in-iteration`）的实现与语义。

## 验收标准

- [ ] **AC1（红→绿）** 新增 `tests/unit/test_verifier_discovery_disk.py`：用例「无 iteration.json + tasks 全勾 ⇒ 队列含该 change」
      ⇒ 修复前红（当前 `[]`）⇒ 修复后绿；
- [ ] **AC2（红→绿）** 同文件用例：「无 iteration.json 且无 tasks.md ⇒ 队列为空 **且** 返回可诊断原因（非静默 `[]`）」
      ⇒ 修复前红 ⇒ 修复后绿；
- [ ] **AC3（回归）** 既有 iteration.json 场景的用例**零回归**（`python3 -m pytest tests/unit -k discovery -q` 全绿）；
- [ ] **AC4（单源）** 断言 disk 推导与 `rddf status` Mode A 引用**同一实现** —— 用**对象身份断言**
      （`discovery._derive is status_cmd._derive` 形态），不是「看起来一样」⇒ 不成立即红；
- [ ] **AC5（端到端）** `tests/integration/` 增 1 例：临时项目根内（无 iteration.json）跑 `rddf rdd-verify --dry-run`
      ⇒ 输出含预期 change 名；临时项目根复用既有 bats 模式（`$BATS_TMPDIR` + `git init`，参照
      `tests/integration/test_global_install_external_project.bats`），**不新建**临时项目根 helper；
- [ ] **AC6（变异）** 把推导源改回 iteration.json ⇒ AC1 用例必须红（判别力证明）；
- [ ] **AC7（门）** `./test.sh --gates` 与 `./test.sh --unit` 全绿。

## Capabilities

- MUST: 批量 verifier 分流在**无 iteration.json** 的项目里仍能发现 eligible change。
- MUST: 推导源与 `rddf status` Mode A **同源**（禁第二套实现）。
- MUST: 空结果必须**可诊断**（不得静默 `[]`）。
- MUST NOT: 创建半成品 iteration.json（推翻归档 AC ⇒ 禁止）。
- MUST NOT: 新建与 `.rddf/state/verifier/` 并行的状态文件。

## Impact

| 面 | 影响 |
|---|---|
| `_lib/verifier/discovery.py` | 推导源从 iteration.json 改为 disk |
| `_lib/cli/rdd_verify_cmd.py` | 批量写回落点决策（verdict cache） |
| `_lib/cli/status_cmd.py`（或共享模块） | Mode A 推导逻辑抽出供复用 |
| `.rddf/state/verifier/` | 写回侧既有单一写入者（不新增文件） |
| ADR / 契约 | 与 `4661096a` 方向一致；**不改**归档 AC |
