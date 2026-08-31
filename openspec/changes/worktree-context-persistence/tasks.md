# Tasks for worktree-context-persistence

> TDD 5 步结构: 写失败测试 → 验证失败 → 实现 → 验证通过 → commit. 遵循 rdd-workflow 通用纪律.

## 1. `skills/guide-ship/SKILL.md` 新增 Worktree Context Rule 段

- [x] **1.1 写失败的内容审查 test** (bats): `test_worktree_context_rule_in_guide_ship` 断言 SKILL.md 含 "Worktree Context Rule" 段,且提到 (a) 同一 wt 内省略 cd (b) 跨 wt 切换显式 cd
- [x] **1.2 验证 test fail**
- [x] **1.3 编辑 SKILL.md**:在 Phase 1 (plan) 与 Phase 2 (execute) 各插入 12-15 行段(标题 "Worktree Context Rule");内容含 3 个 do / 1 个 don't 表格
- [x] **1.4 验证 test pass**
- [x] **1.5 commit**: `docs(guide-ship): add Worktree Context Rule section in Phase 1 & 2`

## 2. `skills/execute/SKILL.md` 同步增加同段

- [x] **2.1 写失败的内容审查 test**: `test_worktree_context_rule_in_execute` 同上, 但查 `skills/execute/SKILL.md`
- [x] **2.2 验证 test fail**
- [x] **2.3 编辑 execute SKILL.md**:在 Phase 1 (worktree detect) 与 Phase 2 (run plan steps) 各加同段
- [x] **2.4 验证 test pass**
- [x] **2.5 commit**: `docs(execute): mirror Worktree Context Rule from guide-ship`

## 3. `_lib/archive.sh` 末尾追加 `cd <main_root>`

- [x] **3.1 写失败的 bash test** (bats): `test_archive_exits_in_main_repo` 跑 `archive_change` 完整流程,断言进程 cwd == main_repo_root
- [x] **3.2 验证 test fail** (断言失败原因: cwd 还在 wt/)
- [x] **3.3 修改 archive.sh**:在 `archive_change` 函数 exit 0 之前(所有 cleanup 之后)插入 `cd "$MAIN_REPO_ROOT" || true`
- [x] **3.4 验证 test pass**
- [x] **3.5 commit**: `fix(archive): cd back to main_repo_root at function exit`

## 4. `tests/integration/test_worktree_context_persistence.bats` 端到端 cd 计数

- [x] **4.1 编写 happy path test**:模拟"1 change 走完 5 阶段",通过环境 stub 拦截 bash 调用序列,统计 cd 数
- [x] **4.2 验证 test fail** (基线 cd 数 ~39, 不满足 < 20)
- [x] **4.3 复测 happy path**:重跑 1 change 5 阶段全流程, 收集实际 cd 数 → 修直到 < 20
- [x] **4.4 添加第 2 个 test case**: 一个 worktree 内连续命令(skip cd)
- [x] **4.5 验证 2 个 test pass**
- [x] **4.6 commit**: `test(wt-context): add 5-phase e2e cd-count assertion`

## 5. 文档化 + Review

- [x] **5.1 更新 `.rddf/state/iteration.json`**:status proposed → ready_for_review
- [x] **5.2 在 PR description 中 link proposal.md + AC 4 项**
- [x] **5.3 通知 1 名 reviewer**
