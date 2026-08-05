# developer-experience-observability — Design

## Context

本次会话中 hook 在必要注释上多次误报:
- `BASH_SOURCE[0]` direct-execution guard 注释(必要,因为 bash idiom 不直观)
- 100ms→150ms timing threshold 解释注释(必要,防止未来维护者"修复"回 100ms)
- worktree 源 LSP 错误(实际是 worktree 隔离的副作用,非代码 bug)

此外,缺乏工具调用统计和失败重试数据,工作流改进无数据基础(本次 session 复盘只能凭记忆)。

## Goals / Non-Goals

**Goals:**

- hook 白名单规则:
  - bash idiom 注释(`BASH_SOURCE`, `set -u`, `set -e`, `set -o pipefail`)
  - "为什么是这个数字/值"的注释(timing threshold, retry counts, magic numbers)
  - TODO 引用(issue/ticket 编号)
- `.rddf/state/session_stats.json`:
  - 工具调用计数(bash, read, edit, write, task)
  - 失败重试次数(子代理超时、配额耗尽)
  - 阶段耗时(plan, execute, archive)
- 工作流改进的数据可视化(可选,后续)

**Non-Goals:**

- 修改 hook 工具本身
- 实时监控仪表板
- 跨 session 统计聚合(后续迭代)

## Decisions

### Hook 白名单

扩展项目级 hook 配置(假设在 `opencode.json` 或类似):
```yaml
hooks:
  comment_check:
    whitelist_contexts:
      - "bash_idiom"      # BASH_SOURCE, set -u, etc.
      - "magic_number"    # timing, retry, threshold
      - "ticket_ref"      # TODO(bug-123)
```

或直接在 hook 实现中加入 `skip_if_comment_matches` 规则,匹配正则:
```
^\s*#\s*(BASH_SOURCE|set -[uoe]+|set -o pipefail|Threshold|TODO\([a-z]+-\d+\))
```

### Session Stats

```python
# skills/_lib/session_stats.py
@dataclass
class SessionStats:
    tool_calls: Dict[str, int] = field(default_factory=dict)
    failures: List[FailureRecord] = field(default_factory=list)
    phase_durations: Dict[str, float] = field(default_factory=dict)

    def record(self, tool: str):
        self.tool_calls[tool] = self.tool_calls.get(tool, 0) + 1
```

session 结束时(guide-ship close hook 或 orchestrator 退出)写入 `.rddf/state/session_stats.json`:
```json
{
  "session_id": "ses_xxx",
  "tool_calls": {"bash": 60, "read": 15, "edit": 25, "task": 8},
  "failures": [
    {"type": "quota_exceeded", "tool": "task", "count": 5, "timestamp": "..."}
  ],
  "phase_durations": {"plan": 1200, "execute": 1800, "archive": 300}
}
```

## Risks / Trade-offs

- **正向**: hook 噪音减少,必要注释不再误报,降低开发摩擦
- **正向**: 工作流改进有数据基础(可识别瓶颈、回归对比)
- **风险**: session_stats 增加少量写入开销(<1ms 每次 record)
- **兼容性**: 不破坏现有 hook 行为,仅添加白名单

## Migration Plan

1. 本提案在主仓库实施,通过 guide-plan + guide-ship 工作流
2. 执行完成后 openspec archive 归档到 openspec/changes/archive/YYYY-MM-DD-developer-experience-observability/
3. 不涉及运行时数据迁移(纯 workflow 增强)

## Open Questions

无 — 提案中所有关键场景(S1-S6 等)已定义清晰。
