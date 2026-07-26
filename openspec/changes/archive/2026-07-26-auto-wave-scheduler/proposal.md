## Why

复盘发现 #3 + #4 指出：当前 Wave 切换靠人工判断，iteration.json 状态转换需要手动操作。`manual_deps` 已有依赖数据（ADR-0022），但缺少自动化消费方来自动检测 blocker 解除状态并建议可执行的下一波 change。

用户必须在 archive 后手动检查哪些 change 的 blocker 已解除，这不仅低效，还容易遗漏。当 iteration.json 中 20+ 个 change 时，人工扫描 blocker 状态不可行。

## What Changes

- **Add** archived hook: 当 change 归档后，自动扫描 `iteration.json` 中所有 `status=planned` 且 `manual_deps` 中包含刚归档 change 的条目
- **Add** 入口 hook 自动迭代状态转换: `guide-arch/guide-plan/guide-ship` 入口 hook 自动推进 `iteration.json` 状态（planned→proposed→in_worktree→archived）
- **Add** 建议输出模块: 归档后输出 "bloker 已解除: change-x, change-y 可以执行"
- **Add** 测试覆盖 archived→unblocked→suggest 链路

## Capabilities

### New Capabilities
- `auto-wave-scheduler`: 自动检测 blocker 解除并建议可执行 change，消除人工扫描依赖图的开销

### Modified Capabilities
- `guide-arch/guide-plan/guide-ship`: 入口 hook 自动推进 iteration 状态转换
- `archive.sh`: 归档完成后触发器（不阻塞），调用 auto-wave-scheduler 检测 blocker 解除

## Impact

- **New code**: ~80 行（hook 逻辑 + 建议输出 + 测试）
- **Dependencies**: 依赖 `manual_deps` 字段（ADR-0022，已完成）
- **Compatibility**: 100% 向后兼容 — 不影响现有 hook 行为，仅追加检测和建议输出
- **Risk**: 低 — 纯附加逻辑，不修改现有状态机行为；仅输出建议不自动执行
- **Source**: 复盘改进 #3 + #4, improvement `auto-wave-scheduler`