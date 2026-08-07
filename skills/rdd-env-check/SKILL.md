---
name: rdd-env-check
description: 独立环境健康检查 skill — 检查 openspec CLI / git 工作区 / branch / build 目录，维护 `.rddf/state/.env-cache.json` 环境快照 (TTL 3600s + branch 失效)，输出单行状态供各 phase 首屏使用。被 guide-arch/guide-design/guide-plan/guide-ship Phase 1 调用。
license: MIT
compatibility: Requires bash + git + openspec CLI; 无需 jq/python3
metadata:
  author: rdd-workflow
  version: 1.0
  evolved-from: "skills/guide-arch/scripts/arch_env_check.sh"
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
- 固定 14 字段: `timestamp` `ttl_s` `branch` `openspec_ver` `git_clean` `build_dir` `adr_count` `roadmap_exists` `gap_count` `active_changes` `discovered_adr_dir` `discovered_roadmap_path` `discovered_architecture_dir` `discovered_adr_pattern`
- 原子写: `.tmp` → `mv` (同目录 rename)
- 失效条件: 文件缺失 / mtime 超 TTL / `cache.branch != git branch --show-current`
- 命中输出: `✅ Env OK (cached Xm ago) | ADR:N | Roadmap:✓` (单行)
- 缓存**不保存** token / 绝对路径 / git remote 等敏感信息

## 失败行为

- openspec CLI 缺失 → 打印修复指引 (`npm install -g openspec-cli`), 退出码非 0 (阻断 phase 进入)
- 任何失效/缺失 → 降级现场全量检查, 对直接调用用户透明

## 边界

- 自动缓存 ADR-0016 工件发现 (opt-out via `SKIP_AUTO_DISCOVERY=yes`)
- 不修改 rddf-session 协议 (本 cache 是其同目录伴随状态文件)
