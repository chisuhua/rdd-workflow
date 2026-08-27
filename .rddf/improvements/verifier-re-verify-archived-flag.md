# verifier-re-verify-archived-flag

**优先级**: P1 | **来源**: 2026-08-27 ship audit (rdd-verifier 默认扫描 `in_worktree/completed`, archived changes 自动排除; 但 AI agent ship 9 个 change 后想 "复盘 AC 是否满足" 时, verifier 无事后审计能力)
**阶段**: phase-5 | **分类**: governance
**类型**: improvement

**主题**: 2026-08-26 文档与代码一致性审计后续修复

## 架构依据

按 ADR-0034 + rdd-verifier SKILL.md:
- scan_queue.sh 过滤 `status in (in_worktree, completed)` AND `tasks_done == tasks_total > 0`
- archived changes 自动排除
- 设计意图: verifier 是 archive **之前**的兜底,不是 archive **之后**的复盘

后果:
- 2026-08-27 ship 9 个 change 后, AI agent 想复盘 AC 是否满足, `rddf rdd-verify` 返回 "No eligible changes"
- 复盘是**非标 workflow**, 但有 audit value (记录 AC 满足情况, 留 evidence)
- LLM-based AC 验证 (ac-verifier) 在 9 个 change 上从未跑过 (proposal 缺 specs/ delta, archive 不阻断)

期望行为: `rddf rdd-verify --re-verify-archived` 扫描 status=archived 的 changes, 跑 ac-verifier, 写 verdict cache 作为事后审计 trail。

## 范围

**In Scope**:
- 修改 `_lib/cli/rdd_verify_cmd.py`: 新增 `--re-verify-archived` argparse flag
- 修改 `skills/rdd-verifier/scripts/scan_queue.sh`: 支持 `--include-archived` 模式
- 修改 `_lib/verifier/discovery.py`: scan archived changes (从 openspec/changes/archive/ 枚举)
- 新增 6 个 test:
  - CLI flag 解析 (`--re-verify-archived`)
  - scan_queue.sh 默认排除 archived, `--include-archived` 包含
  - rdd-verify 在 archived changes 上写 verdict cache
  - verdict cache SHA fingerprint 不冲突 (复用 v2 schema)
  - audit log 包含 `re_verify_archived` 事件类型
  - 与现有 `--loop` 兼容 (但 max_loops 对 archived 禁用, 直接 audit)

**Out of Scope**:
- 修改 ac-verifier 内部逻辑
- 修改 rdd-verifier state machine (只加事后入口, 不改主流程)
- 新增 verdict 显示 UI (留待 dashboard)

## Capabilities

- MUST: `--re-verify-archived` flag 不与默认模式冲突
- MUST: archived change 的 verdict cache 用 archive commit SHA 而非 HEAD SHA
- MUST: audit log 区分 `verify_archived` 与正常 `verify` 事件
- MUST: archived change 不参与 loop (no retry, 直接 record verdict)
- SHOULD: 提供 `--archived-since <date>` 过滤 (减少范围)

## Impact

- MUST NOT: 修改默认 rdd-verify 行为 (向后兼容)
- MUST NOT: 跳过 ac-verifier hard gates

## Acceptance

- [ ] `rddf rdd-verify --re-verify-archived` 不报错, 列出 archived change 的 ac-verifier verdict
- [ ] verdict cache 写入 `.rddf/state/.ac-verdict-<name>.json`
- [ ] audit log 区分事件类型
- [ ] 6 个 test 全部通过 (含 CLI flag + scan_queue 模式)
- [ ] 默认 rdd-verify 行为不变 (向后兼容)
- [ ] `bash tests/scripts/report_regression.sh` 不增加新 failure