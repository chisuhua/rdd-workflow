# auto-archive-iteration-and-commit

**优先级**: P0 | **来源**: 2026-08-27 ship audit (AI agent 调用手工 archive 路径而非 archive_change_for_mode, 需手工更新 iteration.json + 手工 commit archive moves)
**阶段**: phase-3 | **分类**: governance
**类型**: improvement

**主题**: 2026-08-27 文档与代码一致性审计后续修复

## 架构依据

2026-08-27 ship 9 个 audit-fixup change 时, AI agent 走了手工 archive 路径:
```bash
openspec archive <name> --yes
git add openspec/changes/ && git commit -m "archive(...)..."
python3 -c "import json; ...update iteration.json..."
git branch -D openspec/<name>
```

这绕过了 `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode`, 后者**已实现**所有自动化:
- line 231: `openspec archive "$change_name" --yes`
- line 242: `commit_archive_moves "$change_name" "$project_root" || true`
- line 247: `mark_iteration_archived "$change_name" "$project_root" "$archive_commit_sha"`

后果:
- 9 次手工 `git add + commit` (冗余, 9 × ~3 秒)
- 9 次手工 `python3 -c` 更新 iteration.json (冗余, 9 × ~2 秒, 含可能的 schema 错误)
- 9 次手工 `git branch -D` (应自动清理)
- 错误风险: `tasks_done` 字段可能被错误设置(我之前用 tasks_done=0 而非 tasks_done=tasks_total)

期望行为: AI agent (或 CI) 调 `archive_change_smart.sh <name>` 一键完成 archive, 不需手工 follow-up。

## 范围

**In Scope**:
- 新建 `skills/guide-ship/scripts/archive_change_smart.sh`: 一键式 archive wrapper
  - 检测 execution mode (worktree / lightweight)
  - 调用 `archive_change_for_mode` (已有, ship_archive.sh line 135)
  - 自动确认 iteration.json 状态正确 (`status=archived, tasks_done=tasks_total`)
  - 自动确认 archive moves 已 commit (检查 `git status` 干净)
- 新建 `tests/integration/test_archive_change_smart.bats`: 6 个 test case
  - lightweight mode (no worktree)
  - worktree mode (worktree exists)
  - iteration.json 自动 archived
  - archive moves 自动 commit
  - 干净工作树进入
  - 缺失 change dir 错误处理

**Out of Scope**:
- 修改 `archive_change_for_mode` 内部逻辑 (已正确)
- 修改 `mark_iteration_archived` (已正确)
- 修改 `commit_archive_moves` (已正确)
- 改 `guide-ship/SKILL.md` Phase 3 文档(可选, follow-up)

## Capabilities

- MUST: 强制走 `archive_change_for_mode` 路径, 不允许手工 archive
- MUST: archive 后 iteration.json 自动 archived
- MUST: archive 后 working tree 自动干净 (auto-commit archive moves)
- SHOULD: 提供 `--dry-run` 模式预览 archive 影响
- SHOULD: 提供 `--strict` 模式: 任一步骤失败立即 exit 1 (默认容忍)

## Impact

- MUST NOT: 修改 `archive_change_for_mode` 内部
- MUST NOT: 修改 iteration schema

## Acceptance

- [ ] `archive_change_smart.sh` 一键完成 detect mode + archive + iteration sync + commit archive moves + branch cleanup
- [ ] iteration.json 自动 `status=archived` + `tasks_done=tasks_total`
- [ ] archive moves 自动 commit (subject: `archive(<name>): archive completed`)
- [ ] 6 个 bats test 全部通过
- [ ] AI agent 调用此 helper 后不需任何 follow-up 操作
- [ ] `bash tests/scripts/report_regression.sh` 不增加新 failure