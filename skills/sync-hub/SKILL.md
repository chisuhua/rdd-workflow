---
name: sync-hub
description: Hub-Spoke 下行命令 — 从 rdd-hub 拉取 contract 到本地 openspec/specs/<name>/spec.md。Hub Spoke 联邦的下行同步通道,被 contract-check 和 guide-design 在 contract refresh 时调用。ADR-0030 §Hub-Spoke 联邦。
license: MIT
compatibility: Requires Python 3.11+, gh CLI v2.0+, GITHUB_TOKEN env var (read access)
metadata:
  author: rdd-workflow
  version: "1.0"
  evolved-from: "sync-hub CLI command v1.0 (2026-08-16)"
  user-invocable: true
---

# OpenSpec 工作流 — sync-hub (Hub-Spoke 下行)

Hub-Spoke 联邦的**下行通道**:从 `rdd-hub/contracts/` 拉取契约到本地 `openspec/specs/<name>/spec.md`,让 Spoke 实现始终与 Hub 端契约保持一致。

**职责边界**:
- **角色定义**: 见 frontmatter `role:` 字段 (ADR-0028)
- **拥有**: `openspec/specs/<name>/spec.md` (从 Hub 拉取的契约)
- **不拥有**: Hub 仓库 (`rdd-hub/contracts/`)
- **人工介入程度**: **中** (Hub 端契约变更需用户 review 是否影响本地)

**调用方式**:

```bash
# 拉取单个 contract
RDDF_HUB_REPO=org/rdd-hub rddf sync-hub --contract auth-v2.yaml

# 拉取所有 contracts
rddf sync-hub --all

# Dry-run (预览变化)
rddf sync-hub --contract auth-v2.yaml --dry-run
```

**前置条件**:
- `gh` CLI 已认证 (read access to `rdd-hub`)
- `RDDF_HUB_REPO` 环境变量 (默认 `chisuhua/rdd-hub`)
- 本地 `openspec/specs/` 目录存在 (OpenSpec init 后)

**缓存**:
- 24h TTL 缓存 (`.rddf/state/.cross-repo-deps-cache.json`)
- SHA 指纹绑定 (防止 silent drift)

**Breaking-Change 处理**:
- Hub contract 含 `breaking-change: true` 标签 → `contract-check` 升级为 `STRICT_CONTRACT_GATE=yes` 阻断 CI
- 本地实现需先更新到新 contract 才能 merge (按 `enforce-plan-tdd-5step-new`)

**失败 fallback**:
- Hub 网络故障 → 使用本地 cache + emit warning (non-blocking)
- Auth 失败 → fail-closed (不静默)

详见 [ADR-0030-hub-and-spoke-federation.md](docs/adr/ADR-0030-hub-and-spoke-federation.md) §Hub-Spoke 协议 + [ADR-0018-arch-quality-gate.md](docs/adr/ADR-0018-arch-quality-gate.md) §contract-check 集成。
