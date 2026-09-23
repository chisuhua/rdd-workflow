---
优先级: P0
来源: 2026-09-23 add-stage-guide-e2e-cross-process-coverage proposal — AC-1 cross-process fcntl contention test caught real production bug
阶段: v4.1 follow-up
分类: bug-fix
类型: fix
主题: 完整多会话支持
依赖: feat-guide-orchestrator-session-event-bus (shipped), add-stage-guide-e2e-cross-process-coverage (in progress)
---
**优先级**: P0 | **来源**: 2026-09-23 cross-process e2e testing
**阶段**: v4.1 follow-up | **分类**: bug-fix
**类型**: fix | **主题**: 完整多会话支持
**依赖**: feat-guide-orchestrator-session-event-bus, add-stage-guide-e2e-cross-process-coverage
**主题**: 完整多会话支持

> **症状**: `events_log.py` 使用 `fcntl.flock(LOCK_EX | LOCK_NB)` 在并发写时**抛 `BlockingIOError`** 而非序列化写入，导致多进程并发 append_event 时**第二个进程的事件全部丢失**。
>
> **直接证据**（来自 add-stage-guide-e2e-cross-process-coverage AC-1 实测）：
> ```
> === Writer A log ===
> wrote:50
> === Writer B log ===
> Traceback (most recent call last):
>   ...
>   fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
> BlockingIOError: [Errno 11] Resource temporarily unavailable
> EventsLogError: Could not append event: [Errno 11] Resource temporarily unavailable
> ```
> 结果：50 events 写入成功，50 丢失。
>
> **根因**：`LOCK_NB` = non-blocking，锁被占用时立即抛 `EAGAIN`。当前实现**不重试、不等待**。
>
> **代码矛盾**：`events_log.py:8` 模块 docstring 声称 "Locking: fcntl.flock (POSIX), with a 10s lock timeout"，`_LOCK_TIMEOUT = 10.0` 已定义但**未实现**。

## 架构依据

feat-guide-orchestrator-session-event-bus 的核心架构承诺是"多 OpenCode 窗口通过文件轮询协同"。该架构的隐含前提是 events.jsonl 接受**多进程并发写**（每个 rdd-builder 实例都要写 phase_started/completed 事件）。

当前实现使用 `LOCK_EX | LOCK_NB`:
- `LOCK_EX` 排他锁 ✅ 正确
- `LOCK_NB` non-blocking ❌ 错误 — 在并发场景下立即抛 `BlockingIOError`

这意味着 feat-guide-orchestrator-session-event-bus 的多进程协同**实际不可用**，但单元测试 + 单进程 e2e 都无法发现（因为不触发真跨进程锁竞争）。

**为什么 P0**：
1. v4.1 release 的核心 feature 实际不可用 = 高危 silent failure
2. 用户场景"窗口 A 看窗口 B 进度"在并发写时会丢失事件
3. 数据完整性问题，不是 minor bug

## 范围

### In Scope
- `events_log.py:122` `append_event` 的 `fcntl.flock(LOCK_EX | LOCK_NB)` 改成实现 10s timeout 的阻塞锁
- `events_log.py:194` `mark_seen` 同样问题，同步修复
- `events_log.py:242` `archive_events` 同样问题，同步修复
- 加单元测试覆盖"并发写不丢事件"（真 subprocess spawn）
- 在模块 docstring 反映实际行为

### Out Scope
- ❌ 不改 fcntl 锁的 file path（保持 `<events_jsonl>.lock`）
- ❌ 不改 50MB cap 或 archive 逻辑
- ❌ 不改 events.jsonl 的写入格式
- ❌ 不引入新依赖（仅用 fcntl + time）

## Why

修复 fcntl.flock 的 non-blocking 行为，实现 module docstring 承诺的 10s 超时序列化。这是 feat-guide-orchestrator-session-event-bus 跨进程架构承诺能真正成立的前提。

## What Changes

### `events_log.py` 三处 LOCK_EX | LOCK_NB 改为带 timeout 的阻塞锁

```python
# Old (buggy):
fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
# ↑ 立即抛 BlockingIOError on contention

# New (correct):
deadline = time.monotonic() + _LOCK_TIMEOUT
while True:
    try:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
        break
    except BlockingIOError:
        if time.monotonic() >= deadline:
            raise EventsLogError(f"Could not acquire lock within {_LOCK_TIMEOUT}s")
        time.sleep(0.01)  # 10ms retry interval
```

### `import time` (file 顶部)

events_log.py 当前没 import time，需添加。

### 单元测试

新增 `tests/unit/test_events_log_concurrent.py`：
- `test_concurrent_writers_no_loss`: 用 `subprocess.Popen` 启动 2 个 Python 子进程同时写 events.jsonl，验证总数 + 唯一性
- `test_concurrent_writer_timeout`: 模拟锁持有方永不释放，验证超时后抛 EventsLogError

## Acceptance

- [ ] **AC-1**: `events_log.py:122` append_event 在并发场景下序列化（不抛 BlockingIOError）
- [ ] **AC-2**: `events_log.py:194` mark_seen 同样行为
- [ ] **AC-3**: `events_log.py:242` archive_events 同样行为
- [ ] **AC-4**: 锁获取超过 10s 抛 `EventsLogError(f"Could not acquire lock within {_LOCK_TIMEOUT}s")`
- [ ] **AC-5**: 单元测试 `test_concurrent_writers_no_loss` pass（2 子进程各 50 事件，合并 100 唯一）
- [ ] **AC-6**: 单元测试 `test_concurrent_writer_timeout` pass
- [ ] **AC-7**: add-stage-guide-e2e-cross-process-coverage AC-1 由 FAIL → PASS
- [ ] **AC-8**: 全量回归 `./test.sh --quick` 通过

## Capabilities

### MUST

- 锁获取必须实现 10s 超时（与模块 docstring 一致）
- 超时后必须抛清晰的 `EventsLogError`，不是裸 `BlockingIOError`
- 锁释放（LOCK_UN）保持不变
- 所有现有 `events_log.py` 单元测试继续 pass

### MUST NOT

- 不引入新的锁机制（保持 fcntl.flock）
- 不改变 events.jsonl 文件路径或 lock 文件路径
- 不放宽 atomic write 语义（write + fsync + rename）
- 不修复 `parent_session_id` 等其他已知问题（out of scope）

## Impact

- ✅ feat-guide-orchestrator-session-event-bus 跨进程协同实际可用
- ✅ add-stage-guide-e2e-cross-process-coverage AC-1 由 FAIL → PASS
- ⚠️ 引入最多 10s 的写入延迟（在锁竞争场景下）
- ⚠️ 旧测试 `test_unknown_event_type_rejected` 等需要确认不依赖 BlockingIOError 行为
