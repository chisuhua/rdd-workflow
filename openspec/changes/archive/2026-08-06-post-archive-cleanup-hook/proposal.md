# post-archive-cleanup-hook

## Why

已批准但实现不完整的祖先提案(链路依赖):

- `archive-cleanup-working-tree` (P1, 2026-07-28) — 仅覆盖 `openspec/changes/<name>/` 残留
- `archive-cleanup-plan-files` (P2, 2026-07-29) — 覆盖 `.rddf/plans/<name>.md`,但实现用 `rm -f` 而非 `git rm` → **当前 bug 的根因**
- `add-archive-post-commit-hook-and-force-flag` — 已落 `commit_archive_moves` 辅助函数(只 `git add` 3 个路径:openspec/changes/<name>/、openspec/changes/archive/、openspec/specs/)

**相关 ADR**:ADR-0017 (rddf-session)、ADR-0024 (deps-driven execution mode)、ADR-0007 (gate-mechanism)。

**根因(基于实际代码审计)**:

`archive_change` 的清理链是分步、分离的:

```
archive_change (worktree mode)        archive_change_for_mode (lightweight mode)
  └→ openspec archive <name> --yes      └→ openspec archive <name> --yes
  └→ cleanup_worktree_and_branch        └→ cleanup_worktree_and_branch
  └→ commit_archive_moves (3 paths)     └→ update_proposal_status (proposal-approved.md touched)
  └→ cleanup_plan_handoff               └→ cleanup_plan_handoff
  └→ cleanup_plan_file                  └→ cleanup_plan_file
```

3 个独立 bug 共同导致 `.rddf/plans/<name>.md` 残留:

1. `ship_archive.sh:256 cleanup_plan_file` 用 `rm -f` 删文件,**不调用 `git rm`** → 文件从磁盘消失,但 git index 仍把它当 tracked → git status 报告 " D"
2. `_lib/archive.sh:515 commit_archive_moves` 仅 `git add` 3 个路径,不处理 `.rddf/` → 即使 plan file 已 `rm` 也没人 stage 这个删除
3. `_lib/state.sh:452 check_dirty_key_files` 是 **sentinel**(只警告不阻断不修复)——不替代自动 cleanup

用户痛点:**今天 `archive(fix-rddf-init-broken-layout)` commit 9f31a68 之后**,残留 `.rddf/plans/fix-rddf-init-broken-layout.md` (deleted - 未提交),下次启动 `guide` 时看到 `⚠️ 关键文件有未提交更改: proposal-approved.md` + working tree 2 issues 的警告。

## What Changes

**In Scope**:

- 新增 `_lib/post_archive_cleanup.sh`(bash,与 `_lib/archive.sh` 同风格),导出公开函数 `post_archive_cleanup <project_root> [change_name]`
- 单一 idempotent pass:`git status --porcelain` 全扫,按白名单分类处理 3 类残留:
- **deleted tracked**:`git rm -f` 白名单内路径(`.rddf/plans/`、`.rddf/state/<change_name>*.json`、`openspec/changes/<change_name>/`)
- **modified critical files**:`git add` 白名单(`proposal-approved.md`、`proposal-suggestions.md`、`roadmap.md`)— 不自动 commit,留待用户
- **deleted critical tracking files**:`git rm` 同上
- 双路径接入:`_lib/archive.sh::archive_change` 和 `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode` 都调用 hook(在 archive 主体成功后、`commit_archive_moves` 之后)
- 自动 commit 已 `git rm` 的删除项,commit message 格式:`chore(post-archive): clean residue from <change-name>`(idempotent:无残留即 no-op,不创建空 commit)

### 关键场景

- GIVEN archive 主体成功完成, WHEN `post_archive_cleanup <project_root> <change>` 触发, THEN `openspec/changes/<change>/` 已 `git rm`(残留索引条目消失)
- GIVEN `.rddf/plans/<change>.md` 是 ` D ` (deleted) 状态, WHEN hook 触发, THEN 该文件已 `git rm -f`,且在下一 commit 包含 `chore(post-archive)` 类型 commit
- GIVEN `proposal-approved.md` 在 archive 期间被 `update_proposal_status` 改动, WHEN hook 触发, THEN 文件已 `git add`(索引已更新),但不在 hook 自己的 commit 里
- GIVEN 已 archive 后再调 hook(no-op 场景), WHEN 触发, THEN exit 0 且不创建空 commit
- GIVEN worktree mode, WHEN hook 在 `main_root` 跑, THEN 不污染 worktree 当前分支
- GIVEN lightweight mode, WHEN hook 在 `current_branch` 跑, THEN working tree clean
- GIVEN hook 在 dirty 用户分支(`tasks.md` 改、`docs/adr/*.md` 改)上跑, WHEN 触发, THEN 白名单外文件不动,hook commit 只含白名单内变更

**Out of Scope**:

- 不修改 `openspec archive` CLI 自身行为
- 不处理 untracked build 产物(留 follow-up)
- 不自动 commit `tasks.md`、`docs/adr/`、`.rddf/state/sessions.json`、`roadmap.md` 等用户手工修改文件
- 不替换 `_lib/state.sh::check_dirty_key_files`——继续作为 sentinel 警告层
- 不动现有 `cleanup_plan_file` 函数(本次 hook 接管其职责,可后续在合并 PR 中删除)

## Capabilities

- MUST **idempotent**——残留已清无报错;残留不存在则 no-op(无空 commit)
- MUST 用 `git rm -f` 而非 `rm`,保证索引同步
- MUST 仅处理白名单内路径(避免污染 `tasks.md`/其他 dirty 文件)
- MUST 双 mode 都接入(`archive_change` + `archive_change_for_mode`)
- MUST auto commit 仅限已 `git rm` 的删除项,不自动 commit modified untracked
- MUST **NOT** 自动 commit 用户手工修改文件(只 stage `proposal-approved.md` 等已知 hook-owns 文件)
- MUST **NOT** 删除 untracked 文件(避免误删用户工作)
- SHOULD 提供 `SKIP_POST_ARCHIVE_CLEANUP=yes` 旁路(测试/紧急 escape)
- SHOULD 提供 `DRY_RUN_POST_ARCHIVE_CLEANUP=yes` 模式(只 echo 不执行任何 git 操作)
- SHOULD 每个被处理文件输出一行 `🧹 cleaned: <path>`,便于 `bats` 测试断言

## Impact

- MUST **idempotent**——残留已清无报错;残留不存在则 no-op(无空 commit)
- MUST 用 `git rm -f` 而非 `rm`,保证索引同步
- MUST 仅处理白名单内路径(避免污染 `tasks.md`/其他 dirty 文件)
- MUST 双 mode 都接入(`archive_change` + `archive_change_for_mode`)
- MUST auto commit 仅限已 `git rm` 的删除项,不自动 commit modified untracked
- MUST **NOT** 自动 commit 用户手工修改文件(只 stage `proposal-approved.md` 等已知 hook-owns 文件)
- MUST **NOT** 删除 untracked 文件(避免误删用户工作)
- SHOULD 提供 `SKIP_POST_ARCHIVE_CLEANUP=yes` 旁路(测试/紧急 escape)
- SHOULD 提供 `DRY_RUN_POST_ARCHIVE_CLEANUP=yes` 模式(只 echo 不执行任何 git 操作)
- SHOULD 每个被处理文件输出一行 `🧹 cleaned: <path>`,便于 `bats` 测试断言

## Acceptance

- [ ] **新单元测试**:`tests/integration/test_post_archive_cleanup_hook.bats`,≥8 场景覆盖全部 GIVEN/WHEN/THEN + idempotent + dry-run + skip 旁路
- [ ] **现有回归**:`bats tests/integration/test_ship_*.bats` + `pytest tests/unit/` + `pytest tests/integration/` 全绿
- [ ] **根因验证**:对当前残留 `.rddf/plans/fix-rddf-init-broken-layout.md` 跑 hook(独立重放场景的 bats 测试),结果:`git status --porcelain` 不再报告该文件,且新增 1 个 `chore(post-archive): clean residue from fix-rddf-init-broken-layout` commit
- [ ] **双 mode 验证**:独立 bats 测试覆盖 worktree mode 和 lightweight mode 两条 archive 路径都跑通 hook
- [ ] **白名单边界验证**:测试在 dirty 用户分支上跑 hook,确认 `tasks.md`、`docs/adr/*.md`、`.rddf/state/sessions.json` 不被动
- [ ] **架构稳固性**:未来加新 case(如 `.rddf/state/<change>/*.json` 残留)只需扩展 `_WHITELIST_DELETED_PATHS` 数组,不动 hook 主体架构
- [ ] **文档同步**:更新根 `AGENTS.md` 的 "Worktree Commit Flow" 段,把 hook 调用点插图;`docs/adr/` 不新增 ADR(本次修复范围属于 ADR-0017 应用层,无需新决策)

