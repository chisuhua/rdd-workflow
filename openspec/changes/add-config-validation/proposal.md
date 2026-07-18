## Why

用户可编辑的 `config.yaml` 与 `config.py::ConfigParser` 之间无 schema 校验。当用户改错 key（如 `max_iterations` → `maxIterations`），ConfigParser 静默返回 None，Loop 引擎 fallback 到默认值 100——静默降级而非报错。这是用户侧可触达的真 bug 源头，需要 v2.0.9 patch 修复。

## What Changes

- `config.py::ConfigParser.load()` 末尾加 `validate()` 方法
- 创建 `skills/_lib/schemas/config_schema.json`（jsonschema，项目已有依赖）
- schema 校验 required keys + 类型（max_iterations、max_retries 等）
- 失败时 `raise ConfigError(...)` 而非静默 fallback
- 2-3 个单元测试覆盖合法/非法/缺失 schema 场景

## Capabilities

### New Capabilities
- `config-validation`: config.yaml 结构校验，防止 key 拼写错误导致静默降级

### Modified Capabilities
- （无——不修改现有 API 签名）

## Impact

- **Affected code**: `skills/_lib/config.py` + `skills/_lib/schemas/config_schema.json`
- **Scope**: 仅 `ConfigParser.load()` 末尾加 `validate()` 调用
- **Risk**: 低——向后兼容：缺失 schema 文件时跳过验证
- **Effort**: 2-3 小时