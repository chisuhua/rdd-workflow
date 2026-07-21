# fix-rddf-schema-validation Tasks

- [ ] Task 1: `skills/_lib/rddf_session.py` 修正 schema 路径与启用 validation - 期待拒绝 malformed sessions.json
  - [ ] Step 1: `tests/unit/test_rddf_session.py` 增加三条回归用例，分别覆盖缺失 required 字段、类型错误字段、合法 payload 通过
  - [ ] Step 2: 运行 `pytest tests/unit/test_rddf_session.py -q`，确认新用例当前失败
  - [ ] Step 3: 在 `skills/_lib/rddf_session.py` 将 `SCHEMA_PATH` 改为 `skills/_lib/schemas/sessions_schema.json`，并在 `_read_unlocked()` 读取时传入 `validate=True`
  - [ ] Step 4: 重新运行 `pytest tests/unit/test_rddf_session.py -q`，确认 3 个回归用例通过
  - [ ] Step 5: `git add skills/_lib/rddf_session.py tests/unit/test_rddf_session.py && git commit -m "fix: enable rddf session schema validation"`
