# Design: archive-cleanup-working-tree

## Context

plan 阶段 `openspec archive` 将 change 移入 `archive/` 后，原 `openspec/changes/<name>/` 目录变为 git deleted 状态。`commit_archive_moves` (archive.sh) 只 stage archive/ 和 specs/，不处理原目录的删除，导致 working tree 残留 deleted 文件，需手动清理。

## Goals / Non-Goals

### Goals

- 归档后 `git rm -r openspec/changes/<name>/` 原目录，让 git 追踪删除
- 仅在 `openspec archive` 成功后执行清理
- 容错：目录已不存在时跳过
- 批量归档后 working tree 无残留 deleted 文件

### Non-Goals

- 不修改 openspec CLI 本身
- 不修改其他归档消费者的行为

## Decisions

在 `archive.sh::commit_archive_moves` 函数中，在现有 stage archive/ 和 specs/ 之后，增加对原 `openspec/changes/<name>/` 目录的 `git rm -r` 处理：

```bash
# 清理原 change 目录的 git deleted 残留
if [ -d "openspec/changes/$name" ]; then
  git rm -r "openspec/changes/$name" 2>/dev/null || true
fi
```

使用 `git rm -r` 而非 `rm -rf`，确保 git 追踪删除操作。`|| true` 容错处理目录已不存在的情况。

## Implementation

**关键修改文件:**

- `skills/_lib/archive.sh` — `commit_archive_moves` 函数增加原目录清理逻辑
  - 在现有 3 个 stage 路径之后增加第 4 个：`openspec/changes/<name>/` 的 `git rm -r`
  - 保持 `SKIP_ARCHIVE_AUTO_COMMIT=yes` opt-out 语义不变
