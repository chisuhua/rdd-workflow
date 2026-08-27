# reconcile-iteration-after-archive

**优先级**: P0 | **来源**: 2026-08-27 ship audit (3 P1 docs-consistency changes 已 archive 但 iteration 仍 proposed)
**阶段**: default | **分类**: governance
**类型**: data-fixup

**主题**: 2026-08-26 文档与代码一致性审计后续修复

## 架构依据

2026-08-27 完成 3 个 P1 docs-consistency changes 的 ship + archive:

| Change | archive dir | iteration status |
|--------|-------------|------------------|
| sync-package-skills-to-disk | 2026-08-27-* | proposed (未更新) |
| sync-agents-md-five-stage | 2026-08-27-* | proposed (未更新) |
| rdd-doctor-docs-consistency | 2026-08-27-* | proposed (未更新) |

后果: `rddf rdd-verify` 无法识别这 3 个已 archive 的 changes,verifier 永远空队列。

期望行为: 在 `fix-iteration-archive-sync` 提案实施前,一次性 reconcile iteration.json 历史数据。

## 范围

**In Scope**:

- 一次性脚本扫描 `openspec/changes/archive/2026-08-27-*` 目录,找出所有 archive 的 changes。
- 对每个 archived change,检查 `.rddf/state/iteration.json`,如果 status 不是 `archived`,更新为 `archived` + 同步 `tasks_done = tasks_total`。
- 输出 reconcile report。

**Out of Scope**:

- 修改 `_lib/archive.sh`(那是 `fix-iteration-archive-sync` 的 scope)
- 修复历史更早的 archive 数据(本次只处理 2026-08-27 的 3 个)

## 关键场景

- GIVEN 3 个 P1 changes 已 archive
  WHEN `reconcile-iteration.sh` 运行
  THEN iteration.json 中这 3 个 change 的 status 更新为 `archived`,tasks_done=total

- GIVEN reconcile 完成后
  WHEN `rddf rdd-verify --dry-run` 运行
  THEN 能识别这 3 个 change 为"已通过",不再返回 empty queue

## 技术约束

- MUST: 使用 atomic write 保护 iteration.json
- MUST: 备份 iteration.json.before-reconcile 到 `.rddf/state/.before-reconcile/`
- MUST NOT: 修改 archive/ 子目录的 proposal.md / tasks.md
- SHOULD: 提供 `--dry-run` 模式预览

## 验收标准

- [ ] `reconcile-iteration.sh` 脚本实现
- [ ] 3 个 P1 changes 在 iteration.json 中 status='archived',tasks_done=tasks_total
- [ ] 备份文件存在 `.rddf/state/.before-reconcile/iteration.json.before-reconcile-2026-08-27`
- [ ] `rddf rdd-verify --dry-run` 不再返回 empty queue
- [ ] 不修改 archive/ 子目录的任何文件
