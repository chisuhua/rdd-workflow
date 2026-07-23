# Design: add-heartbeat-config

## Context

`RddfSessionCoordinator` 硬编码 `DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 30 * 60`（1800秒）和默认刷新阈值 5 分钟，无法在不同部署环境（高延迟集群、低延迟本地）按需调整。当前只能修改源码才能适配，缺少运行时可配置性。

## Goals / Non-Goals

**Goals:**
- 支持 `RDDF_HEARTBEAT_TIMEOUT_SECONDS` 环境变量覆盖默认超时
- 支持 `RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS` 环境变量覆盖默认刷新阈值
- 将 `check_heartbeat_timeouts()` 从模块常量改为实例属性，支持每个 coordinator 实例独立配置

**Non-Goals:**
- 不修改 `sessions_schema.json`（无 schema 变更）
- 不引入新 capability（仅为现有 `configuration` 能力新增运行时配置项）

## Decisions

| 决定 | 理由 |
|------|------|
| 优先级：环境变量 > 实例参数 > 模块常量 | 环境变量可全局覆盖，实例参数提供细粒度控制，常量作为安全默认值 |
| 非法值回退默认值 + 日志警告 | 防御性编程，避免配置错误导致服务不可用 |
| 构造函数解析 env var 存入实例属性 | 单次解析，后续调用无开销 |

## Risks / Trade-offs

- **低风险**：默认值保持不变（30min / 5min），无覆盖时不改变行为
- **向后兼容**：所有现有调用方无需修改
- **测试覆盖**：3 个新增测试（默认值 / 环境变量覆盖 / 非法值回退）