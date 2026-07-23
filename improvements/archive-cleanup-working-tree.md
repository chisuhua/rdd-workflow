# archive-cleanup-working-tree

**优先级**: P1 | **来源**: 会话复盘 2026-07-23 — plan 归档后残留 deleted 文件
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据

- plan 阶段 `openspec archive` 将 change 移入 `archive/` 后，原 `openspec/changes/<name>/` 目录变为 git deleted 状态
- 需手动 `git checkout -- .` 清理，破坏自动化流程
- `commit_archive_moves` (archive.sh) 只 stage archive/ 和 specs/，不处理原目录的删除

## 范围

- **In Scope**:
  - `archive.sh::commit_archive_moves` 或 `archive_change` 中增加：归档后 `git rm -r openspec/changes/<name>/` 原目录
  - 或者：在 `openspec archive` 完成后自动清理原目录
- **Out Scope**:
  - 不修改 openspec CLI 本身
  - 不修改其他归档消费者的行为

## 关键场景

- GIVEN openspec archive 成功, WHEN 检查 working tree, THEN openspec/changes/<name>/ 已 clean
- GIVEN 5 个 change 批量归档, WHEN 全部完成后, THEN working tree 无残留 deleted 文件

## 技术约束

- MUST 仅在 openspec archive 成功后执行清理
- MUST 使用 `git rm -r` 而非直接 `rm -rf`（让 git 追踪删除）
- SHOULD 容错：目录已不存在时跳过

## 验收标准

- 归档后 `git status` 不显示 openspec/changes/<name>/ 为 deleted
- working tree clean 检查通过
