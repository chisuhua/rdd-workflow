---
name: rdd-hub-bootstrap
description: |
  Hub repo (rdd-hub) bootstrap: dir structure + Projects V2 board + CI templates.

  Invoke when BOTH:
    1. GitHub Org exists + need Projects V2 board for cross-repo federation
    2. Hub repo does not exist OR needs re-bootstrap

  Default: idempotent + dry-run capable; requires `gh` CLI v2.0+.

  Boundary ownership: see role.boundaries.owns / not_owns.
license: MIT
compatibility: Requires gh CLI v2.0+ and GitHub Org membership.
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "ADR-0030 Hub-and-Spoke 联邦架构 Step 1"
  user-invocable: true
---

# RDD Hub Bootstrap

初始化独立的 `rdd-hub` 仓库,作为跨项目协同的 SSOT(Single Source of Truth)。

## 调用

```bash
skill_use("rdd-hub-bootstrap")
# 等价于:
bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --org <org> --repo rdd-hub
```

## 标志

| Flag | 含义 |
|------|------|
| `--org <org>` | GitHub Org 名称 |
| `--repo <repo>` | Hub 仓库名(默认 `rdd-hub`) |
| `--dry-run` | 模拟运行,不调用任何 GitHub API |

## 前置条件

- `gh` CLI v2.0+ 已安装
- `gh auth login` 已认证
- 当前用户是目标 Org 的 member(不需要 Owner)

## 使用说明（自包含快速入门）

`rdd-hub-bootstrap` 用于初始化独立的 `rdd-hub` 仓库，作为跨项目协同的 SSOT（Single Source of Truth）。适用场景：多个项目间需要共享 OpenAPI contract、Issue 追踪或跨项目变更协调。

**前置条件**：`gh` CLI v2.0+ 已安装并认证，当前用户是目标 GitHub Org 的 member（不需要 Owner）。

**常用命令**：
- 引导 Hub 仓库：`bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --org <org> --repo rdd-hub`
- 干运行（不调 API）：`bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --org <org> --dry-run`

**入口**：`skill_use("rdd-hub-bootstrap")` 等价于上述命令。

安装后可通过 `install.sh --with-docs` 获取完整架构文档（仓库根 `docs/rdd-hub-bootstrap.md`）。
