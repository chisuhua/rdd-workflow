## Why

loop_engine.py 中有 5 处 `except Exception: pass` 位于关键执行路径（verify_goal、scan_state、generate_plan、execute_plan、adapt）。当 state schema 漂移或 event_log I/O 失败时，静默吞错导致故障表现为"循环卡住/无输出"，极难诊断。这是可观测性债务，需要在 v2.0.9 patch 中修复。

## What Changes

- loop_engine.py: 5 处 `except Exception: pass` → 替换为 `event_log.record(ERROR_OCCURRED)` + pass 双行模式
- 复用 loop_engine.py:167-173 已有的错误日志模式
- 追加 1-2 个回归测试验证日志写入
- 不修改 fs_watcher.py 的 `except OSError: pass`（文件监听 cleanup 标准模式）

## Capabilities

### New Capabilities
- `engine-error-observability`: Loop 引擎关键路径错误可见性，确保静默异常被 event_log 记录

### Modified Capabilities
- （无——不改变现有行为，仅增加日志）

## Impact

- **Affected code**: `skills/loop_engine.py`
- **Scope**: 仅 5 处 `except` 块，每处追加一行 `self.event_log.record(...)` + 保留 `pass`
- **Risk**: 低——不改变控制流，不修改公有 API
- **Effort**: 1-2 小时