---
优先级: P1
来源: 2026-09-24 complete-guide-orchestrator-flow Step A.6 Oracle review — 多窗口 owner 区分依赖 `OPENCODE_SESSION_ID` 平台层真值，目前 `_rddf_resolve_owner` 5 层 fallback 链 (`env > OPENCODE_SESSION_ID > cache > proc > shell-pid`) 是 sandbox/CLI 场景的近似，非真多窗口。当前 OpenCode 未将 session UUID 注入 `$OPENCODE_SESSION_ID` 环境变量。
阶段: v4.3 (Wave 3)
分类: arch-design
类型: feature
主题: 平台层 session 注入
依赖: feat-guide-orchestrator-session-event-bus (shipped), complete-guide-orchestrator-flow (shipped 2026-09-24)
roadmap_ref:
  project_id: 完整多会话支持
  phase: phase-3
revision_count: 0
feedback_status: none
---

**优先级**: P1 | **来源**: 2026-09-24 Oracle 审查
**阶段**: v4.3 (Wave 3) | **分类**: arch-design | **类型**: feature | **主题**: 平台层 session 注入
**依赖**: feat-guide-orchestrator-session-event-bus (shipped), complete-guide-orchestrator-flow (shipped 2026-09-24)

> **完整设计**: `docs/superpowers/specs/2026-09-24-wave3-opencode-session-injection-design.md` (待写)
> **本文件为 5 段式 improvements 提案**，用于 `rdd-planner` review。

## Why

`complete-guide-orchestrator-flow` Wave 2 已 ship（ADR-0056, 2026-09-24）。W2 完成了"guide 是唯一入口"流程层契约，但**多窗口 owner 区分**仍依赖 OpenCode 平台层 `$OPENCODE_SESSION_ID` 注入。

当前 `_rddf_resolve_owner` 5 层 fallback (`skills/rddf-session/scripts/rddf_session_hooks.sh:_rddf_resolve_owner`)：
```
$OPENCODE_SESSION_ID → $RDDF_OWNER (exported) → cache file → opencode process → $$ (shell-pid)
```

第 4 层 `opencode process` 探测是 Linux 下 `/proc` 扫描，不是真 session UUID。当用户在 OpenCode 内同时打开 2 个窗口（Window A 跑 guide，Window B 跑 rdd-builder）时，两个窗口的 owner 都会 fallback 到 `shell-pid`（同一 shell 的 $$），导致：
- 2 个窗口的 session 共享 owner_opencode_session_id
- `_commands.py:67-78` 的 per-owner 同 kind 幂等逻辑误判（第二个 stage 命中"existing session_id" 而非新建）
- `_commands.py:86-98` 的 cross-stage singleton 失效（arch active + planner 创建应阻断却放过——owner 看起来一样，arch 在另一窗口却仍 ACTIVE）

真实多窗口协同在用户场景下基本不可用。Wave 1 (feat-guide-orchestrator-session-event-bus) 提供了数据结构 + 读写端 + e2e，Wave 2 提供了 hook 强制 + fail-loud，**Wave 3 缺最后一公里：平台层 session 标识符**。

## What Changes

### 方案 A（推荐，OpenCode-side）

OpenCode 平台层在每个 AI session 启动时：
- 生成 UUID `ses_<12 hex>`（与 `rds_<12 hex>` 命名一致）
- `export OPENCODE_SESSION_ID=ses_<12 hex>` 到所有子进程 env
- 在会话文档配置（`~/.opencode/sessions/`）记录映射

本地 `_rddf_resolve_owner` 简化为 1 层：直接读 `$OPENCODE_SESSION_ID`（per-step fallback 保留为兜底）。

### 方案 B（fallback，rdd-workflow-side）

若 OpenCode 平台层短期不动，rdd-workflow 在 hook 路径上额外探测：
- 读 OpenCode session 文件（`~/.opencode/sessions/{uuid}/...`）的 mtime 推断
- 引入 `RDDF_OPENCODE_SESSION_AWARE=yes` env var 启用探测

**优先方案 A**，方案 B 作为短期降级。

### 涉及文件 (方案 A)

- `OpenCode 平台代码（外部）`：session UUID 生成 + env 注入
- `_lib/rddf_session_pkg/_commands.py`：可选简化 resolve_owner 逻辑（per-platform 切到 1 层）
- `skills/rddf-session/scripts/rddf_session_hooks.sh`：`_rddf_resolve_owner` 简化 + 弃用
- `tests/integration/test_real_two_owner_poll.bats` (改名自 `test_multi_window_poll.bats`)：升级断言，从"sessions 不同"→"process-tree 真不同"

## Acceptance

- **AC-P1-3-1**: OpenCode 启动新会话时自动 `export OPENCODE_SESSION_ID=ses_<uuid>` 到所有子进程
- **AC-P1-3-2**: 2 个窗口同时运行 guide (Window A) + rdd-builder (Window B) 时，各自 hook 调用产生不同 `owner_opencode_session_id`
- **AC-P1-3-3**: Window A 的 stage_guide session 不与 Window B 的 stage_builder session 冲突（cross-stage singleton 严格生效）
- **AC-P1-3-4**: `_rddf_resolve_owner` 简化后 fallback 链 < 3 层（默认 OPENCODE_SESSION_ID → cache，仅当 unset 时再降级）

## Capabilities

### MUST (M-OPN1~5)

- **M-OPN1**: OpenCode 在每个 session 启动时生成 UUID 并 export 到子进程 env
- **M-OPN2**: UUID 格式 `ses_<12 hex>` 与 rds_ 一致
- **M-OPN3**: `OPENCODE_SESSION_ID` unset 时仍 fallback 到现有 5 层链（向后兼容 sandbox/CLI）
- **M-OPN4**: 跨窗口 session 不被 per-owner 幂等逻辑误判（多窗口真实并行）
- **M-OPN5**: 提供 `--show-session-id` CLI 帮助调试（`rddf sessions --owner <ses_id>` 列出该 owner 全部 session）

### MUST NOT (MN-OPN1~3)

- **MN-OPN1**: 不修改 `_rddf_resolve_owner` 的 5 层 fallback 链语义（向后兼容）
- **MN-OPN2**: 不修改 session.json / events.jsonl schema（per MN1）
- **MN-OPN3**: 不强制要求所有用户升级 OpenCode 版本（无感降级）

## Impact

### 用户体验
- **多窗口协同真可用**: Window A 跑 guide 观察 Window B 跑 rdd-builder，进度实时同步（per ADR-0056 G-1~G-4）
- 4 个 rdd-* skill 在多窗口下不再互相阻塞

### 代码量
- OpenCode 平台层: ~30 行 (UUID 生成 + env 注入 + session 文件)
- rdd-workflow 简化: ~20 行净减（去掉 fallback 链多余层）
- 测试: ~100 行（2-窗口 e2e + UUID 格式 + env propagation）

### 测试影响
- `tests/integration/test_rddf_session_*.bats` (4 个 owner 相关)：可降级运行时跳过（无 OpenCode 平台）
- `tests/e2e/agent/test_multi_window_poll.bats` (REAL-2P-1/2)：可升级为真多窗口

### 文档影响
- `docs/architecture/guide-orchestrator-flow.md` §5 多窗口协作：更新为"依赖 OpenCode 平台层 session 注入"
- `docs/adr/ADR-0056-guide-orchestrator-minimal-usage-flow.md` §决策 5 / Wave 3 P1-3：移除 W2.5 残留，标记完成

### 风险
- **R1 (高)**: 依赖 OpenCode 平台层 API 改动 — 若 OpenCode 团队排期延迟，本提案搁置。**缓解**: 方案 B 作为短期降级。
- **R2 (中)**: UUID 跨进程冲突（同一机器 2 个 OpenCode 实例）— 12 hex = 48 bit entropy，碰撞概率可忽略。
- **R3 (低)**: `_rddf_resolve_owner` 简化误删 fallback 链 — 测试覆盖完整，无回归。

### 依赖与协同
- 上游: OpenCode 平台层（外部项目）
- 协同: `feat-guide-orchestrator-session-event-bus` (Wave 1, 已 ship) — 数据结构就绪
- 下游: `complete-guide-orchestrator-flow` (Wave 2, 已 ship 2026-09-24) — 消费者已就位