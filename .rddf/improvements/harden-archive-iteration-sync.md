# harden-archive-iteration-sync

**优先级**: P1 | **来源**: 2026-08-16 post-archive 验证发现 backfill-proposal-approved-col4 / enforce-plan-tdd-5step-new iteration.json sync 漏写
**阶段**: v2.2 | **分类**: quality
**类型**: fix

## 架构依据
- `archive.sh::mark_iteration_archived` 是 archive 后必调函数,负责写 `iteration.json` 的 archived_at 字段
- 本次 2 个 P2 debt improvements (`backfill-proposal-approved-col4` + `enforce-plan-tdd-5step-new`) 的 archive 都走完 on-disk 操作(merge + openspec archive + cleanup + 目录移动),但 `iteration.json` sync 全部漏写 — 异常被 swallow
- 漏写的 root cause 是 `KeyError: 'skills._lib'` 在 mark_iteration_archived 内部抛出(命名空间包合并问题),外层 `archive_change_for_mode` 捕获后只打 traceback 继续,不重试也不 reconciliation
- **后果**: `rddf status` 显示 change 仍为 `📋 planned` 但 archive 目录实际存在 — 状态不一致需手动 backfill iteration.json
- **类比 anchor**: `add-archive-post-commit-hook-and-force-flag` (P0) 是处理 archive hook edge cases 的同型提案
- **ADR-0017** (rddf-session) 要求 stage_ship 完成时 iteration 与 archive 状态一致

## 范围
- **In Scope**:
 - 修改 `skills/_lib/archive.sh::archive_change_for_mode`,在 `mark_iteration_archived` 失败后追加 reconciliation 步骤
 - Reconciliation 逻辑:扫描 `openspec/changes/archive/` 目录,对比 `iteration.json` 的 `archived_at` 字段,缺失则补全
 - 增加 try/except + stderr warning(`⚠️ iteration.json sync failed, attempting on-disk reconciliation`)
 - 新增 `tests/integration/test_archive_iteration_sync_resilience.bats`:3 个 case(正常 / sync-fail / manual-fix)
 - 文档化 `docs/operations/archive-state-recovery.md`:手动修复流程(已有内容扩展)

- **Out Scope**:
 - NOT 重写 `archive.sh` 整体逻辑(只增量添加 reconciliation step)
 - NOT 修复 `skills/_lib/__init__.py` (已 commit 78724ca 修复)
 - NOT 添加 CI check(用 `rddf status` 手动验证已足够)
 - NOT 改 iteration.json schema(version 保持)
 - NOT 修 `archive.sh` 内部对 `skills._lib` 命名空间导入(假设未来 import 不再 swallow)

## 关键场景
- GIVEN `archive.sh` 主体成功(`merge → openspec archive → cleanup → branch delete`)
- AND `mark_iteration_archived` throws exception(例如 `KeyError: 'skills._lib'` 或 `ModuleNotFoundError`)
- WHEN `archive_change_for_mode` 捕获异常
- THEN 自动 reconciliation:扫描 `openspec/changes/archive/<date>-<name>/`,对 `iteration.json` 缺失的 entry 补 `archived_at` + `status: archived`
- AND 输出 stderr 警告 `⚠️ archive main flow succeeded but iteration.json sync failed — auto-recovered via on-disk scan`
- AND exit code 仍为 0(archive 主体成功,只是 sync 故障)

- GIVEN 用户用 `rddf status` 验证
- WHEN 发现 change 显示 `📋 planned` 但 `openspec/changes/archive/<date>-<name>/` 存在
- THEN 提示用户运行 `bash skills/_lib/archive.sh reconcile` (新 subcommand)强制 on-disk reconciliation

- GIVEN `FORCE_ITERATION_BACKFILL=no` (默认)
- AND archive 主体失败
- THEN 不执行 reconciliation(避免不一致)

## 技术约束
- MUST 幂等(多次执行无副作用)
- MUST NOT 修改 on-disk archive(只读 + 补 iteration.json)
- MUST 保留 `FORCE_ITERATION_BACKFILL` env var(用户 opt-in 关闭自动 backfill)
- MUST 输出 clear stderr warning(让用户知道 main flow OK 但 sync 自动恢复)
- SHOULD 在 reconciliation 失败时,提示具体手动修复命令(`python3 -c "from skills._lib.iteration import ...; manually_set(...)"`)

## 验收标准
- `rddf status` 对所有 10 个 2026-08-16 archives 显示 `📦 archived`(当前 backfill-proposal-approved-col4 + enforce-plan-tdd-5step-new 应已 archived)
- `tests/integration/test_archive_iteration_sync_resilience.bats` 3 个 case 全过
- `archive.sh` 错误日志含 `⚠️ iteration.json sync failed, auto-recovered` warning
- 文档 `docs/operations/archive-state-recovery.md` 含手动修复流程(3 步骤)
- 模拟 sync 失败的 dry-run test:archive 主体成功后,iteration.json 仍被 reconciliation 补全
- idempotency test:重复执行 `archive.sh reconcile` 无副作用