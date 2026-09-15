---
name: rdd-env-check
description: |
  Env health check: openspec CLI / git workspace / branch / build dir.

  Invoke when BOTH:
    1. Each rdd-arch/rdd-planner/rdd-builder phase first screen
    2. `.rddf/state/.env-cache.json` stale (>3600s) or branch-changed

  Default: TTL 3600s + branch invalidation; non-blocking.

  Boundary ownership: see role.boundaries.owns / not_owns.
license: MIT
compatibility: Requires bash + git + openspec CLI; 无需 jq/python3
metadata:
  author: rdd-workflow
  version: 1.0
  evolved-from: "skills/rdd-arch/scripts/arch_env_check.sh"
  user-invocable: true
---

# rdd-env-check

## 调用方式

```bash
source "$(resolve_rdd_skill_dir rdd-env-check)/scripts/env_check.sh"
_run_env_check_cached   # 推荐入口: 读 cache, 命中输出单行; miss 现场跑
_run_env_full_check     # 强制全量检查 (写 cache + 输出 10 字段 JSON)
```

## JSON / Cache 契约

- 固定路径: `.rddf/state/.env-cache.json` (gitignored)
- 默认 TTL: 3600 秒; 覆盖: `RDD_ENV_CACHE_TTL` (设 0 恒失效)
- 固定 15 字段: `timestamp` `ttl_s` `branch` `openspec_ver` `git_clean` `build_dir` `adr_count` `roadmap_exists` `gap_count` `active_changes` `discovered_adr_dir` `discovered_roadmap_path` `discovered_architecture_dir` `discovered_adr_pattern` **`gh_available`**
- `gh_available` 三态: `yes:<user>` (安装 + 认证) / `no:gh-missing` / `no:not-authed` — 用于 ADR-0027 reporter 前置依赖检测, **不** 阻断 phase 入口 (缺 gh 仅使 reporter L2 路径不可用, L1 本地文件仍可用)
- 原子写: `.tmp` → `mv` (同目录 rename)
- 失效条件: 文件缺失 / mtime 超 TTL / `cache.branch != git branch --show-current`
- 命中输出: `✅ Env OK (cached Xm ago) | ADR:N | Roadmap:✓ | GH:<status>` (单行)
- 缓存**不保存** token / 绝对路径 / git remote 等敏感信息

## 失败行为

- openspec CLI 缺失 → 打印修复指引 (`npm install -g openspec-cli`), 退出码非 0 (阻断 phase 进入)
- 任何失效/缺失 → 降级现场全量检查, 对直接调用用户透明

## .gitignore 硬防护检测 (add-gitignore-hard-protection)

全量检查 (`_run_env_full_check`) 额外跑 `_check_gitignore`（非阻塞, 不影响 15 字段 cache 契约）:

| `.rddf/project.yaml` `git.openspec_tracked` | `.gitignore` 含 `openspec/` | 行为 |
|---|---|---|
| `false` | 缺失 | ⚠️ warn "gitignore guard missing"（`git add -A` 会把 openspec/ 重新拉进 git） |
| `false` | 有 | ✅ 静默 (`_GITIGNORE_PROTECTED=yes`) |
| `true`/缺省 | 有 | ⚠️ 反向不一致（commit_archive_moves 会 git add 被 ignore 的路径 → 空 commit） |
| 缺省 | 缺失 | 静默（传统 tracked 项目） |

Auto-fix (opt-in): `RDDF_ENV_FIX_GITIGNORE=yes` → 幂等追加 `openspec/` 到 `.gitignore`（仅 false+缺失场景）。默认只报告不改文件。

## 边界

- 自动缓存 ADR-0016 工件发现 (opt-out via `SKIP_AUTO_DISCOVERY=yes`)
- 不修改 rddf-session 协议 (本 cache 是其同目录伴随状态文件)
