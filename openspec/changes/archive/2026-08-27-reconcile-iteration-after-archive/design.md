# reconcile-iteration-after-archive — Design

## Context

2026-08-27 完成 3 个 P1 docs-consistency changes 的 ship + archive:

| Change | archive dir | iteration status |
|--------|-------------|------------------|
| sync-package-skills-to-disk | 2026-08-27-* | proposed (未更新) |
| sync-agents-md-five-stage | 2026-08-27-* | proposed (未更新) |
| rdd-doctor-docs-consistency | 2026-08-27-* | proposed (未更新) |

后果: `rddf rdd-verify` 无法识别这 3 个已 archive 的 changes,verifier 永远空队列。
期望行为: 在 `fix-iteration-archive-sync` 提案实施前,一次性 reconcile iteration.json 历史数据。
。

## Goals / Non-Goals

**Goals:**
- 一次性脚本扫描 `openspec/changes/archive/2026-08-27-*` 目录,找出所有 archive 的 changes。
- 对每个 archived change,检查 `.rddf/state/iteration.json`,如果 status 不是 `archived`,更新为 `archived` + 同步 `tasks_done = tasks_total`。
- 输出 reconcile report。
- GIVEN 3 个 P1 changes 已 archive
- GIVEN reconcile 完成后

**Non-Goals:**
- 修改 `_lib/archive.sh`(那是 `fix-iteration-archive-sync` 的 scope)
- 修复历史更早的 archive 数据(本次只处理 2026-08-27 的 3 个)

## Decisions

### 1. MUST: 使用 atomic write 保护 iteration.json

Implementation MUST satisfy this constraint.

### 2. MUST: 备份 iteration.json.before-reconcile 到 `.rddf/state/.before-reconcile/`

Implementation MUST satisfy this constraint.


## Risks / Trade-offs

- No identified risks beyond standard implementation discipline.

- **SHOULD**: SHOULD: 提供 `--dry-run` 模式预览