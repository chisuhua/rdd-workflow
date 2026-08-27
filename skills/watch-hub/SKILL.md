---
name: watch-hub
description: Hub-Spoke 监听命令 — 一次性轮询 Hub issue 状态。由 cron/CI 以 ≤5 分钟间隔调度(不在 CLI 内维护长驻 daemon)。Hub-Spoke 联邦的状态同步通道。ADR-0030 §Hub-Spoke 联邦。
license: MIT
compatibility: Requires Python 3.11+, gh CLI v2.0+, GITHUB_TOKEN env var (read access)
metadata:
  author: rdd-workflow
  version: "1.0"
  evolved-from: "watch-hub CLI command v1.0 (2026-08-16)"
  user-invocable: true
---

# OpenSpec 工作流 — watch-hub (Hub-Spoke 监听)

Hub-Spoke 联邦的**状态同步通道**:一次性轮询 `rdd-hub` 上的 `[RFC]` issue 状态,更新本地 `.rddf/state/.cross-repo-pending.json`。

**职责边界**:
- **角色定义**: 见 frontmatter `role:` 字段 (ADR-0028)
- **拥有**: `.rddf/state/.cross-repo-pending.json` (本地挂起状态)
- **不拥有**: Hub 仓库 issue state
- **人工介入程度**: **低** (CLI 自动执行,无需用户决策)

**调用方式**:

```bash
# 一次性轮询 (推荐 — 由 cron/CI 调度)
RDDF_HUB_REPO=org/rdd-hub rddf watch-hub --once

# 持续轮询 (默认 60s 间隔,按 Ctrl+C 退出)
rddf watch-hub --interval 60

# Dry-run
rddf watch-hub --once --dry-run
```

**前置条件**:
- `gh` CLI 已认证 (read access to `rdd-hub`)
- `RDDF_HUB_REPO` 环境变量 (默认 `chisuhua/rdd-hub`)

**调度模式 (关键约束)**:
- **不在 CLI 内维护长驻 daemon** — daemon 模式会增加 system service 复杂度
- 由 cron / GitHub Actions / systemd timer 等调度 (≤5 分钟间隔)
- 每次执行都是**幂等**:同一 Hub 状态多次 poll 不会产生重复 audit entry

**审计日志**:
- 每次 poll 追加到 `.rddf/state/.cross-repo-audit.jsonl` (decision=poll)
- Hub state 变化时 (open → approved) 才记录 decision=approve

详见 [ADR-0030-hub-and-spoke-federation.md](docs/adr/ADR-0030-hub-and-spoke-federation.md) §Hub-Spoke 协议 + [ADR-0017-rddf-session.md](docs/adr/ADR-0017-rddf-session.md) §workflow group 跨会话。
