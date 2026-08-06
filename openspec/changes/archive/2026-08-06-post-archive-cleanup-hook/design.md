# post-archive-cleanup-hook — Design

> Schema: spec-driven
> Created: 2026-08-06
> See: `proposal.md` (motivation/scope) + `tasks.md` (implementation steps).

## Context

rdd-workflow 的 archive 流程 (`_lib/archive.sh::archive_change` 和 `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode`) 当前是**分散的、按文件类型重复实现**的清理链:

```
archive_change                      archive_change_for_mode
  └→ openspec archive <name>         └→ openspec archive <name>
  └→ cleanup_worktree_and_branch     └→ cleanup_worktree_and_branch
  └→ commit_archive_moves (3 paths)  └→ update_proposal_status
  └→ cleanup_plan_handoff            └→ cleanup_plan_handoff
  └→ cleanup_plan_file               └→ cleanup_plan_file
```

3 个独立 bug 共同导致 `archive(fix-rddf-init-broken-layout)` (commit 9f31a68) 后残留 `.rddf/plans/fix-rddf-init-broken-layout.md`(deleted,但 git index 仍有条目):

1. `ship_archive.sh:256 cleanup_plan_file` 用 `rm -f` 而非 `git rm`
2. `_lib/archive.sh:515 commit_archive_moves` 只 stage 3 个路径(`openspec/changes/<n>/`、`openspec/changes/archive/`、`openspec/specs/`),不处理 `.rddf/`
3. `_lib/state.sh:452 check_dirty_key_files` 是 sentinel(只警告不修复)

`scan-state.sh` 检测到这些残留时输出 `⚠️  关键文件有未提交更改` 警告,但不修复。

## Goals / Non-Goals

**Goals:**
- 用单个 idempotent bash hook 取代分散的清理逻辑,统一处理 3 类残留
- 双 mode 接入(`archive_change` + `archive_change_for_mode`),行为一致
- 严格白名单:`.rddf/plans/`、`.rddf/state/<change>*`、`openspec/changes/<change>/`、`proposal-approved.md` 等已知 hook-owns 文件 — **不动** `tasks.md` / `docs/adr/` / `roadmap.md` 等用户手工修改
- 自动 commit `git rm` 的删除项,commit message 格式 `chore(post-archive): clean residue from <change-name>`;不自动 commit modified

**Non-Goals:**
- 不修改 `openspec archive` CLI
- 不处理 untracked build 产物(留 follow-up)
- 不替换 `check_dirty_key_files`(继续作为 sentinel 层)

## Decisions

| 决策 | 备选 | 选定 | 理由 |
|---|---|---|---|
| **白名单策略** vs 通用所有 deleted | 通用 | 白名单 | 避免 `git checkout -- <file>` 误删用户工作 |
| **集成到 archive_change** vs 独立 CLI | 集成 | 集成 | 用户已默认 archive 是"原子",独立 CLI 会被忘 |
| **自动 commit `git rm` 项** vs 仅 stage | 自动 | 自动(消息 `chore(post-archive): clean residue from <change>`) | 不留 dangling 索引条目 |
| **不动 modified files** vs 也自动 commit | 不动 | 不动(`git add` 但不 commit) | modified 是用户意图,擅自 commit 风险高 |
| **SKIP env var escape** | 无 | `SKIP_POST_ARCHIVE_CLEANUP=yes` | 测试 + 紧急 escape |
| **DRY_RUN mode** | 无 | `DRY_RUN_POST_ARCHIVE_CLEANUP=yes` | 调试时只 echo 不执行 |

## Risks / Trade-offs

- **Risk:** 白名单不覆盖未来新 case (e.g. `.rddf/state/<change>/*.json`) → 用户下次又看到残留
  - **Mitigation:** 白名单用单一变量数组,加新路径只改 1 行
- **Risk:** auto-commit 引入噪音(每次 archive 多一个 chore commit)
  - **Mitigation:** idempotent + `DRY_RUN=yes` + 用户可 `git reset` 撤销
- **Risk:** worktree 模式下 `cleanup_worktree_and_branch` 之后跑 hook,如果主仓库 worktree 不存在可能失败
  - **Mitigation:** hook 检测 cwd 不在 main_root 时 bail,显式报错而非静默

## Migration Plan

1. 部署 `_lib/post_archive_cleanup.sh`(新文件,不放 `_lib/archive.sh` 内)
2. 在 `_lib/archive.sh::archive_change` 和 `ship_archive.sh::archive_change_for_mode` 的 `cleanup_plan_file` 调用之后插入 hook 调用
3. 现有 `cleanup_plan_file` 函数保留(向后兼容),可后续 PR 移除
4. 跑 `bats tests/integration/test_post_archive_cleanup_hook.bats` + 现有回归

## Open Questions

- 是否要在 hook commit message 里加 Co-authored-by 或 `#noverify`?等实施时看 maintainer 偏好
- `proposal-approved.md` git add 后是否给用户一个 "please commit before next guide" 的提示?目前用现有 `check_dirty_key_files` 即可

## Cross-Reference

- 祖先提案:`archive-cleanup-working-tree` (P1) → `archive-cleanup-plan-files` (P2) → `add-archive-post-commit-hook-and-force-flag`(已合)
- 相关 ADR:ADR-0007 (gate-mechanism)、ADR-0017 (rddf-session)、ADR-0024 (deps-driven execution mode)
