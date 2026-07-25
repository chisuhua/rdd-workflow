## 1. loop_engine.py:203-205 — verify_goal

- 在 `except Exception: pass` 前追加 event_log.record
- 完成后 commit

## 2. loop_engine.py:274-277,303-305,339-342,355-358 — _load_interaction_mode

- 4 处 phase 级别的 `except Exception: pass` 前追加 event_log.record
- 完成后 commit

## 3. 编写回归测试

- 验证 5 处日志写入在异常时生效
- test_silent_exception_verify_goal
- test_silent_exception_phase_states
- 完成后 commit

## 4. 验证

- 运行 `python3 -m pytest tests/ -k "loop" -v`
- 确保所有现有测试通过