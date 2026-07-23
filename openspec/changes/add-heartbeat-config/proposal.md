## Why

RddfSessionCoordinator 硬编码 `DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 30 * 60`，导致不同部署环境（高延迟集群、低延迟本地）无法按需调整心跳超时阈值。当前只能改源码才能适配，缺少运行时可配置性。

## What Changes

- **RddfSessionCoordinator 构造函数** 新增对 `RDDF_HEARTBEAT_TIMEOUT_SECONDS` 环境变量的支持，覆盖默认 30min 超时
- **RddfSessionCoordinator 构造函数** 新增对 `RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS` 环境变量的支持，覆盖默认 5min 刷新阈值
- **check_heartbeat_timeouts()** 从模块常量改为使用实例属性，使每个 coordinator 实例可独立配置
- 非法值（负数、非数字）自动回退到默认值，日志记录警告

## Capabilities

### New Capabilities
- (无 — 不引入新 capability，仅为现有 `configuration` 能力新增运行时配置项)

### Modified Capabilities
- `configuration`: 新增 `RDDF_HEARTBEAT_TIMEOUT_SECONDS` 和 `RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS` 环境变量支持，扩展运行时配置覆盖范围

## Impact

- **RddfSessionCoordinator** — 构造函数解析 env var，实例属性替代模块常量
- **check_heartbeat_timeouts()** — 引用实例属性而非全局常量
- **测试** — 3 个新增测试（默认值 / 环境变量覆盖 / 非法值回退）
- 无 schema 变更，无 API 破坏性变化