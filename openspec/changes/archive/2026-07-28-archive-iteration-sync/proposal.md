## Why

- 复盘发现：archive.sh 归档流程完成后，iteration.json 中 5/8 个 change 缺少 `archived_at` 时间戳，feature_view.archived_count 与实际值差 5
- 根因：skeleton→archive 快速路径跳过了 iteration 同步步骤

## What Changes

- **In Scope**:
  - archive.sh::archive_change() 末尾强制调用 `iteration.mark_archived(name)` 写入 archived_at 时间戳
  - feature_view 的 archived_count 从 iteration 动态计算，不依赖缓存字段
  - 3 个回归测试：正常归档、重复归档幂等、archive 失败不写入
- **Out Scope**:
  - 不修改 guide-ship 的轻量模式归档逻辑（仅 worktree 模式）

## 验收标准

- archive 后迭代 iteration.json，archived_at 存在且 archived_count 正确
- 3 个 bats 回归测试通过

## Capabilities

### New Capabilities
- `workflow-synthesizer` (add-workflow-synthesizer only): WorkflowRecommendation + PhaseStatus module
- `archive-iteration-sync`: iteration.json 同步机制
- `wave-scheduler`: 自动 wave 调度引擎
- `propose-quality-check`: propose 阶段质量检查 hook
- `guide-plan-noninteractive`: 非交互模式

### Modified Capabilities
（视具体 change 而定）

## Impact

（视具体 change 而定）
