---
优先级: P2
来源: 2026-09-24 complete-guide-orchestrator-flow Step A.6 Oracle 审查 — 用户问 "我 5 分钟前那个 session 发生了什么？" 没有 CLI 可查；events.jsonl 数据已落但只通过 monitor --watch 被动可见，无历史回放接口。
阶段: v4.3 (Wave 3)
分类: cli
类型: feature
主题: 历史回放命令
依赖: feat-guide-orchestrator-session-event-bus (shipped), complete-guide-orchestrator-flow (shipped 2026-09-24)
roadmap_ref:
  project_id: 完整多会话支持
  phase: phase-3
revision_count: 0
feedback_status: none
---

**优先级**: P2 | **来源**: 2026-09-24 Oracle 审查
**阶段**: v4.3 (Wave 3) | **分类**: cli | **类型**: feature | **主题**: 历史回放命令
**依赖**: feat-guide-orchestrator-session-event-bus, complete-guide-orchestrator-flow
**软协同（非硬依赖）**: wave3-phase-heartbeat-progressing (P2-2) — `show --events` 是通用只读回放，对任何 event_type 有效；P2-2 接入 phase_heartbeat 后本提案的 `--kind phase_heartbeat` 查询更有意义，但 P2-4 独立 ship 不阻塞 P2-2

> **本文件为 5 段式 improvements 提案**。
> **范围**: `rddf session show --events` 命令 — 按 owner / session / kind / time-range 查询 events.jsonl 的历史。

## Why

events.jsonl (`/workspace/project/rdd-workflow/.rddf/state/events.jsonl`) 当前是**只写不读**的 append-only log：
- **写端**: 5 类 hook（entry / close / heartbeat / attach / detach）+ monitor --watch 读端
- **读端**: 仅 monitor_cmd.py:154-165 的 last 5 行渲染 + workflow_synthesizer._read_events_for_children 的全量聚合

用户问 "5 分钟前 Window B 那个 builder 跑到哪一步了？" 无法直接查 — 必须：
1. 手动 `cat events.jsonl | jq`（要懂 schema + jq 语法）
2. 或跑 `monitor --watch=1` 等待实时滚动（事件可能已 archive 归 0）

`rddf session` 子命令族 (`_lib/cli/sessions_cmd.py`) 当前仅显示 session state machine（active/completed/orphaned/abandoned），**不显示 events 历史**。

Wave 1/2 完成了事件数据层（events.jsonl + hooks + monitor），**缺最后一公里：历史回放 CLI**。本提案补 `rddf session show --events` 命令。

## What Changes

### CLI 接口

```bash
# 默认: 当前 active session 的最近 events
rddf session show --events

# 按 owner 过滤
rddf session show --events --owner ses_xxxxxxxx

# 按 session_id 过滤
rddf session show --events --session rds_xxxxxxxx

# 按 kind 过滤
rddf session show --events --kind stage_builder

# 时间范围
rddf session show --events --since "2026-09-24T01:00:00" --until "2026-09-24T02:00:00"

# 输出格式
rddf session show --events --format json | table | raw
```

### 输出格式

默认 `table`:
```
TIME                  KIND           SESSION_ID         EVENT_TYPE         MESSAGE
2026-09-24T01:15:00  stage_builder  rds_abc123def456  phase_started      rddf-session: rds_abc123...
2026-09-24T01:16:30  stage_builder  rds_abc123def456  phase_completed    rddf-session: rds_abc123...
2026-09-24T01:17:00  stage_builder  rds_abc123def456  phase_heartbeat    (after archive demo)
```

`json` 输出原始 event dict 数组（每条含 `event_id` / `ts` / `event_type` / `severity` / `message` / `context`）。

### 涉及文件

- 新增 `_lib/cli/session_show_cmd.py` (新子命令)
- `_lib/cli/sessions_cmd.py`: 注册 `show --events` 子命令分派
- 新增 `tests/unit/test_session_show_events.py` (CLI 输出 + 过滤 + 格式)

## Acceptance

- **AC-P2-4-1**: `rddf session show --events --owner <owner>` 仅输出该 owner 的 events
- **AC-P2-4-2**: `rddf session show --events --session <sid>` 仅输出该 session 的 events
- **AC-P2-4-3**: `rddf session show --events --kind <kind>` 仅输出该 kind 的 events
- **AC-P2-4-4**: `--since` / `--until` 支持 ISO 8601 时间戳格式（`2026-09-24T01:00:00` 或 `2026-09-24T01:00:00+00:00`）
- **AC-P2-4-5**: 默认 `--format table` 输出按 ts 升序（最近事件在底部）
- **AC-P2-4-6**: events.jsonl 不存在时输出 "(no events)" 而非崩

## Capabilities

### MUST (M-SE1~6)

- **M-SE1**: `rddf session show --events` 支持 `--owner` / `--session` / `--kind` / `--since` / `--until` / `--format` 6 个 flag
- **M-SE2**: 默认 `--format table` 按 `ts` 升序
- **M-SE3**: `--format json` 输出 JSON 数组（可被 jq 进一步处理）
- **M-SE4**: `--format raw` 输出一行一 event 原始 JSONL (per-line，方便 `| jq` 组合)
- **M-SE5**: archive 文件 (`events.jsonl.archive-*`) 单独列出，不混入当前 events.jsonl（除非显式 `--include-archive`）
- **M-SE6**: 过滤可组合（`--owner A --kind stage_builder` = AND）

### MUST NOT (MN-SE1~3)

- **MN-SE1**: 不修改 events.jsonl 写端语义（per MN1 兼容）
- **MN-SE2**: 不修改 sessions.json schema（per MN1）
- **MN-SE3**: 不实现事件删除/编辑命令（仅只读查询）

## Impact

### 用户体验
- **可观测性大幅提升**: 用户问"为什么我的 builder 卡住" → `rddf session show --events --owner <owner> --kind stage_builder` 看 phase_completed 是否缺失 / phase_heartbeat 是否陈旧
- 调试效率提升：告别手动 `jq` + schema 记忆

### 代码量
- 新 CLI 子命令: ~80 行 (argparse + filter + format)
- 测试: ~120 行 (filter combinations + format variants + empty events case)
- 文档更新: ~30 行 (CLARITY.md + skill metadata)

### 测试影响
- `tests/unit/test_rddf_session.py` (Wave 1 ~25 tests): 可加 `--events` roundtrip test
- 新增 `tests/unit/test_session_show_events.py`

### 文档影响
- `USAGE.md` 增加 `rddf session show --events` 使用示例
- `docs/architecture/guide-orchestrator-flow.md` §9.2 同步清单添加新测试
- `skills/rddf-session/SKILL.md` 增加 CLI 示例

### 风险
- **R1 (低)**: events.jsonl 50MB cap + 历史 archive 文件可能很大 — `--since/--until` 可缓解（默认 24h）
- **R2 (中)**: 大结果集输出卡顿（10K+ events 时 table 渲染慢）— 加 `--limit N` flag（默认 100）
- **R3 (低)**: owner 字段在 multi-window 下依赖 Wave 3 P1-3 平台层 UUID；本期未 ship 时 owner 过滤可能失效（降级到 shell-pid 重复 owner 多 session）— 接受，因为仅"过滤不精确"而非"命令崩"

### 依赖与协同
- 上游: events.jsonl 数据（Wave 1 ship + Wave 2 P2-2 task-level 字段）
- 协同: monitor_cmd.py Panel 5 (同读 events.jsonl，可共享 `_read_events_for_children` 工具函数)
- 下游: rdd-doctor 可扩展"events 健康度"巡检类别（参考 `add-cli-coverage-rdd-doctor-roadmap-rdd-hub.md` 已实现的 7 类）