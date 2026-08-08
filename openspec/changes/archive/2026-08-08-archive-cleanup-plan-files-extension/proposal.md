# archive-cleanup-plan-files-extension

## Why

- `archive-cleanup-plan-files`（v2.0 已落地）清理 `.rddf/plans/<name>.md`，但 scope 显式声明 "Out of Scope: 不清理 `.rddf/plans/` 之外的文件"
- 复盘发现：`add-rdd-doctor-skill` archive 走 `merge → openspec archive` 流程而非 `archive_change_for_mode → cleanup_plan_file`，残留 6 个文件未被任何 helper 覆盖：
  - `openspec/changes/add-rdd-doctor-skill/.openspec.yaml`
  - `openspec/changes/add-rdd-doctor-skill/design.md`
  - `openspec/changes/add-rdd-doctor-skill/proposal.md`
  - `openspec/changes/add-rdd-doctor-skill/roadmap-meta.yaml`
  - `openspec/changes/add-rdd-doctor-skill/specs/diagnose-changes/spec.md`
  - `openspec/changes/add-rdd-doctor-skill/tasks.md`
- `post-archive-cleanup-hook`（P1 已落地）的 `_WHITELIST_DELETED_PATTERNS` 只覆盖 `.rddf/plans/` 和 `.rddf/state/*.tmp`，**不覆盖 `openspec/changes/`**
- 残留让 `./test.sh --full` 多报6 项 `D` status 噪音；这些 residue 历史上应在 archive 提交时自动清理

## What Changes

**In Scope**:

- `_lib/post_archive_cleanup.sh::_WHITELIST_DELETED_PATTERNS` 增加 `openspec/changes/` 前缀
- `post_archive_cleanup` 在 `git rm` 阶段检测 `D openspec/changes/<name>/` 模式（精确名称，不 glob）
- 删除前必须先确认 `openspec/changes/archive/<date>-<name>/` 存在（防止误删活跃 change）
- `archive-cleanup-plan-files` 已有的 `--cleanup-plan-files` 手动入口扩展为 `--cleanup-plan-files --include-change-artifacts`
- 8 个 bats 单元测试 + 3 个 e2e（worktree mode + lightweight mode + 残留保护）

### 关键场景

- GIVEN change 已 archive 到 `openspec/changes/archive/<date>-<name>/`, WHEN archive 完成 hook 触发, THEN 自动 `git rm` 残留的 `openspec/changes/<name>/*` 6 类文件
- GIVEN change 仍活跃（`openspec/changes/<name>/` 存在但 archive/ 不存在），WHEN hook 触发, THEN 跳过（防御性检查）
- GIVEN hook 误报残留, WHEN `SKIP_POST_ARCHIVE_CLEANUP=yes`, THEN 全部跳过（与现语义一致）
- GIVEN 手工 `--cleanup-plan-files --include-change-artifacts`, WHEN 运行时, THEN 列出每个残留 change 目录 + 用户确认后才删
- GIVEN `archive_change_for_mode` lightweight 路径, WHEN 删除 `.openspec.yaml` etc., THEN 不影响 `archive/.../specs/` 副本

**Out of Scope**:

- 不修改 `archive-cleanup-plan-files` 现有 scope（`.rddf/plans/` 清理）
- 不引入对 `openspec/changes/archive/` 自身的清理（archive 目录是设计目标）
- 不动 `.rddf/plans/<name>.md` 的逻辑（由前序改进负责）
- 不修改 `tests/KNOWN_FAILURES.txt`（保持 baseline 隔离）

## Capabilities

- MUST 删除前 `test -d openspec/changes/archive/*-name` 检查（防御活跃 change 误删）
- MUST 用 `git rm -r openspec/changes/<name>/` 而非 `rm -rf`，让 git index 同步
- MUST 保留 `post_archive_cleanup` 现有 idempotent 语义（bucket 为空则跳过 commit）
- SHOULD 仅删除 6 类 artifact（`.openspec.yaml`、`design.md`、`proposal.md`、`roadmap-meta.yaml`、`specs/...`、`tasks.md`），不动 change 目录下其它文件
- SHOULD 跳过 archive/ 目录下任何匹配（防止删错历史归档）

## Impact

- MUST 删除前 `test -d openspec/changes/archive/*-name` 检查（防御活跃 change 误删）
- MUST 用 `git rm -r openspec/changes/<name>/` 而非 `rm -rf`，让 git index 同步
- MUST 保留 `post_archive_cleanup` 现有 idempotent 语义（bucket 为空则跳过 commit）
- SHOULD 仅删除 6 类 artifact（`.openspec.yaml`、`design.md`、`proposal.md`、`roadmap-meta.yaml`、`specs/...`、`tasks.md`），不动 change 目录下其它文件
- SHOULD 跳过 archive/ 目录下任何匹配（防止删错历史归档）

## Acceptance

- archive 完成后 change dir 残留自动 `git rm`，1 次新 commit subject = `chore(post-archive): clean residue from <name>`
- 残留保护：未 archive 的 change dir 不被误删
- `--cleanup-plan-files --include-change-artifacts` 交互式确认后清理
- `tests/integration/test_archive_cleanup_plan_files.bats` 现有 9 个 case 不回归
- 新增 8 bats + 3 e2e 测试
- `git status --porcelain` 在两次 archive 后保持 0 条 `D openspec/changes/` 行

