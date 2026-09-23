## Tasks

- [ ] ### Task 0 — Setup (cross-cutting)
- [ ] ### Task 1 — Shared fixture (AC infrastructure)
- [ ] ### Task 2 — AC-1 fcntl 并发写 (2 real Python child processes write 50 events each)
- [ ] ### Task 3 — AC-2 offset 轮询时序 (process A writes, process B polls with incrementing offset)
- [ ] ### Task 4 — AC-3 crash 残留恢复 (process A killed, process B sees residual session)
- [ ] ### Task 5 — AC-4 H7 全局单例 (2 owners, 2nd create_session raises ConflictError)
- [ ] ### Task 6 — AC-5 自动归档重置 (events.jsonl hits 50MB, last_seen_offset resets to 0)
- [ ] ### Task 7 — AC-6 guide_entry 持久化 (subshell exit triggers guide_close, abnormal exit preserves active)
- [ ] ### Task 8 — Documentation + regression gate (AC-7, AC-8, AC-9)
- [ ] ### Task 9 — Final integration + commit
