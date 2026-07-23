# Tasks: add-rddf-concurrency-tests

## 1. Add Concurrency Test
- [ ] 1.1 创建 `tests/integration/test_rddf_session_concurrency.py`
- [ ] 1.2 实现 multiprocessing.Pool 并发 100 次 create_session 测试
- [ ] 1.3 验证 LOCK_NB fail-fast 语义（非无限重试）

## 2. Add Cross-Session Recovery Test
- [ ] 2.1 创建 `tests/integration/test_rddf_session_cross_session_recovery.py`
- [ ] 2.2 实现 session 超时 → orphaned → find_next_recommendation 全链路
- [ ] 2.3 验证 transfer_ownership 恢复后会话一致性