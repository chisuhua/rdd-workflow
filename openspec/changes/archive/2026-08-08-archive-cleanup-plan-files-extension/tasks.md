# Tasks — archive-cleanup-plan-files-extension

## 1. Implementation

- [x] 1.1 在 `_lib/post_archive_cleanup.sh` 的 `_WHITELIST_DELETED_PATTERNS` 数组追加 `"openspec/changes/"` (不含 trailing slash 的也行，但建议保留 trailing slash 以便精确匹配)
- [x] 1.2 在 `post_archive_cleanup` 主循环的 ` D` 分支增加 archive-presence 检查：
  - 提取 path 第 3 段作为 `<name>`
  - 使用 `compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-$name"` 验证 archive 存在
  - 跳过 `openspec/changes/archive/` 前缀的路径
- [x] 1.3 添加一次 `git rm -f` 调用 (沿用现有 `_WHITELIST_DELETED_PATTERNS` 路径,无需 `git rm -r`)
- [x] 1.4 扩展 `scripts/cleanup-plan-files.sh` 接受 `--include-change-artifacts` 标志,内部追加 6 类清理逻辑 + 交互确认

## 2. Unit Tests (8 bats)

- [x] 2.1 `test_whitelist_includes_openspec_changes` — 验证 `_WHITELIST_DELETED_PATTERNS` 数组包含 `openspec/changes/`
- [x] 2.2 `test_matches_prefix_openspec_changes` — 验证 `_matches_prefix` 对 `openspec/changes/foo/proposal.md` 匹配
- [x] 2.3 `test_skip_archive_self` — 验证 `openspec/changes/archive/2026-08-08-foo/` 不被清理
- [x] 2.4 `test_active_change_blocked` — 无 archive/ 存在的活跃 change 不被清理
- [x] 2.5 `test_idempotent_with_changes` — 第二次运行 working tree 干净时无 commit
- [x] 2.6 `test_skip_env_var_with_changes` — `SKIP_POST_ARCHIVE_CLEANUP=yes` 跳过 openspec/changes 清理
- [x] 2.7 `test_dry_run_echoes_rm` — `DRY_RUN_POST_ARCHIVE_CLEANUP=yes` echo 但不执行
- [x] 2.8 `test_modified_bucket_unchanged` — proposal-approved.md 仍只 stage 不 commit

## 3. E2E Tests (3 bats)

- [x] 3.1 `test_e2e_worktree_mode` — 完整 worktree-mode archive flow, 验证残留清零 + 1 commit
- [x] 3.2 `test_e2e_lightweight_mode` — lightweight mode archive flow, 验证残留清零
- [x] 3.3 `test_e2e_active_change_protection` — 活跃 change (无 archive) 在 hook 触发后仍存在

## 4. 手工入口扩展

- [x] 4.1 在 `scripts/cleanup-plan-files.sh` 顶部 arg-parser 接受 `--include-change-artifacts`
- [x] 4.2 新增 section: 列出每个 `openspec/changes/<name>/` (排除 archive/) 的 6 类 artifact 数量
- [x] 4.3 验证 archive-presence 后, 提示 `y/N` 确认
- [x] 4.4 确认后 `git rm -r openspec/changes/<name>/` (使用 -r 是手工入口, 自动 hook 仍用 -f)

## 5. 回归验证

- [x] 5.1 `bats tests/integration/test_archive_cleanup_plan_files.bats` 9 个 case 全部 pass
- [x] 5.2 `bats tests/integration/test_post_archive_cleanup.bats` 新 8 个 case 全部 pass
- [x] 5.3 `bats tests/integration/test_post_archive_cleanup_e2e.bats` 新 3 个 case 全部 pass
- [x] 5.4 `./test.sh --full --regression` 0 新增失败 (KNOWN_FAILURES baseline 隔离)

## 6. 文档

- [x] 6.1 更新 `skills/INSTALL.md` 不需要 (范围外)
- [x] 6.2 更新 `docs/architecture/` 不需要 (范围外)
- [x] 6.3 `proposal-approved.md` 条目状态保持 approved (本 change 不消费 entry, 完成后由 `mark_approved_completed` 移至 `## 已实施`)

## 7. Archive 流程

- [x] 7.1 完成所有 task 后, 在 worktree 内聚合 commit: `chore(post-archive-cleanup): extend scope to openspec/changes/<name>/`
- [x] 7.2 跑 `./test.sh --full --regression` 验证
- [x] 7.3 调用 `skill_use("guide-ship")` Phase 3 archive 流程
- [x] 7.4 验证 `openspec/changes/archive/<date>-archive-cleanup-plan-files-extension/` 存在
- [x] 7.5 验证 `openspec/specs/post-archive-cleanup-hook/spec.md` 在 `openspec/specs/` 落地
