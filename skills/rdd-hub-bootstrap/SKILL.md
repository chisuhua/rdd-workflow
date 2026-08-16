---
name: rdd-hub-bootstrap
description: 引导式初始化 rdd-hub 仓库 — 创建目录结构、Projects V2 看板、CI 工作流模板。幂等且支持 dry-run。
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

## 详细文档

参见 [`docs/rdd-hub-bootstrap.md`](../../docs/rdd-hub-bootstrap.md)。
