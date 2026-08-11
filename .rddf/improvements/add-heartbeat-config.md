# add-heartbeat-config

**优先级**: P1 | **来源**: .omo/plans/rddf-session-improvement-plan.md — W1-1
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据
- DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 30 * 60 硬编码

## 范围
- **In Scope**:
  - RddfSessionCoordinator 构造函数支持 RDDF_HEARTBEAT_TIMEOUT_SECONDS 环境变量
  - 支持 RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS 环境变量
  - check_heartbeat_timeouts() 使用实例属性而非模块常量
- **Out Scope**:
  - 不修改 sessions_schema.json（运行时配置）

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- 默认值仍为 30min / 5min
- 环境变量可覆盖
- 3 个测试（默认/覆盖/非法值）
