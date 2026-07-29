# Guide-ship quick finish path for near-complete changes — 实施任务

## Task 1: 在 `ship_plan.sh` 中添加 `detect_quick_finish()` 函数

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_ship_quick_finish.bats`，定义 `detect_quick_finish()` 的行为：
   - 当 tasks.md 中有 1 个 trivial 任务（如 `[ ] update proposal-suggestions.md`）时，输出 `quick_finish`
   - 当 tasks.md 中有 2 个 trivial 任务时，输出 `quick_finish`
   - 当 tasks.md 中有 3 个 trivial 任务时，输出 `standard`（超过阈值）
   - 当 tasks.md 中有 1 个非 trivial 任务（如 `[ ] implement new feature`）时，输出 `standard`
   - 当 tasks.md 不存在时，输出 `no_tasks` 并返回 1
   - 当存在未提交的代码变更时，输出 `standard`
2. 验证测试失败（函数不存在）
3. 在 `skills/guide-ship/scripts/ship_plan.sh` 中实现 `detect_quick_finish()`：
   - 读取 tasks.md 中所有 `[ ]` 开头的任务行
   - 匹配 trivial 关键词：`update`, `proposal`, `suggestion`, `doc`, `status`, `changelog`, `readme`, `md`, `bump`, `version`, `release`, `note`
   - 匹配非 trivial 关键词（任一匹配即阻止）：`implement`, `add`, `create`, `build`, `refactor`, `test`, `function`, `class`, `module`, `api`, `feature`, `logic`, `handler`, `controller`, `schema`, `migration`, `script`
   - 检查 git status 是否有非 tasks.md 的修改
   - 条件全部满足返回 `quick_finish`，否则返回 `standard`
4. 验证测试通过
5. Commit

## Task 2: 将 quick-finish 检测集成到 `run_ship_phase1()` 决策点

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_ship_quick_finish_flow.bats`，验证：
   - 当 `detect_quick_finish` 返回 `quick_finish` 时，`run_ship_phase1` 输出包含 "Quick Finish" 的提示
   - 设置环境变量 `QUICK_FINISH_SELECTED=A` 时，跳过后续 worktree 和 plan 生成步骤
   - 设置 `QUICK_FINISH_SELECTED=B` 时，走标准流程
2. 验证测试失败
3. 在 `skills/guide-ship/scripts/ship_plan.sh` 的 `run_ship_phase1()` 中，在 COMMIT GATE 之后、execution mode 检测之前插入 quick-finish 检测：
   - 调用 `detect_quick_finish`
   - 若返回 `quick_finish`，展示选项 A/B 并读取 `QUICK_FINISH_SELECTED`
   - 若选择 A，设置 `QUICK_FINISH_DETECTED=yes`，跳过后续步骤
   - 若选择 B，继续标准流程
4. 在 `skills/guide-ship/SKILL.md` 的 Phase 1 流程说明中新增 quick-finish 分支
5. 验证测试通过
6. Commit

## Task 3: 端到端 bats 测试

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_ship_quick_finish_e2e.bats`，验证：
   - 创建一个模拟 change 目录，tasks.md 中仅有 1 个 trivial 任务
   - 所有代码已提交，无未提交变更
   - 运行 `run_ship_phase1`，确认输出包含 "Quick Finish" 选项
   - 设置 `QUICK_FINISH_SELECTED=A` 后再次运行，确认跳过 worktree 和 plan 生成
   - 验证归档后 iteration.json 状态正确更新
2. 验证测试失败
3. 实现端到端测试
4. 验证测试通过
5. Commit