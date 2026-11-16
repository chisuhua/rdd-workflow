---
优先级: P2
priority: P2
来源: 2026-11-16 rddf-layout-manifest 归档过程发现（follow-up F-6）——rdd-builder 创建的 change
  从不注册进 iteration.json，rddf status / 归档 sync 都取不到条目
阶段: phase-2
分类: bugfix
类型: bugfix
状态: approved
approved_at: 2026-11-16
approved_by: rdd-planner
review_notes: "metis 1 轮（2026-11-16，5 份合并调用，每份 1 轮在预算内）；4 处 P0 采纳并重写草案，逐条处置见正文「## 审稿记录」；7 段 + 主题校验 PASS；已 attach 到 阶段步骤化执行/phase-2"

生成时间: 2026-11-16
roadmap_ref:
  project_id: 阶段步骤化执行
  phase: phase-2
---

# register-change-in-iteration

**主题**: 阶段步骤化执行

## 审稿记录

metis 1 轮（2026-11-16，planner 阶段 gap 分析）。逐条处置：

- **采纳 P0-5（AC 口径纠偏，最重要）**：原 AC「`rddf doctor --category roadmap-feature` 不再报
  CRITICAL」不可满足 —— 该 category 的 CRITICAL 判据是
  `roadmap_feature_check.py:181-197` 的「active feature 不在 `feature_view`」与 `:326-350` 的
  AGENTS.md 哨兵，与 `changes[]` 无关（实测未注册 change 期间 `All 1 categories OK`）。
  已改为 `rddf status` 能列出该条目 + `sync_iteration_after_archive` 不再返回 missing warning
  （两条均经临时 change 目录实测复现）。
- **采纳（复用既有 API，不新建模块）**：`store.py:677 set_status` 的 docstring 明写
  「creates the entry if missing」⇒ 删掉新建 `_lib/iteration/register.py` 的提案。
- **采纳（测试隔离）**：`tests/integration/test_rdd_builder_phases.bats:86-89` 在仓库本体跑 P0
  approve ⇒ 加注册后会污染真实 `iteration.json`。已把「改造该用例为临时项目根」写入 What Changes，
  并加 AC「跑完整套 bats 后仓库本体 iteration.json 内容不变」。
- **采纳（choice=5 不得写）**：`phase0_approval.sh:132-135` 可能 auto-pick dispatch-quick ⇒ 调用点
  限定在 `case 1)`，并加 AC。
- **采纳（缺失时不创建半成品）**：`iteration.json` 缺失 / 损坏 / 锁超时 ⇒ 只 WARN，且不得用
  `store.create_empty` 落半成品文件。
- **记录未采纳**：`parent_feature` 推断与 `feature_view` 重算 —— 属另一件事（feature 视图层面可见），
  本项 Out Scope 明示。

## 架构依据

`iteration.json` 是 `rddf status` / `rddf feature` / deps 分析的共同数据源，但**没有任何写者负责创建条目**：

- `_lib/iteration/post_archive.py:103 sync_iteration_after_archive` —— 只在**已存在**条目上更新；
  条目缺失时返回 warning（`:162-168`：`"change '<name>' missing from iteration.json"`），**不新增**。
- `_lib/iteration/repair.py::force_mark_archived` —— 同样是「已存在条目的兜底修正」，不创建。
- `_lib/iteration/store.py:677 set_status` —— docstring 明写 *"creates the entry if missing"*，
  内部走 `add_or_update_change`（`:632`，按 name 合并、保留 `added_at`、不会重置未传字段）。**能力已存在**。

⇒ 缺的不是能力，而是**调用者**：rdd-builder 从 P0 建 change 到 P2 实施完成，全程不写 `iteration.json`。

**实测症状（本仓，用临时 change 目录 `openspec/changes/_probe_unreg` 复现）**：

- `rddf status _probe_unreg` → `❌ change '_probe_unreg' not found`（即便 change 目录存在）
- `mark_iteration_archived _probe_unreg` →
  `change '_probe_unreg' not found in iteration.json AND no archive dir on disk; archive sync skipped`
- 也就是说：状态视图看不到该 change，归档时的 iteration 回写被跳过。

**一处需要纠正的既往判断**：这不影响 `rddf doctor --category roadmap-feature`。该 category 的 CRITICAL
判据是「active feature 不在 `iteration.json.feature_view`」与「AGENTS.md 哨兵段过期」
（`skills/rdd-doctor/scripts/checks/roadmap_feature_check.py:181-197` / `:326-350`），与
`changes[]` 无关 —— 实测未注册 change 期间 `roadmap-feature` 仍为 `All 1 categories OK`。
若要让 feature 视图层面也可见，属另一件事（`feature_view` 需由
`skills/feature/scripts/feature_view.py::update_iteration_feature_view` 重算，且分组依赖
`parent_feature`），不在本项范围。

## 范围

- **In Scope**：在 P0 approve 成功路径上补一次 `changes[]` 注册（复用既有 `set_status` / `add_or_update_change`）；幂等；`iteration.json` 缺失/损坏/锁超时时只 WARN 不阻断；测试隔离（现有 bats 在仓库本体跑 P0）。
- **Out Scope**：不新建 `_lib/iteration/register.py`（能力已存在，见「架构依据」）；不改 `sync_iteration_after_archive` / `force_mark_archived`；不重算 `feature_view`；不实现 `parent_feature` 推断；不处理 rdd-quick（`choice=5`）路径；不回填历史缺失条目。

## Why

归档侧有 sync、有 repair、有兜底，创建侧什么都没有 —— 补齐成本极低（一处调用），但缺失的代价在每个
新 change 上重复：状态视图缺条目、归档回写被跳过、deps 分析看不到它，且每次都要人手工编辑
`.rddf/state/iteration.json`。

手工补不可持续：补的人必须知道 schema（`status` 取值域、`tasks_total` 来源要跟 tasks.md 一致），还得
避免覆盖既有 `tasks_done`。这类知识应只存在于一个函数里 —— 而那个函数**已经写好了**，只是没人调。

## What Changes

1. **复用既有 API**：在 `skills/rdd-builder/scripts/phase0_approval.sh` 的 `case 1)`（approve 成功、
   proposal 落盘之后）加一次注册调用，经 python 侧 `_lib/iteration/store.py::set_status(data, name,
   "proposed")` + `save()`（等价于 `add_or_update_change(name=..., status="proposed")`）。
   **不新建模块、不加新 schema 字段**。
2. **幂等**：`add_or_update_change` 按 name 合并且 `merged.update(fields)` 只覆盖传入字段 ⇒
   重复 approve 不会产生重复条目、不会重置 `tasks_done` / `archived_at` / `archive_commit_sha`。
   AC 需显式断言这一点，不靠「读代码推出来」。
3. **失败只 WARN**：`iteration.json` 缺失 / 损坏 / `FileLockedError` 时打印 stderr WARN 并继续，
   **不得**创建半成品文件（`store.create_empty` 在缺失时只报错不落盘）。
4. **测试隔离**：`tests/integration/test_rdd_builder_phases.bats:86-89` 在**仓库本体**跑
   `phase0_approval.sh test-change`；加入注册后这条用例会把 `test-change` 写进真实的
   `.rddf/state/iteration.json`。必须把该用例改造成临时项目根（`RDDF_PROJECT_ROOT`），并在 AC 里断言
   「跑完整套 bats 后仓库本体的 `iteration.json` 内容不变」。
5. **调用位置限定在 `case 1)` 内**：`phase0_approval.sh:132-135` 可能 auto-pick `choice=5`
   （dispatch-quick，不建 openspec change）⇒ 该分支不得写 `iteration.json`。

## Acceptance

- [ ] 新 change 经 P0 approve（`choice=1`）后，`rddf status <name>` 能列出该条目（此前为 `not found`）
- [ ] 同场景下 `mark_iteration_archived` / `sync_iteration_after_archive` 不再返回
      `"missing from iteration.json"` warning
- [ ] 重复 approve 幂等：无重复条目，`tasks_done` / `archived_at` / `archive_commit_sha` / `added_at` 不被重置
- [ ] `iteration.json` 缺失 / 损坏 / 锁超时时只输出 stderr WARN，P0 approve 仍成功（exit 0）
- [ ] `iteration.json` 缺失时**不创建**半成品文件（断言文件仍不存在）
- [ ] `choice=5`（dispatch-quick）路径不写 `iteration.json`
- [ ] 跑完 `tests/integration/test_rdd_builder_phases.bats` 后仓库本体 `.rddf/state/iteration.json` 内容不变
      （用例已改造为临时项目根）
- [ ] `sync_iteration_after_archive` / `force_mark_archived` 既有行为不回归（`./test.sh --unit` 全绿）
- [ ] `rddf doctor --category roadmap-feature` 与 `--category state-schema` 均无新增 finding

## Capabilities

- change 从创建起就进入 `iteration.json`，`rddf status` / `rddf feature` / deps 视图一致
- 归档时的 iteration 回写不再因「条目缺失」被跳过
- 不再需要手工编辑 `.rddf/state/iteration.json`
- 「创建」与「归档」两侧各有唯一写入口，且复用同一 store API

## Impact

- **影响面**：`skills/rdd-builder/scripts/phase0_approval.sh`（一处调用）+ pytest/bats（含改造既有用例）。
  不新增模块、不改 schema。
- **风险**：若 P0 阶段 `tasks_total` 尚不存在（tasks.md 由 P1 生成），条目初始 `tasks_total` 缺省 ——
  需确认 `rddf doctor --category state-schema` 与 deps 分析不因缺省字段报错（实施时先读这两个判据）。
- **测试污染风险（已知）**：现有 P0 bats 在仓库本体跑，本项必须同时改造它，否则会重新引入
  `feat-fix-test-isolation-and-hygiene` 已清掉的污染。
- **兼容性**：纯新增写入口，schema 不变；历史缺失条目不回填（由 `force_mark_archived` 兜底）。
