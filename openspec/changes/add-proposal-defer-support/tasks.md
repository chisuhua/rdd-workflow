# Add proposal defer support — 实施任务

## Task 1: 在 `list_improvements()` 中增加状态字段输出

**TDD 步骤**:
1. 在 `tests/unit/test_state.sh` 或 `tests/integration/test_proposal_defer.bats` 中编写测试，定义：
   - GIVEN `improvements/` 下有含 `**状态**: 已推迟` 的文件
   - WHEN `list_improvements()` 被调用
   - THEN 输出包含 `name|priority|source|已推迟` 格式
   - GIVEN `improvements/` 下有含 `**状态**: 待讨论` 的文件
   - THEN 输出包含 `name|priority|source|待讨论`
   - GIVEN `improvements/` 下有**无 `**状态**` 字段**的文件
   - THEN 输出包含 `name|priority|source|待讨论`（缺省默认）
2. 验证测试失败
3. 修改 `skills/_lib/state.sh` 中 `list_improvements()` 函数：
   - 在 priority 和 source 提取后，增加 `**状态**` 字段读取
   - 新代码：`local status=$(grep -m1 '^\*\*状态\*\*:' "$f" 2>/dev/null | sed 's/.*\*\*状态\*\*: *//' | cut -d'|' -f1 | xargs)`
   - 输出追加 `|${status:-待讨论}`
4. 验证测试通过
5. Commit

## Task 2: 更新 `arch_proposal_review.sh` 支持延迟状态跳过

**TDD 步骤**:
1. 在 `tests/integration/test_proposal_defer.bats` 中追加测试，定义：
   - GIVEN 2 个 improvement 文件：`test-deferred.md`（含 `**状态**: 已推迟`）和 `test-pending.md`（无状态字段）
   - WHEN `arch_proposal_review` 在默认模式运行
   - THEN 只显示 `test-pending`，显示 `⏸️ 1 个已推迟（按 v 查看全部）`
   - GIVEN 用户按 `v` 查看全部
   - THEN 显示 `[P?] ⏸️ test-deferred` 带 `⏸️` 前缀
   - GIVEN `test-deferred.md` 无 `**状态**` 字段的旧提案
   - THEN 正常展示（向后兼容，不跳过）
2. 验证测试失败
3. 修改 `skills/guide-arch/scripts/arch_proposal_review.sh`：
   - Step 3 分类循环中：从 `imp_file` 读取 `**状态**` 字段
   - 已推迟 → 默认跳过，`DEFERRED_COUNT++`
   - Step 4 展示：在 `📋 待审查` 后显示 `⏸️ N 个已推迟（按 v 查看全部）`
   - 推迟提案列表项加 `⏸️` 前缀
   - Step 5 菜单：增加 `v` 选项（查看全部含已推迟）
   - 处理 `v`：设置 `SHOW_ALL=true` 重新执行审查（跳过跳过逻辑）
4. 验证测试通过
5. Commit

## Task 3: 实现 `d`（延迟）决策写入 improvement 文件 + 集成测试

**TDD 步骤**:
1. 在 `tests/integration/test_proposal_defer.bats` 中追加集成测试：
   - GIVEN `improvements/test-defer.md` 无 `**状态**` 字段
   - WHEN 用户在 Phase 5.5 选择 `d`（延迟）该提案
   - THEN `improvements/test-defer.md` 包含 `**状态**: 已推迟`
   - THEN 重新进入 Phase 5.5 默认不展示该提案（延迟已持久化）
   - GIVEN 用户再次审查并选择 `v` 查看全部
   - THEN 该提案以 `⏸️` 前缀显示
2. 验证测试失败
3. 修改 `skills/guide-arch/scripts/arch_proposal_review.sh`：
   - `d` 分支（L318-L325）：在 `sed -i` 写入 suggestions.md 之前，增加写入 `imp_file`
   - 新代码：`sed -i '/^\*\*类型\*\*:/a\**状态**: 已推迟' "$imp_file"`
   - 保持 suggestions.md 写入不变（双重持久化）
4. 验证测试通过
5. 运行 `bats tests/integration/test_proposal_defer.bats` 确认全部 3 个任务通过
6. Commit