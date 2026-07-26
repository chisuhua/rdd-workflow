# fix-silent-exception

## 动机

`loop_engine.py` 中 5 处 `except Exception: pass` 在 verify_goal/_load_interaction_mode/run 等关键路径静默吞掉异常。一旦 state schema 漂移或 event_log I/O 失败，故障表现为"循环卡住/无输出"，极难诊断。

## 提议

在 5 处 `except Exception: pass` 的 `pass` 前追加 `event_log.record(EventType.ERROR_OCCURRED, Severity.ERROR, ...)` 记录异常信息，保持原有控制流不变。

### 架构依据

- Oracle 代码审查 2026-07-19 #4

### 范围

- **In Scope**:
  - loop_engine.py:203-205 — state.update_field 失败
  - loop_engine.py:274-277 — scan_state 阶段
  - loop_engine.py:303-305 — generate_plan 阶段
  - loop_engine.py:339-342 — execute_plan 阶段
  - loop_engine.py:355-358 — adapt 阶段
  - 对应单元测试
- **Out Scope**:
  - fs_watcher.py `except OSError: pass`
  - gate.py 已有 logging 的 except 块
  - 不引入新 event type

### 验收标准

- 5 处 `except Exception: pass` 全部替换为 `event_log.record` + pass 双行模式
- 1-2 个回归测试验证日志写入
- 所有现有测试通过