# harden-archive-iteration-sync — Design

> Schema: spec-driven
> See: `proposal.md` for motivation, scope and acceptance criteria.

## Context

`archive.sh::mark_iteration_archived` 是 archive 主体完成后**必调**的函数,负责把 `iteration.json` 中的 change entry 标记为 `status: archived` + `archived_at` 时间戳。本批 2 个 P2 debt improvements (`backfill-proposal-approved-col4` + `enforce-plan-tdd-5step-new`) 的 archive 走完了 on-disk 全部动作(merge → openspec archive → cleanup → 目录移动),**但 `iteration.json` sync 全部漏写**——异常被 swallow,archive 主体仍 exit 0。

漏写的 root cause 是 `KeyError: 'skills._lib'` 在 `iteration.post_archive.sync_iteration_after_archive()` 内部抛出(命名空间包合并问题),`archive.sh` 的 `mark_iteration_archived` 调用 `python3 -c '...'` 捕获到 `Exception` 后只打 `⚠️ iteration.json update failed (archive still succeeded): {e}` 到 stderr,然后 `return 0`。外层 `archive_change_for_mode` 完全感知不到。

后果:`rddf status` 显示 change 仍为 `📋 planned` 但 `openspec/changes/archive/<date>-<name>/` 实际存在——状态不一致需手动 backfill iteration.json。

类比 anchor:`add-archive-post-commit-hook-and-force-flag` (P0) 是处理 archive hook edge cases 的同型提案(2026-08-08 已实施,作为 post-archive-cleanup-hook 的演进)。

ADR-0017 (rddf-session) 要求 stage_ship 完成时 iteration 与 archive 状态一致,本提案补齐 archive 主流程的 on-disk ↔ iteration.json 同步缺口。

## Goals / Non-Goals

**Goals:**
- 在 `archive_change_for_mode` 内部,`mark_iteration_archived` 之后追加 on-disk reconciliation 步骤
- Reconciliation 逻辑:扫描 `openspec/changes/archive/`,对 `iteration.json` 缺失 `archived_at` 字段的 entry 自动补全
- 增加 stderr warning 让用户感知 sync 故障 + 自动恢复(`⚠️ iteration.json sync failed, attempting on-disk reconciliation`)
- 新增 `bash skills/_lib/archive.sh reconcile <project_root>` 子命令供用户手动触发
- 新增 `tests/integration/test_archive_iteration_sync_resilience.bats`(3 个 case)
- 文档化 `docs/operations/archive-state-recovery.md`(扩展现有内容)

**Non-Goals:**
- 不重写 `archive.sh` 整体逻辑(只增量添加 reconciliation step)
- 不修复 `skills/_lib/__init__.py`(已 commit 78724ca 修复)
- 不加 CI check(用 `rddf status` 手动验证已足够)
- 不改 iteration.json schema(version 6 保持)
- 不修 `archive.sh` 内部对 `skills._lib` 命名空间导入(假设未来 import 不再 swallow)

## Decisions

### 1. Reconciliation 实现位置

修改 `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode`,在现有 `mark_iteration_archived` 调用**之后**追加 on-disk reconciliation 步骤:

```bash
# 现有(L244-247):
mark_iteration_archived "$change_name" "$project_root" "$archive_commit_sha"

# 新增:
reconcile_iteration_from_disk "$change_name" "$project_root" || \
  echo "⚠️ on-disk reconciliation 也失败,iteration.json 可能仍不一致" >&2
```

**原因**: `archive_change_for_mode` 是 worktree + lightweight 两种模式的 single funnel(ADR-0027 §1),只在这里加一次就覆盖两条路径。

### 2. Reconciliation 算法

`reconcile_iteration_from_disk <change_name> <project_root>` 函数:

1. 调用 `sync_iteration_after_archive(project_root, change_name)` 重试一次(覆盖 transient failures)
2. 如果重试后 `iteration.json` 仍显示 change status != "archived":
   - 扫描 `openspec/changes/archive/*-<change_name>/`,确认 archive dir 存在
   - 调用 `iteration.set_status(data, change_name, "archived")` + 设 `archived_at` + `archive_commit_sha`
   - 调 `iteration.save(project_root, data)` 落盘
3. 输出 stderr 警告 `⚠️ iteration.json sync failed — auto-recovered via on-disk scan`

**幂等保证**: 重复执行不会产生副作用——`set_status` 在已 archived 时强制再写一次 archived_at(可接受,文档化为 idempotency quirk)。

### 3. 手动 reconcile 子命令

新增 `bash skills/_lib/archive.sh reconcile [project_root]`,签名:

```bash
reconcile() {
  local project_root="${1:-$PWD}"
  echo "🔍 Scanning $project_root/openspec/changes/archive/ for missing iteration.json entries..."
  # 遍历 archive/ 子目录,对每个 <date>-<name>,检查 iteration.json 状态
  # 缺失/未 archived → 调用 sync_iteration_after_archive + on-disk fallback
}
```

用户场景:`rddf status` 显示某 change `📋 planned` 但 archive dir 存在 → 运行 `bash skills/_lib/archive.sh reconcile .` 强制 on-disk 同步。

### 4. Skip / Opt-out 语义

环境变量 `FORCE_ITERATION_BACKFILL=no`(默认)允许用户 opt-in 关闭 reconciliation:

```bash
if [ "${FORCE_ITERATION_BACKFILL:-yes}" = "yes" ]; then
  reconcile_iteration_from_disk "$change_name" "$project_root" || \
    echo "⚠️ on-disk reconciliation failed" >&2
fi
```

**注意**: 默认行为是 ON(自动 reconciliation),用户需显式设 `FORCE_ITERATION_BACKFILL=no` 才跳过。

### 5. 不重写 sync,只补 reconciliation

保留现有 `mark_iteration_archived` 函数(已 commit 78724ca 修复 `__init__.py`)。新逻辑只追加 fallback,不替换——保持责任分离:
- `mark_iteration_archived`: 正常路径(archive 主体成功后立即调)
- `reconcile_iteration_from_disk`: 容错路径(主路径失败后兜底)

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| `archive_change_for_mode` 加 reconciliation 后性能影响 (每次 archive 多扫一次 archive/ 目录) | 目录扫描 O(N) 其中 N 是已 archive 数量,通常 < 100,sub-second overhead |
| `iteration.json` 漏写可能有更深 root cause (不只是 `KeyError`) | reconciliation 是 on-disk authoritative source,可覆盖任何 transient failure |
| 重复执行 reconcile 会重写 `archived_at`(幂等性问题) | 文档化为已知行为,iteration.json schema 不强制 archived_at 不变 |
| `mark_iteration_archived` 旧代码已 commit,用户可能依赖其行为 | reconciliation 是**追加**行为,旧行为不变 |