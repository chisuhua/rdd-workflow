# add-rddf-concurrency-tests

**优先级**: P1 | **来源**: .omo/plans/rddf-session-improvement-plan.md — W1-2
**阶段**: v2.1 | **分类**: core
**类型**: test-only

## 架构依据
- _with_file_lock 使用 LOCK_NB（非阻塞 fail-fast），并发调用会失败而非排队
- 需要测试验证这一真实语义

## 范围
- **In Scope**:
  - tests/integration/test_rddf_session_concurrency.py: multiprocessing.Pool 并发 100 次 create_session
  - tests/integration/test_rddf_session_cross_session_recovery.py: session 超时→orphaned→恢复全链路
- **Out Scope**:
  - 不修改 rddf_session.py 逻辑

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- 并发测试验证 LOCK_NB 行为（非破坏，非无限重试）
- 跨 session 恢复测试验证 find_next_recommendation + transfer_ownership
