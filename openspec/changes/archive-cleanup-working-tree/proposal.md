# Proposal: archive-cleanup-working-tree

## Why

plan 阶段 `openspec archive` 将 change 移入 `archive/` 后，原 `openspec/changes/<name>/` 目录变为 git deleted 状态，需手动 `git checkout -- .` 清理，破坏自动化流程。`commit_archive_moves` (archive.sh) 只 stage archive/ 和 specs/，不处理原目录的删除。

来源: 会话复盘 2026-07-23

## What Changes

- 在 `archive.sh::commit_archive_moves` 或 `archive_change` 中增加：归档后 `git rm -r openspec/changes/<name>/` 原目录
- 或者在 `openspec archive` 完成后自动清理原目录
- 不修改 openspec CLI 本身
- 不修改其他归档消费者的行为

## Capabilities

### New Capabilities: archive-cleanup-working-tree

归档流程完成后自动清理 `openspec/changes/<name>/` 原目录的 git deleted 残留，使用 `git rm -r` 让 git 追踪删除，确保 working tree clean。容错处理：目录已不存在时跳过。

## Impact

**受影响文件:**
- `skills/_lib/archive.sh` — `commit_archive_moves` 或 `archive_change` 增加清理逻辑

**不受影响:**
- openspec CLI 本身
- 其他归档消费者行为
