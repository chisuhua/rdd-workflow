# fix-iteration-archive-sync — Design

## Context

`openspec archive <name> --yes` 命令成功移动 change 到 `openspec/changes/archive/` 子目录,但**不更新** `.rddf/state/iteration.json` 中该 change 的 status,导致其仍为 `proposed`。
后果:

- `rddf rdd-verify` 的 `scan_queue.sh` 扫描 `status in (in_worktree, completed)` 的 changes,完全找不到已归档的 change — verifier 队列为空,ADR-0034 规定的自动 AC 验证失效。
- 状态机不一致: 目录层面已归档,但 iteration.json 视角仍是"待执行"。

## Goals / Non-Goals

**Goals:**
- `_lib/archive.sh::archive_change` 和 lightweight 模式路径在 `openspec archive` 成功后调用 `iteration.add_or_update_change(name, status='archived')`。
- 同步更新 `tasks_done = tasks_total`(archive 时所有 task 完成)。
- audit log `.cross-repo-audit.jsonl` 追加 `archive` 事件。
- archive auto-commit 失败时,iteration 更新应优先于 commit(状态机一致性优先于 git 持久化)。
- GIVEN 3 个 change 已 `archive` 但 iteration.json 仍是 `proposed`

**Non-Goals:**
- 修复 `iteration.json` 当前 3 个 pending 的"proposed" 状态(本提案生效前的历史数据)。
- 改 `iteration.json` schema(`status` 枚举扩展)。

## Decisions

### 1. MUST: archive hook 失败时,iteration 更新回滚(避免目录在 archive/ 但 iteration 状态不一致)

Implementation MUST satisfy this constraint.

### 2. MUST: `iteration.json` 写入使用 atomic write(`_lib/core/atomic_write.atomic_write_json`)

Implementation MUST satisfy this constraint.


## Risks / Trade-offs

- No identified risks beyond standard implementation discipline.

- **SHOULD**: SHOULD: 在 audit log 中记录 archive 事件 + iteration 同步结果
- **SHOULD**: SHOULD NOT: 在 archive_auto_commit 阶段才同步 iteration(应在目录移动后立即同步)