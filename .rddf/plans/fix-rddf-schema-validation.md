# fix-rddf-schema-validation — 实施计划

**Change**: fix-rddf-schema-validation | **类型**: bug-fix | **模式**: worktree
**Worktree**: .rddf/wt/fix-rddf-schema-validation | **Branch**: openspec/fix-rddf-schema-validation

---

## 1. 修正 SCHEMA_PATH + 启用 validation

- 修改 `skills/rddf-session/scripts/rddf_session.py`
- 将 `SCHEMA_PATH` 修正为 `skills/_lib/schemas/sessions_schema.json`
- 在 `_read_unlocked()` 中实现 validation 调用
- 完成后 commit

## 2. 编写 schema validation 测试 (3 tests)

- `test_validate_legal_session` — 合法 json 通过
- `test_validate_missing_required_field` — 缺失必需字段被拒绝
- `test_validate_invalid_field_type` — 非法字段类型被拒绝
- 完成后 commit

## 3. 验证

- 运行 `python3 -m pytest tests/ -k "rddf_session" -v`
- 确保所有现有测试通过

---

## 验证
    
- 每个步骤完成后 commit
- 最终运行 `pytest` / `bats` 确保回归通过
