# fix-rddf-schema-validation — 设计

## 方案

当前 `rddf_session.py` 中 `_read_unlocked()` 方法接收 `validate=True` 参数，但两个问题导致 validation 从未生效：

1. `SCHEMA_PATH` 常量指向 `schemas/`（不存在），应指向 `skills/_lib/schemas/sessions_schema.json`
2. `validate=True` 参数传递链中未实际传给 `jsonschema.validate()`

## 实现

- 修改 `rddf_session.py`: 修正 SCHEMA_PATH，在 `_read_unlocked()` 中传入 validate 逻辑
- 添加 3 个测试:
  - 合法 sessions.json 正常通过
  - 缺失必需字段的 sessions.json 被拒绝
  - 非法字段类型的 sessions.json 被拒绝

## 影响

仅修改 rddf_session.py 内部逻辑，不影响 session 数据模型或 API。