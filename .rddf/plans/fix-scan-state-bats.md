# fix-scan-state-bats — 实施计划

## 概述
修复 scan_state 的 handoff 读取逻辑，使 plan-handoff.json 与实际目录状态一致。

## TDD 步骤

### Step 1: 排查 handoff 与实际目录的差异
- [ ] 检查 `.rddf/state/.arch-handoff.json` 内容
- [ ] 检查 `.rddf/state/.plan-handoff.json` 内容  
- [ ] 对比 openspec/changes/ 目录实际状态
- [ ] 定位不一致的来源

### Step 2: 修复 scan_state 的 handoff 读取逻辑
- [ ] 分析 `scan_state()` 函数中的 handoff 读取代码
- [ ] 修复 handoff 与目录状态的对齐
- [ ] 更新或归档已完成的 changes

### Step 3: 验证修复
- [ ] 运行 scan_state bats 测试
- [ ] 确认所有测试通过
- [ ] 确认无回归
