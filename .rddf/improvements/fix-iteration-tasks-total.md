---
优先级: P1
priority: P1
来源: 2026-11-17 第八批 5 项归档过程发现（follow-up G）——iteration.json 的 tasks_total
  在 v4 丢失了 v3 的写者 ⇒ 「已完成数」被隐藏，且批量验证的发现恒空（eligible 判据要求
  tasks_done == tasks_total > 0）⇒ 归档门只能靠手写 cache 才能过
阶段: phase-2
分类: bugfix
类型: bugfix
状态: draft

生成时间: 2026-11-17
roadmap_ref:
---

# fix-iteration-tasks-total

**主题**: 阶段步骤化执行

## 架构依据

### 这不是新功能，是 v4 丢掉的一环（metis 第 1 轮 P0 指出，本项据此重构）

v3 的 guide-ship **P1 hook 写过 `tasks_total`**：

- `.rddf/plans/extract-guide-ship-inlined-scripts.md:387-391`：
  ```bash
  plan_step_count=$(grep -c '^- \[ \]' "$plan_file" 2>/dev/null || echo 0)
  ```
  该 hook 在写 iteration 时一并写入 `tasks_total`（`:234` 的注释亦列明 `tasks_total`）。
- **v4 stage-merge 把它丢了** ⇒ 生产代码里没有任何地方写 `tasks_total`。
- 而 `tests/integration/test_guide_ship_iteration_hook.py:45-69` **仍在测试里复刻那段死掉的 hook body**（`plan_step_count` → `tasks_total`），**测试仍然通过** ⇒ 仓库里存在一个「已实现」的假信号（`USAGE.md:366` 还把它写成已完成能力）。

⇒ 用户真正要的表述是：**「把 v4 丢掉的那一环补回来，并让那条复刻死契约的测试重新对齐真实实现」**，而不是「设计一个新的写入点」。

### 现在的状态：能力在，写者不在

| 位置 | 行为 |
|---|---|
| `_lib/schemas/iteration_schema.json:79-90` | 定义了 `tasks_done` / `tasks_total`（integer ≥ 0）；`:87` 的描述写「Snapshot at plan generation; **not auto-updated when tasks.md is edited**」—— 但**没有任何代码在 plan generation 时写它**（schema 文档在说谎） |
| `_lib/iteration/store.py:686-695` `set_tasks_done(data, name, done, total=None)` | **能力齐备**（`total` 可选）—— 但硬编码 `kwargs = {"name": name, "status": "in_worktree", ...}` ⇒ **不能直接用**：在 P1 调用会把 P0 刚写的 `proposed` 翻成 `in_worktree`（`phase0_approval.sh` 特意加了「不降级」守卫），在归档回写里调用会把 `archived` **复活**成 `in_worktree` |
| `skills/execute/scripts/execute_step7.py:49` | **唯一的实际写者**（execute 子技能的 step7）—— rdd-builder 的 P1/P2 流程**不走**它 |
| `skills/rdd-builder/scripts/phase1_plan.sh` | 只生成 tasks.md，**不写任何 tasks 字段** |
| `skills/rdd-builder/scripts/phase2_execute.sh` | 只做 worktree 准备 + handoff 写入（末尾无条件写 `execution_status="completed"`），**从不写 tasks 字段** |
| `_lib/iteration/post_archive.py:192-197` | 归档回写只写 `tasks_done`（且是 `if "tasks_done" not in existing` 的守卫下），**从不写 `tasks_total`** |
| `skills/reconcile-iteration.sh:114-116` | 另一个既有写者：`total = c.get("tasks_total", 0); c["tasks_done"] = total` ⇒ **缺 total 时把 done 清零** |

⇒ **只补 `tasks_total` 不修主因**：在 builder 路径里 `tasks_done` 同样没人写（归档回写只能捡一次），所以 eligible 判据仍然不成立。

### 两个后果（主次分明）

**后果一（主因）：质量门不可达。**
`_lib/verifier/discovery.py:19-29` 的 eligible 判据：

```python
if status in _IMPLEMENTED:      # {in_worktree, completed}
done = change.get("tasks_done") or 0
total = change.get("tasks_total") or 0
if total <= 0:  return False
return done == total
```

`tasks_total` 缺失 ⇒ `total = 0` ⇒ **一律 ineligible** ⇒ 批量 `rddf rdd-verify` **发现恒空** ⇒ rdd-verifier 根本不会跑 ⇒ 归档门（`_lib/archive.sh:536-557`，fail-closed）报「no valid verdict cache」⇒ **只能手写 cache 或开 `SKIP_RDD_VERIFIER` 旁路**。

**实测（临时 fixture）**：

```
changes: [ {no-total: in_worktree, tasks_done: 4},
           {with-total: in_worktree, tasks_done: 4, tasks_total: 4} ]
discover_eligible() → ['with-total']        ← no-total 被静默跳过
```

**本批 5 项归档时就是手工写的 verdict cache** —— 缺的这一环**每次都在被人肉补**。

而 `rddf rdd-verify` 在空队列时打印「No eligible changes…」并**返回 0**（`_lib/cli/rdd_verify_cmd.py:470-472`）⇒ 空队列看起来像成功。

**后果二（次要）：状态视图说谎。**
`rddf status` 的渲染（`_lib/cli/status_cmd.py:244-253`）是 `if tasks_total > 0: … else: tasks_disp = "-"` ⇒ **`tasks_total` 缺失时，连 `tasks_done` 也不显示**。
实测：`rddf status fix-flow-drift-batch-1` → `Tasks: -`（实际已完成 4 个 task）。

### 三处必须先定下来的口径（否则实现必然漂移）

1. **计数口径不统一**：仓里至少 5 套实现 ——
   `_lib/iteration/post_archive.py:71`（regex，忽略大小写）、`skills/execute/scripts/execute_step7.py:36-41`（`startswith("- [x]")`）、`_lib/discover_ship_changes.py:82`（`text.count("- [ ]") + done`）、`skills/rdd-doctor/scripts/checks/tasks_checkbox_check.py:68-70`（`text.count("- [x]")`，**区分大小写**）、`_lib/iteration/archive_sidecar.py:29-35`（**自称 canonical**：case-insensitive regex）。
2. **`done == total` 会在「中途加 task」时变成永久 ineligible**：total 是 P1 快照、done 继续涨 ⇒ `done > total` ⇒ 判据失败 ⇒ 该 change 永远不进 verify 队列，而 `rddf status` 显示 `7/5`（比现在的 `-` 更难诊断）。
3. **归档后 tasks.md 会被替换成 skeleton**：`archive_sidecar.write_tasks_md_sidecar`（`:38-61`）把原文件挪到 `tasks.md.archived-snapshot`、写入无 checkbox 的 skeleton；而 `_lib/archive.sh:682-691` 的顺序是在 `mark_iteration_archived` **之后**跑 ⇒ 之后重放 `rddf archive-sync`（`archive_sync_cmd.py:96` → `sync_iteration_after_archive`）会读到 skeleton ⇒ **把好的 done/total 覆盖成 0**。

## 范围

- **In Scope**：① P1（`phase1_plan.sh`，tasks.md 落地后）写 `tasks_total` 快照（**不改 status**）；② P2 完成时新增一次写回，写 `tasks_done` + 按当前 tasks.md 重算 `tasks_total`（这是让 eligible 真正成立的**唯一**写入点）；③ `store.set_tasks_done` 增加可选 `status` 参数（默认仍 `in_worktree`，保住 `tests/unit/test_iteration.py:153` 的既有断言）；④ 归档回写同时写 `tasks_total`，并**拆开** `tasks_done` / `tasks_total` 的两个守卫；⑤ 计数优先读 `tasks.md.archived-snapshot`；⑥ 计数口径收敛到一处（扩 `archive_sidecar.count_done_tasks` → `count_tasks(text) -> (done, total)`）；⑦ `iteration_schema.json:87` 的 description 改成与实现一致；⑧ `tests/integration/test_guide_ship_iteration_hook.py` 重连到真实实现或删除。
- **Out Scope**：**不改 eligible 判据的放宽方向**（`done == total` 保留为语义，靠「每次重算 total」消除 `done > total`）；不追溯回填存量条目（见 Impact 的存量说明）；不改 `SKIP_RDD_VERIFIER` / `FEATURE_ARCHIVE_GATE` 语义；不改 `reconcile-iteration.sh` 的既有行为（**记一条 follow-up**，见 AC）；不新建「task 计数模块」（扩既有 `archive_sidecar` 即可）；不改 rdd-quick 的流程（只加 skip 语义）。

## Why

真正的用户问题不是「状态视图显示 `-`」，而是：**归档门声称「没验证过」，而验证确实做过** —— 用户于是只能手写 cache 或开旁路。`Tasks: -` 只是同一根因的可见症状。

本批 5 项归档时**全部手工写了 verdict cache**，而且不止一次 —— 这说明缺的不是某个字段，是**流程里少了一环**。补上这一环之后，「下次归档不要再手工写 JSON / cache」才成立。

第二层：schema 文档（`:87`）宣称字段在 plan generation 时被快照，却没有任何代码这么做 ⇒ 下一个读 schema 的人会照着写（或以为已经写了）。

## What Changes

1. **P1 快照**（`skills/rdd-builder/scripts/phase1_plan.sh`，tasks.md 落地后）：写 `tasks_total`（按 tasks.md 的 task 条目数），**不得改 status**（保持 P0 写的 `proposed`）。
2. **P2 完成写回**（**新增**，`skills/rdd-builder/scripts/phase2_execute.sh` 的 handoff 写入之后）：写 `tasks_done` + 按**当前** tasks.md 重算 `tasks_total` ⇒ 实施完成后 `done == total` 自然成立 ⇒ eligible 成立。
   - 这是**唯一**能让批量发现不再恒空的写入点（只在 P1 写 total 时，`done` 仍缺 ⇒ 仍 ineligible）。
3. **`set_tasks_done` 加 `status` 参数**（`_lib/iteration/store.py:686`）：`status: Optional[str] = None`，默认仍写 `in_worktree`（保住 `tests/unit/test_iteration.py:153` 的「有 tasks_done 就必须是 in_worktree」断言）；P1 传「不改 status」的哨兵；**归档回写不调它**，继续用 `add_or_update_change(status="archived", tasks_done=…, tasks_total=…)`（`post_archive.py:181-205` 已是这个形状）。
4. **归档回写拆守卫**（`_lib/iteration/post_archive.py:192-197`）：`tasks_done` 与 `tasks_total` **各自** `if not in existing`（否则已有 done 的条目永远补不上 total）。
5. **计数优先读 sidecar**：`tasks.md.archived-snapshot` 存在时用它，否则用 `tasks.md` ⇒ archive-sync 重放不再把 done/total 归零。
6. **计数口径收敛**：扩 `_lib/iteration/archive_sidecar.py::count_done_tasks` → `count_tasks(text) -> (done, total)`，并把 5 个调用点改为使用它：`post_archive.py:71`、`execute_step7.py:36-41`、`_lib/discover_ship_changes.py:82`、`skills/rdd-doctor/scripts/checks/tasks_checkbox_check.py:68-70`、`archive_sidecar.py:35`。
   - ⚠ 计数口径必须能识别 `phase1_plan.sh` 生成的 `- [ ] ### Task <title>` 格式（**task 数 ≠ 条目数**：条目数是 checkbox 行数，task 数是 `### Task` 行数 ⇒ 两者取其一并在 AC 里写死）。
7. **schema 描述改成与实现一致**（`_lib/schemas/iteration_schema.json:87`）：从「plan generation 时快照、不随 tasks.md 更新」改为「每次写回时按当前 tasks.md 重算」。
8. **死契约测试重连或删除**：`tests/integration/test_guide_ship_iteration_hook.py`（复刻 v3 hook body 的绿测试）⇒ 要么真 source 真实实现，要么删除并在 AC 里说明「v3 契约由 <新测试> 继承」。否则它继续给「已实现」的假信号。
9. **skip 语义**：
   - rdd-quick（无 openspec change / 无 tasks.md）⇒ **skip-on-missing**，不创建幽灵条目（沿用 `store.py:718-740` `set_deps_info` docstring 里已付过的学费）；
   - `total == 0`（tasks.md 只有标题、生成失败）⇒ **不写**，不把「未知」写成 0；
   - lightweight 路径（`phase3_archive.sh:135-145` 的 KNOWN GAP：归档回写根本不跑）⇒ 本项对 lightweight 归档**无效**，该缺口归 `fix-execution-mode-decision` 收口（见该草案 AC）。
10. **存量条目的显示口径**（只读，不回填）：`tasks_total` 缺失时显示 `4/-`（**done 仍可见**），而不是现在的 `-` ⇒ 状态视图不再说谎。doctor 的提示落到**既有 `state` 类目**（`skills/rdd-doctor/scripts/checks/state_schema_check.py`，它已在校验 `iteration.json ⊆ iteration_schema.json`），**WARNING 不进 CRITICAL**。
11. **第二份 eligible 判据同步**：`skills/rdd-verifier/scripts/scan_queue.sh:20-28` 与 `_lib/verifier/discovery.py:19-29` 两处必须同步（若判据有变）。

## Acceptance

- [ ] P1（`phase1_plan.sh`）在 tasks.md 落地后写 `tasks_total` 快照，且**不改变 status**（`proposed` 不被翻成 `in_worktree`）
- [ ] P2 完成时新增一次写回：`tasks_done` 与 `tasks_total` 同时写入，且 `done == total` ⇒ `discover_eligible(root)` 返回该 change（fixture 实测断言：P1 之后返回 `[]`，P2 之后返回 `[<change>]`）
- [ ] `store.set_tasks_done` 增加可选 `status` 参数（默认仍 `in_worktree`）；`tests/unit/test_iteration.py:153` 的既有断言仍绿；**归档回写不调它**（对 `archived` 条目调用后 status 仍为 `archived`，有专门断言）
- [ ] 归档回写同时写 `tasks_total`，且 `tasks_done` / `tasks_total` 是**两个独立守卫** ⇒ 已有 done 的条目也能补上 total
- [ ] 计数优先读 `tasks.md.archived-snapshot` ⇒ **归档后再重放 `rddf archive-sync`，done/total 不被归零**（两条路径下 `done == total` 都成立）
- [ ] 计数口径收敛到 `archive_sidecar.count_tasks(text) -> (done, total)`，5 个调用点全部改用它；`done` 与 `total` 同源（都由 tasks.md 现算）⇒ 不会出现 `done > total`
- [ ] `iteration_schema.json:87` 的 description 与实现一致（不再宣称「plan generation 快照、不更新」）
- [ ] `tests/integration/test_guide_ship_iteration_hook.py` 已重连到真实实现或已删除，且有说明（不得继续复刻死契约）
- [ ] rdd-quick 路径（无 tasks.md）⇒ skip，不创建幽灵条目；`total == 0` ⇒ 不写
- [ ] `rddf status` 对缺 `tasks_total` 的条目显示 `4/-`（done 可见），不再显示 `-`；对有 total 的显示 `4/4`
- [ ] doctor 的提示落在既有 `state` 类目（不新建 category），且为 WARNING 不进 CRITICAL
- [ ] 幂等：重跑 P1 / P2 不把 `in_worktree` 打回 `proposed`、不覆盖已写的 done
- [ ] `skills/rdd-verifier/scripts/scan_queue.sh` 与 `_lib/verifier/discovery.py` 两份 eligible 判据同步
- [ ] `./test.sh --unit` + `./test.sh --full --regression` 全绿（per AGENTS.md 归档前强制门）

## Capabilities

- 批量 `rddf rdd-verify` 能发现到「任务已做完」的 change ⇒ rdd-verifier 恢复为**默认会跑**
- 归档门不再因为「cache 没人生成」而要求人工介入 ⇒ **下次归档不必手写 cache / 手改 iteration.json**
- `rdcf status` / dashboard 显示真实任务进度，缺字段时也显示 done（`4/-` 而非 `-`）
- 「哪个字段由谁写、什么时候写、按什么口径算」全部有唯一答案，v3 丢掉的那一环被补回

## Impact

- **影响面**：`skills/rdd-builder/scripts/phase1_plan.sh`、`skills/rdd-builder/scripts/phase2_execute.sh`（新增一次写回）、`_lib/iteration/store.py`（`set_tasks_done` 加参数）、`_lib/iteration/post_archive.py`（守卫拆分 + sidecar 优先 + 写 total）、`_lib/iteration/archive_sidecar.py`（扩成 `count_tasks`）、`_lib/schemas/iteration_schema.json`（description）、`_lib/cli/status_cmd.py`（`4/-` 显示）、`skills/rdd-doctor/scripts/checks/state_schema_check.py`（提示）、`_lib/verifier/discovery.py` + `skills/rdd-verifier/scripts/scan_queue.sh`（若判据有变）、5 个计数调用点、`tests/integration/test_guide_ship_iteration_hook.py`。
- **风险**：
  - **`set_tasks_done` 的 status 语义**是本项最危险的一处：默认仍是 `in_worktree`，任何新调用方都可能把 `proposed`/`archived` 覆盖掉 ⇒ 必须有「不改 status」的显式哨兵 + 断言。
  - `done` 改为「按 tasks.md 现算」后，任何**手工**改 tasks.md 而不重跑写回流程的场景会短暂不一致 ⇒ doctor 的 `state` 提示负责暴露它。
  - 写回是 read-modify-write（`store.save` 有锁但无版本校验）⇒ 与 execute step7 并发写可能丢更新 ⇒ 本项不解决并发（记 follow-up），但 AC 要求幂等不回归。
- **兼容性**：iteration.json 的**字段不变**（`tasks_done` / `tasks_total` 早已在 schema 里）；`store.set_tasks_done` 的默认行为不变（仅新增可选参数）；既有单测（`test_iteration.py:153`）保持绿。
- **存量**（本仓 `.rddf/state/iteration.json` 25 条）：5 条 `done == total`（本批手工写的）、4 条 `archived` 且完全无 tasks 字段、1 条 `4/None` ⇒ **本项不回填**，这 10 条会长期处于残缺状态；可见性由「`4/-` 显示 + doctor `state` 提示」提供；**回填脚本另开 follow-up**。
- **既有冲突（记 follow-up，本项不改）**：`skills/reconcile-iteration.sh:114-116` 会把缺 `tasks_total` 的条目的 `tasks_done` **清零** ⇒ 它会与本项的修复相互抵消（在本项落地后执行 reconcile 仍会清零）。
- **依赖**：与本批第 4 项（`register-change-in-iteration`，已归档）互补 —— 第 4 项让条目**存在**，本项让字段**完整**；与 `fix-execution-mode-decision` 的 lightweight 缺口互为参照（lightweight 路径的归档回写不跑 ⇒ 本项对它无效）。

## 审稿记录

metis 1 轮（2026-11-17）。逐条处置：

- **采纳 P0-1（本项是 v4 丢失的能力，不是新功能）**：原草稿把「补 `tasks_total`」当成新增能力设计。已据 `.rddf/plans/extract-guide-ship-inlined-scripts.md:387-391`（v3 的 `plan_step_count`）重写「架构依据」，并新增「死契约测试 `test_guide_ship_iteration_hook.py` 必须重连或删除」一条（它复刻已无生产实现的 hook body 却仍然绿，是假信号）。
- **采纳 P0-2（只补 total 不修主因）**：原草稿的写入点写成了「P1/P2 或归档」三选一。已改为二元结构：**P1 只写 total 快照**（不改 status）+ **P2 完成时写 done 与重算 total**（唯一能让 eligible 成立的写入点），并在 Why 里写明「只补 total 不补 done ⇒ 主因不修」。
- **采纳 P0-3（`set_tasks_done` 硬编码 `status: "in_worktree"`）**：原草稿称「能力齐备」是错的 —— 直接调用会在 P1 把 `proposed` 翻成 `in_worktree`、在归档回写把 `archived` 复活。已改为「加可选 `status` 参数（默认仍 `in_worktree`）+ 归档回写不用它、改用 `add_or_update_change`」，并加专门断言。
- **采纳 P0-4（post_archive 的守卫与 sidecar）**：原草稿只说「同时写 total」。已拆成两个独立守卫（否则已有 done 的条目永远补不上 total），并加「计数优先读 `tasks.md.archived-snapshot`」⇒ archive-sync 重放不再把好数据归零。
- **采纳 P0-5（`done == total` vs `done >= total` 必须决策）**：原草稿把判据「供着不动」。已决策：**保留 `done == total`（不放宽）**，靠「每次写回按当前 tasks.md 重算 total」从源头消除 `done > total`（done 与 total 同源），并同步修正 schema 的 description。
- **采纳 P1-5（AC 二分 + 删掉二选一）**：原 AC「显示 `4/4`（或 `archived (snapshot 4/4)`）」不可判定。已拆成「新流程 AC」与「存量/显示 AC」（缺 total 固定显示 `4/-`），并删掉所有「（或 …）」与「可选/若成本高可降级」。
- **采纳 P1-6（点名 canonical 计数器）**：已指定扩 `archive_sidecar.count_done_tasks` → `count_tasks(text) -> (done, total)`，并列出 5 个待收敛的调用点；同时注明「task 数 ≠ 条目数」的口径必须写死。
- **采纳 P1-7（doctor 不新建 category）**：原草稿写「doctor 的某个 category」是含糊且倾向新建。已改为落到既有 `state` 类目，WARNING 不进 CRITICAL。
- **采纳 P1-8（skip 语义 + lightweight 缺口）**：已补 rdd-quick 的 skip-on-missing、`total == 0` 不写、lightweight 路径归档回写不跑（本项对它无效，归 `fix-execution-mode-decision`）。
- **采纳 P1-9（死契约测试）**：已列为 What Changes 第 8 条 + AC。
- **采纳 P1-10（幂等 + 两份判据同步）**：已加入 AC。
- **采纳 P2-11（存量只读诊断入口 + `reconcile-iteration.sh` 的冲突）**：已写入 Impact，并明确「回填脚本另开 follow-up」「`reconcile-iteration.sh:114-116` 会把缺 total 的条目 done 清零 ⇒ 与本项相互抵消，记 follow-up」。
- **采纳 P2-12（测试门升级）**：AC 测试段已加 `./test.sh --full --regression`。
- **采纳（主次分明）**：原草稿把「视图说谎」与「发现恒空」并列。已明确**主因是质量门不可达**，「`Tasks: -` 只是症状」；并补上「空队列时 `rddf rdd-verify` 返回 0 ⇒ 看起来像成功」这一失真。

## 立项核查（2026-11-17，planner）

| 断言 | 核实结果 |
|---|---|
| `tasks_total` 无写者（schema 说 "Snapshot at plan generation; not auto-updated"） | ✅ `iteration_schema.json:85-87` 原文如此；`grep tasks_total` 全是读者，无写者 |
| `set_tasks_done` 硬编码 `status: "in_worktree"` | ✅ `_lib/iteration/store.py:693` `kwargs = {"name": name, "status": "in_worktree", ...}` ⇒ 对 `archived` 条目调用会打回 `in_worktree` |
| `set_tasks_done` 已有 `total` 可选参数 | ✅ 签名 `(data, name, done, total=None)` ⇒ 本项只需加 `status` 参数 |
| `archive_sidecar.count_done_tasks` 只返 done | ✅ `:29` `-> int`（本项要扩成 `count_tasks -> (done, total)`） |
| 5 个计数调用点存在且口径不一致 | ✅ **逐个验过**：`post_archive.py:71` 与 `archive_sidecar.py:35` 用 `re.findall(r"^\s*-\s*\[x\]\s", IGNORECASE)`；`discover_ship_changes.py:82` 用 `text.count("- [ ]")` 子串；`execute_step7.py:36` 手写 split 循环；`tasks_checkbox_check.py:68` 用自有常量 |
| rdd-quick 路径无 tasks.md | ✅ 与立项的 skip 要求一致 |
| `tests/unit/test_iteration.py` 有 `set_tasks_done` 断言 | ✅ 存在 |

> 附带实测：`openspec/changes/` 下缩进子项 checkbox 存在（如 `  - [ ] check_proposal_length(...)`），
> 而 `text.count("- [ ]")` 的子串匹配会**计入**它们，`^\s*-\s*\[x\]\s` 正则也会计入 ——
> 两者对「缩进子项算不算 task」的判定相同，但对 `- [ ]` 与 `-[ ]`（无空格）的判定不同。
> 收口到单一 `count_tasks` 后此歧义消失。
