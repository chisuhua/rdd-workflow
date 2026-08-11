# fix-silent-exception

**优先级**: P0 | **来源**: Oracle 代码审查 2026-07-19 #4
**阶段**: default | **分类**: general
**类型**: feature

## 架构依据
- Oracle 代码审查结论：`except Exception: pass` 在 loop_engine.py 中 5 处出现，位于 verify_goal/_load_interaction_mode/run 等关键路径。一旦 state schema 漂移或 event_log I/O 失败，故障表现为"循环卡住/无输出"，极难诊断。

## 范围
- **In Scope**:
  - loop_engine.py:203-205 — state.update_field 失败时静默 pass → 加 event_log.record
  - loop_engine.py:274-277 — scan_state 阶段 state 更新失败
  - loop_engine.py:303-305 — generate_plan 阶段 state 更新失败
  - loop_engine.py:339-342 — execute_plan 阶段 state 更新失败
  - loop_engine.py:355-358 — adapt 阶段 state 更新失败
  - 对应单元测试
- **Out Scope**:
  - 不修改 fs_watcher.py 的 `except OSError: pass`（文件监听 cleanup 的标准模式）
  - 不修改 gate.py 已有 logging 的 except 块
  - 不引入新的 event type

## 关键场景
- GIVEN state.update_field() 抛出异常, WHEN 静默 pass, THEN event_log 记录 ERROR_OCCURRED 事件
- GIVEN 连续 5 处静默错误, WHEN 用户查看 event_log, THEN 五条错误日志可追溯

## 技术约束
- MUST 复用 loop_engine.py:167-173 已有的 `self.event_log.record(EventType.ERROR_OCCURRED, Severity.ERROR, ...)` 模式
- MUST NOT 删除原有 pass（保持控制流不变），仅在 pass 前追加日志
- SHOULD 每条记录包含异常信息作为 context

## 验收标准
- 5 处 `except Exception: pass` 全部替换为 `event_log.record` + pass 的双行模式
- 1-2 个回归测试验证日志写入
- 所有现有测试通过
