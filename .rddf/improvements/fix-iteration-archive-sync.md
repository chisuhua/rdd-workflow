# fix-iteration-archive-sync

**优先级**: P0 | **来源**: 2026-08-27 ship audit (sync-package-skills-to-disk + sync-agents-md-five-stage + rdd-doctor-docs-consistency)
**阶段**: default | **分类**: governance
**类型**: bugfix

**主题**: 2026-08-26 文档与代码一致性审计后续修复

## 架构依据

`openspec archive <name> --yes` 命令成功移动 change 到 `openspec/changes/archive/` 子目录,但**不更新** `.rddf/state/iteration.json` 中该 change 的 status,导致其仍为 `proposed`。

后果:

- `rddf rdd-verify` 的 `scan_queue.sh` 扫描 `status in (in_worktree, completed)` 的 changes,完全找不到已归档的 change — verifier 队列为空,ADR-0034 规定的自动 AC 验证失效。
- 状态机不一致: 目录层面已归档,但 iteration.json 视角仍是"待执行"。
- 3 个 P1 docs-consistency change 完成 archive 后,`rddf rdd-verify` 返回 `No eligible changes to verify (empty queue)`,跳过 verify 阶段。

期望行为: archive hook 应同时调用 `iteration.add_or_update_change(data, name, status='archived')`,保持目录状态与状态机同步。

## 范围

**In Scope**:

- `_lib/archive.sh::archive_change` 和 lightweight 模式路径在 `openspec archive` 成功后调用 `iteration.add_or_update_change(name, status='archived')`。
- 同步更新 `tasks_done = tasks_total`(archive 时所有 task 完成)。
- audit log `.cross-repo-audit.jsonl` 追加 `archive` 事件。
- archive auto-commit 失败时,iteration 更新应优先于 commit(状态机一致性优先于 git 持久化)。

**Out of Scope**:

- 修复 `iteration.json` 当前 3 个 pending 的"proposed" 状态(本提案生效前的历史数据)。
- 改 `iteration.json` schema(`status` 枚举扩展)。

## 关键场景

- GIVEN 3 个 change 已 `archive` 但 iteration.json 仍是 `proposed`
  WHEN 运行 `rddf rdd-verify --dry-run`
  THEN 返回 `No eligible changes to verify (empty queue)`,跳过所有验证

- GIVEN 用户对 `fix-iteration-archive-sync` 提案执行 `archive`
  WHEN `_lib/archive.sh::archive_change` 完成目录移动
  THEN 立即调用 `iteration.add_or_update_change(data, name, status='archived', tasks_done=tasks_total)`

## 技术约束

- MUST: archive hook 失败时,iteration 更新回滚(避免目录在 archive/ 但 iteration 状态不一致)
- MUST: `iteration.json` 写入使用 atomic write(`_lib/core/atomic_write.atomic_write_json`)
- MUST NOT: 修改 `_lib/openspec/` CLI 包装层
- SHOULD: 在 audit log 中记录 archive 事件 + iteration 同步结果
- SHOULD NOT: 在 archive_auto_commit 阶段才同步 iteration(应在目录移动后立即同步)

## 验收标准

- [ ] `_lib/archive.sh::archive_change` 在 `openspec archive` 成功后调用 `iteration.add_or_update_change`
- [ ] `_lib/iteration/store.py` 的 `add_or_update_change` 支持 `status='archived'` 且 `tasks_done` 字段
- [ ] 新增 unit test `tests/unit/test_archive_iteration_sync.py` 覆盖以下场景:
  - archive 后 iteration 状态更新为 archived
  - archive 失败时 iteration 不被更新(回滚)
  - tasks_done 字段正确传播
- [ ] 已有 archive 的 3 个 P1 change 一次性 sync 到 iteration.json(`status='archived'`)
- [ ] `rddf rdd-verify --dry-run` 在 sync 后能正确识别 archived change 为"已通过"(无需 verify)
- [ ] `bash tests/scripts/report_regression.sh` 不增加新 failure

## 相关

- 关联: `post-archive-cleanup-hook` (.rddf/improvements/) — cleanup hook 是相关但不同关注点
- 关联: ADR-0034 rdd-verifier — 该 bug 阻断 verifier 自动验证
- 来源: 2026-08-27 全链路工作流审计 (3 P1 docs-consistency changes ship + archive 后发现)
