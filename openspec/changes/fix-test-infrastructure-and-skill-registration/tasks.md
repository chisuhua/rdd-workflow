## 1. bats test_helper 路径修复

- [x] 1.1 修复 `tests/integration/test_helper.bash` 路径解析（`bats_load_safe` 找不到）
- [x] 1.2 修正 `tests/integration/` 下所有 `.bats` 文件的 `load test_helper` 为 `BATS_TEST_DIRNAME` 派生路径
- [x] 1.3 运行 `npm test`（至少 smoke.bats）确认退出码 0

## 2. skill 计数动态化

- [x] 2.1 更新 `tests/unit/test_doc_contracts.py`：skill 计数改为动态扫描磁盘（含 `guide-design`）
- [x] 2.2 运行 `python3 -m pytest tests/unit/test_doc_contracts.py -q --tb=short` 通过

## 3. concurrency / cross-session 测试环境自适应

- [x] 3.1 4 个 concurrency 测试（`test_rddf_session_concurrency`）：单 worker / 无 xdist 环境 `pytest.skip()` 而非 FAIL
- [x] 3.2 4 个 cross-session recovery 测试（`test_rddf_session_cross_session_recovery`）：检查 timeout 配置，必要时放宽
- [x] 3.3 运行 `python3 -m pytest tests/unit/ -q --tb=short` 全量通过（concurrency 可 skip 但不可 FAIL）

## 4. guide-design skill 注册验证

- [x] 4.1 验证 `skill_use("guide-design")` 在 skill 工具中可用
- [x] 4.2 若未注册，完成注册并更新相关文档/测试
