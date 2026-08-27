---
name: report-issue
description: Hub-Spoke 上行命令 — 在 rdd-hub 创建 [RFC] issue 并记录到本地 .rddf/state/.cross-repo-pending.json。被 OpenSpec 工作流各阶段（arch / plan / ship / verify）的 phase-exit hooks 调用以上报 agent-plane 异常。ADR-0030 §Hub-Spoke 联邦 + ADR-0027 L2 上报契约。
license: MIT
compatibility: Requires Python 3.11+, gh CLI v2.0+, GitHub Org membership (or GITHUB_TOKEN env var)
metadata:
  author: rdd-workflow
  version: "1.0"
  evolved-from: "report-issue CLI command v2.0 (2026-08-19)"
  user-invocable: true
---

# OpenSpec 工作流 — report-issue (Hub-Spoke 上行)

Hub-Spoke 联邦的**上行通道**:将本地工作流异常以 `[RFC]` issue 形式上报到 `rdd-hub` 仓库,关联 RDD Cross-Repo Sync Project V2,记录到 `.rddf/state/.cross-repo-pending.json`。

**职责边界**:
- **角色定义**: 见 frontmatter `role:` 字段 (ADR-0028)
- **拥有**: `.rddf/state/.cross-repo-pending.json` (本地挂起状态)
- **不拥有**: `rdd-hub/` 仓库本身 (Hub 端)
- **人工介入程度**: **低** (CLI 自动执行,L2 上报需三重 opt-in)

**调用方式**:

```bash
# 自动 (phase-exit hooks)
rddf report-issue --category=flow-bug --phase guide-ship --exit-code 1 "auto-detected anomaly"

# 手动 (用户主动上报)
RDDF_REPORT_GH_REPO=org/rdd-hub rddf report-issue \
    --category=rfc \
    --title "[RFC] 重构用户鉴权流程 (Auth V2)" \
    --stakeholders "org/repo-backend,org/repo-data" \
    --gate "Design-Gate" \
    --contract-impact "Breaking-Change"

# 仅 dry-run (不提交)
rddf report-issue --no-submit --category=rfc --title "..." --body "..."
```

**前置条件**:
- `gh` CLI v2.0+ 已安装并认证 (`gh auth status`)
- GitHub Org 成员 (有写权限) 或设置 `GITHUB_TOKEN`
- `RDDF_REPORT_GH_REPO` 环境变量 (默认 `chisuhua/rdd-workflow`)

**安全边界 (per ADR-0027 L2 上报契约)**:
- 默认 **NO** auto-submit (`--no-submit` is default)
- 三重 opt-in: `RDDF_REPORT_ENABLED=yes` + `RDDF_REPORT_AUTO_SUBMIT=yes` + `RDDF_REPORT_SUBMIT_CATEGORIES=...`
- CI 环境自动禁用 (`CI/GITHUB_ACTIONS/JENKINS_URL` 检测)
- 失败 fallback: 写入本地 `.rddf/issues/`,由用户/管理员事后审查

**审计日志**:
- 每次上报追加到 `.rddf/state/.cross-repo-audit.jsonl` (decision=approve/reject/bypass)
- 失败时自动记录 Hub state (open/closed/error) + labels (rfc/cross-repo/...)

详见 [ADR-0030-hub-and-spoke-federation.md](docs/adr/ADR-0030-hub-and-spoke-federation.md) §Hub-Spoke 协议 + [ADR-0027-continuous-evolution.md](docs/adr/ADR-0027-continuous-evolution.md) §L2 上报契约。
