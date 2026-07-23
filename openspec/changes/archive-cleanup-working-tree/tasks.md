# Tasks: archive-cleanup-working-tree

## Implementation Steps

- [ ] 在 `skills/_lib/archive.sh` 的 `commit_archive_moves` 函数中增加原目录清理
  - 在现有 stage `openspec/changes/<name>/`、`openspec/changes/archive/`、`openspec/specs/` 之后
  - 增加 `git rm -r "openspec/changes/$name" 2>/dev/null || true`
  - 确保 git 追踪删除操作
- [ ] 添加容错逻辑
  - 目录已不存在时跳过（`|| true`）
  - 不影响已成功的 archive 主体操作
- [ ] 验证 `SKIP_ARCHIVE_AUTO_COMMIT=yes` opt-out 语义不变
  - 跳过整个 helper 时不执行清理
- [ ] 更新 AGENTS.md 中 "Archive Auto-Commit" 章节的 strict scope 说明
  - 增加 `openspec/changes/<name>/` 删除清理的说明

## Verification (验收标准)

- [ ] 归档后 `git status` 不显示 openspec/changes/<name>/ 为 deleted
- [ ] working tree clean 检查通过

## Key Scenarios (关键场景)

- [ ] GIVEN openspec archive 成功, WHEN 检查 working tree, THEN openspec/changes/<name>/ 已 clean
- [ ] GIVEN 5 个 change 批量归档, WHEN 全部完成后, THEN working tree 无残留 deleted 文件
