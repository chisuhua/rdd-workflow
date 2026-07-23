# task-parallel-throttle

**优先级**: P1 | **来源**: Session 复盘 2026-07-21
**阶段**: v2.1 | **分类**: planning
**类型**: feature

## 架构依据
- 复盘发现：8 个 deep agent 同时发起导致 volcengine-plan 限流 + kimi-code 配额耗尽，6/8 个 agent 需要 2-3 次重试才能完成
- 总延迟从线性变为超线性（约 20 分钟 vs 预期 10 分钟）

## 范围
- **In Scope**:
  - ./rddf ship --parallel 命令增加 `--max-concurrent=<N>` 参数，默认值 3
  - 超过限制的 agent 排队等待而非立即发起
  - 排队逻辑用 bash 实现：wait -n + 自旋检查
  - 1 个 bats 测试：验证并发数不超过限制
- **Out Scope**:
  - 不修改 task() 函数本身（平台层）

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- 3 agent 并发时不超 3 个同时发起
- 1 个 bats 测试通过
