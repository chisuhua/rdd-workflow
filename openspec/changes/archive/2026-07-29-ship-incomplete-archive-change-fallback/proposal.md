## Why

当前 guide-ship archive 阶段：如果 tasks.md 中有未完成的 [ ] 条目，直接归档会导致这些任务丢失。需要 archive 前检查未完成任务，自动生成 change 候选追加到 proposal-suggestions.md。

## What Changes

- guide-ship Phase 3 (archive) 增加 pre-archive check：扫描 tasks.md 中未完成的 [ ] 条目
- 对每个未完成任务判断是「依赖未解除」还是「主动跳过」
- 依赖未解除：自动生成 change 候选描述，追加到 proposal-suggestions.md
- 主动跳过：标记为 skipped，不生成新 change
- 用户交互确认（展示即将创建的候选 change 列表）

## Capabilities

### New Capabilities
- `archive-incomplete-task-fallback`: 归档时检测未完成任务并生成候选 change

### Modified Capabilities
- `archive-flow`: 在归档流程中增加 pre-archive check 步骤

## Impact

- 修改文件：skills/_lib/archive.sh, skills/guide-ship/scripts/ship_archive.sh
- 影响流程：guide-ship Phase 3 归档流程
- 新增测试：2 个 bats 测试（有未完成任务 + 无未完成任务场景）
