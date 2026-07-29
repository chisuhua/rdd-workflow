# Archive cleanup plan files — 实施任务

## Task 1: 在 `ship_archive.sh` 中添加 `cleanup_plan_file()` 函数

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_archive_cleanup_plan_files.bats`，定义 `cleanup_plan_file()` 的行为：
   - 当 `.rddf/plans/<name>.md` 存在时，调用 `cleanup_plan_file` 后文件被删除
   - 当 `.rddf/plans/<name>.md` 不存在时，调用 `cleanup_plan_file` 返回 0 且无错误输出
   - `cleanup_plan_file` 只删除精确匹配的 `<name>.md` 路径，不误删其他文件
2. 验证测试失败（函数不存在）
3. 在 `skills/guide-ship/scripts/ship_archive.sh` 中实现 `cleanup_plan_file()`：
   - 接收 `project_root` 和 `change_name` 参数
   - 构造路径：`<project_root>/.rddf/plans/<change_name>.md`
   - 检查文件是否存在，不存在则返回 0（幂等）
   - 存在则 `rm -f` 删除，输出日志
4. 在 `archive_change_for_mode()` 末尾（`cleanup_plan_handoff` 之后）插入 `cleanup_plan_file` 调用
5. 验证测试通过
6. Commit

## Task 2: 在 `scan-state.sh` 中添加 `check_orphan_plan_files()` 函数

**TDD 步骤**:
1. 在 `tests/integration/` 中扩展 `test_archive_cleanup_plan_files.bats`，定义 `check_orphan_plan_files()` 的行为：
   - 当 `.rddf/plans/` 中存在孤立文件（其 change 目录不存在）时，输出包含 "孤立计划文件" 的 warning
   - 当 `.rddf/plans/` 中文件均对应活跃 change 时，不输出 warning
   - 当 `.rddf/plans/` 目录不存在时，静默返回 0
   - 孤立文件计数正确（3 个孤立文件输出 3）
2. 验证测试失败（函数不存在）
3. 在 `skills/guide/scripts/scan-state.sh` 中实现 `check_orphan_plan_files()`：
   - 接收 `PROJECT_ROOT` 参数
   - 遍历 `.rddf/plans/*.md`，提取文件名（不含扩展名）作为 change 名称
   - 检查 `openspec/changes/<name>/` 目录是否存在
   - 若不存在再检查 `openspec/changes/archive/*-<name>` 是否存在
   - 两者都不存在则判定为孤立文件，计数
   - 输出 warning 级别信息（文件名列表 + 计数）
4. 在 `scan_state()` 末尾（`check_arch_handoff_stale` 之后）插入 `check_orphan_plan_files` 调用
5. 验证测试通过
6. Commit

## Task 3: 端到端 bats 测试

**TDD 步骤**:
1. 在 `tests/integration/` 中扩展 `test_archive_cleanup_plan_files.bats`，编写端到端场景：
   - 创建模拟 change 目录，创建 `.rddf/plans/<name>.md` 文件
   - 模拟 archive 流程（通过 `archive_change_for_mode` 或直接调用 `cleanup_plan_file`）
   - 验证 plan 文件已被删除
   - 创建孤立计划文件（不创建对应 change 目录），运行 `scan_state` 函数
   - 验证 warning 输出包含文件名和计数
   - 清理所有孤立文件后再次运行，确认无 warning
2. 验证测试失败
3. 实现端到端测试
4. 验证测试通过
5. Commit