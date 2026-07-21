# fix-rddf-schema-validation

**Priority**: P0
**Phase**: v2.1
**Status**: skeleton

## Why

## 架构依据
- RDDF session schema validation 基础设施从未生效: SCHEMA_PATH 指向不存在的目录，validate=True 从未传参

## 范围
- **In Scope**:
  - 修正 SCHEMA_PATH 指向 skills/_lib/schemas/sessions_schema.json
  - 在 _read_unlocked() 中启用 schema validation
  - 3 个 schema validation 测试
- **Out Scope**:
  - 不修改 session 数据模型
  - 不修改 sessions_schema.json 内容

## 验收标准
- SCHEMA_PATH 指向正确路径且 validation 生效
- 非法 fields 的 sessions.json 被正确拒绝
- 合法 sessions.json 正常通过

## What Changes

- TODO: define specific changes during fill phase

## Impact

- Affected specs: TBD
- Affected code: TBD
