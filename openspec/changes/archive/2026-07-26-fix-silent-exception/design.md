# fix-silent-exception — 设计

## 问题

`loop_engine.py` 中有 5 处 `except Exception: pass`，分布在关键路径上。该模式源于 v2.0 初期对错误处理的保守策略——担心 event_log 写入本身触发二次异常导致死循环。

## 方案

利用 loop_engine.py:167-173 已建立的 pattern:
```python
self.event_log.record(EventType.ERROR_OCCURRED, Severity.ERROR, message=f"...", context={"error": str(e)})
```

在每处 `pass` 前插入 `event_log.record(...)`。如果 event_log 也失败，外层仍有 `pass` 兜底，不会改变控制流。

## 修改位置

| Line | 方法 | 修改 |
|------|------|------|
| 203-205 | `verify_goal()` | 追加 event_log.record |
| 274-277 | `_load_interaction_mode()` → scan_state | 追加 event_log.record |
| 303-305 | `_load_interaction_mode()` → generate_plan | 追加 event_log.record |
| 339-342 | `_load_interaction_mode()` → execute_plan | 追加 event_log.record |
| 355-358 | `_load_interaction_mode()` → adapt | 追加 event_log.record |

## 影响

纯粹是增量日记记录，无功能变更，无新依赖，无 schema 变更。