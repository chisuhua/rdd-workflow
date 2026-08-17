# harden-archive-iteration-sync — Tasks

> Schema: spec-driven
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## Implementation

- [ ] 1.1 在 `skills/guide-ship/scripts/ship_archive.sh` 末尾新增 `reconcile_iteration_from_disk <change_name> <project_root>` 函数
  - 调用 `sync_iteration_after_archive(project_root, change_name)` 重试一次
  - 检查重试后 `iteration.json` 状态,若仍非 archived 则扫描 `openspec/changes/archive/*-<change_name>/`
  - 若 archive dir 存在,调用 `iteration.set_status + archived_at + archive_commit_sha` + `iteration.save`
  - 输出 stderr warning `⚠️ iteration.json sync failed — auto-recovered via on-disk scan`
  - 返回 0(success) 或 1(failed)
- [ ] 1.2 在 `archive_change_for_mode` 内部,`mark_iteration_archived` 调用之后追加 reconciliation 调用
  - 用 `FORCE_ITERATION_BACKFILL` env var 包裹(默认 ON)
  - 失败不阻断 archive 主流程(`|| echo "⚠️ ..." >&2`)
- [ ] 1.3 在 `skills/_lib/archive.sh` 末尾新增 `reconcile [project_root]` 子命令
  - 遍历 `openspec/changes/archive/*-<name>/`,对每个 entry 检查 iteration.json 状态
  - 缺失 archived_at 的 entry 自动补全
  - 输出每条 reconciliation 结果(✅ fixed / ⏭️ already synced)
  - Idempotent(重复运行无副作用)
- [ ] 1.4 新增 `tests/integration/test_archive_iteration_sync_resilience.bats` (3 cases)
  - Case 1:正常 archive 流程 → `mark_iteration_archived` 成功 → 不触发 reconciliation
  - Case 2:`mark_iteration_archived` 抛异常 (mock `KeyError`) → reconciliation 触发 → iteration.json 最终状态 `archived`
  - Case 3:手动 `bash skills/_lib/archive.sh reconcile .` → 模拟历史遗漏 entries → 全部补全
- [ ] 1.5 文档化 `docs/operations/archive-state-recovery.md`(扩展现有内容)
  - 第 1 节:`症状` — `rddf status` 显示 `📋 planned` 但 archive dir 存在
  - 第 2 节:`手动修复` — 3 步流程(运行 `reconcile` → 验证 → commit)
  - 第 3 节:`FORCE_ITERATION_BACKFILL=no` opt-out 说明
  - 第 4 节:`rddf status` 状态一致性快速验证命令

## Verification

- [ ] 2.1 `bash tests/integration/test_archive_iteration_sync_resilience.bats` — 3/3 cases 通过
- [ ] 2.2 `python3 -m pytest tests/unit/ -q --tb=short` — 无回归
- [ ] 2.3 `bats tests/smoke.bats` — 无回归
- [ ] 2.4 `openspec validate harden-archive-iteration-sync` — passes
- [ ] 2.5 Dry-run 模拟:`rm .rddf/state/iteration.json` 后 archive 一个 test change → 验证 reconciliation 自动重建状态
- [ ] 2.6 Idempotency:重复执行 `bash skills/_lib/archive.sh reconcile .` 5 次 → iteration.json 哈希不变
- [ ] 2.7 端到端:在真实 change 上 archive,验证 `rddf status` 立即显示 `📦 archived`(无需手动 backfill)