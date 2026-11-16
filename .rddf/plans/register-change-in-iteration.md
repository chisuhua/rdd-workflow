# register-change-in-iteration Implementation Plan

**Goal:** rdd-builder P0 approve 成功后把该 change 注册进 `iteration.json.changes[]`，使 `rddf status` / `rddf feature` / deps 视图与归档侧 sync 都能看到它。

**Architecture:** 不新建模块 —— `_lib/iteration/store.py:677 set_status` 的 docstring 明写 "creates the entry if missing"，`add_or_update_change` 按 name 合并且只覆盖传入字段（幂等）。本 change 只补**调用者**：`phase0_approval.sh` 的 `case 1)` 在 proposal 落盘后调一次；`iteration.json` 缺失/损坏/锁超时只 WARN，P0 仍成功（且不创建半成品文件）。`choice=5`（dispatch-quick，不建 change）不写。

## File Structure

| File | 类型 | Responsibility |
|---|---|---|
| `skills/rdd-builder/scripts/phase0_approval.sh` | 改 | `case 1)` 末尾加注册调用（python 内联，复用 store.set_status + save） |
| `tests/integration/test_phase0_iteration_register.bats` | 新 | 注册后 `rddf status` 可见；幂等（不重置 tasks_done/archived_at）；iteration.json 缺失 ⇒ WARN + 仍 exit 0 + 不创建文件；choice=5 不写 |
| `tests/integration/test_rdd_builder_phases.bats` | 改 | `phase0: approve writes spec.md` 用例改造为临时项目根（当前它在仓库本体跑，会污染真实 iteration.json） |

### Task 1: 注册调用（TDD）

- [ ] 测试先行：fixture 临时项目根 + `iteration.json`（空 changes）⇒ 跑 `phase0_approval.sh` `choice=1` ⇒ `changes[]` 出现该 name、`status=proposed`。
- [ ] 实现：`case 1)` 在写 proposal/spec 之后插入 python 块：`store.load` → `store.set_status(data, name, "proposed")` → `store.save`；异常/缺失 ⇒ stderr WARN，不改变退出码。

### Task 2: 幂等与不破坏既有字段

- [ ] 测试：先手工把条目设为 `tasks_done=3, archived_at=...`，再跑一次 approve ⇒ 字段保留、无重复条目。

### Task 3: 缺失 / 损坏 / choice=5

- [ ] 测试：`iteration.json` 不存在 ⇒ 输出 WARN、exit 0、文件仍不存在；`choice=5` ⇒ 不写 iteration.json。

### Task 4: 测试隔离 + 全量回归

- [ ] 改造 `test_rdd_builder_phases.bats::phase0: approve writes spec.md`：用临时项目根（`RDDF_PROJECT_ROOT`），并加断言「跑完该文件后仓库本体 iteration.json 内容不变」。
- [ ] `./test.sh --bats --regression`（主仓基线：已知 11 / 新增 0）+ `pytest -k "iteration or approve"` + doctor `roadmap-feature` / `state-schema`。
