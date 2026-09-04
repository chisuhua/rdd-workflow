# ADR-0042: rdd-arch rename + rdd-arch ↔ rdd-planner 双向反馈闭环

> **状态**: 已采纳 (2026-09-03)
> **日期**: 2026-09-03
> **决策者**: sisyphus
> **替代**: ADR-0016 §v2 additive（planner 反馈通道独立化）、ADR-0028 role.boundaries.owns（新增 planner owns `.planner-feedback.json`）

## Context

Stage 2.5 引入的 `rdd-planner` 是五阶段架构的**横切编排器**，管理 sprint 生命周期 + proposal attach + history。但 arch 阶段（v3.0+ 五阶段架构第一阶段，per ADR-0034）与 planner 之间**无显式双向契约**：

- arch 不知道 planner 的 proposal 是否已 attach、是否缺 theme
- planner 不知道 arch 何时新增 ADR / roadmap theme，无法主动给架构师反馈
- 唯一共享通道是 `.rddf/state/.arch-handoff.json`，但 ADR-0028 明确 arch owns 该文件，planner 写入会**违反角色边界**

此外，D1a 渐进策略明确 Stage 3 重命名 `guide-arch → rdd-arch`，与 `rdd-planner` / `rdd-verifier` 命名对齐。

## Decision

### 1. 角色边界正式化（ADR-0028 §Role Boundary）

| 文件 | owner | 写入者 | 读取者 |
|---|---|---|---|
| `.rddf/state/.arch-handoff.json` | **rdd-arch** | arch-done gate | planner（adhoc read-only）, guide-plan, detectors, actions, scan-state |
| `.rddf/state/.planner-feedback.json` | **rdd-planner** | planner sync/audit/feedback CLI | rdd-arch（Phase 1 advisory read-only）|

**关键约束**: planner **不写** arch-owned handoff；arch **不写** planner-owned feedback。两个文件**完全独立**，独立 FileLock（`.arch-handoff.json.lock` vs `.planner-feedback.json.lock`），互不阻塞。

### 2. 持久化 review 任务模型（独立文件）

`.planner-feedback.json` 承载**持久化 review 任务**（非瞬时诊断快照）：

```json
{
  "schema": "planner-feedback-v1",
  "version": 1,
  "owner": "rdd-planner",
  "branch": "master",
  "worktree_root": "...",
  "codebase_commit": "abc123",
  "arch_handoff_revision": 12,
  "planner_state_last_sync_at": "2026-09-03T10:00:00Z",
  "feedbacks": [
    {
      "feedback_id": "pf-20260903-001",
      "kind": "unmapped_proposal | coverage_gap | adr_drift | roadmap_staleness",
      "severity": "critical | warning | info",
      "status": "open | acknowledged | resolved | dismissed",
      "fingerprint": "a3f7b2c1e9d4f5a8",
      "proposal": "feat-cross-repo-auth",
      "theme": "cross-repo-protocol",
      "related_adr_ids": ["0030"],
      "message": "...",
      "suggested_action": "...",
      "created_at": "...",
      "last_seen_at": "...",
      "acknowledged_at": null,
      "resolved_at": null,
      "resolved_by": null,
      "dismissed_at": null,
      "dismissed_by": null,
      "computed_from": {
        "state_revision": 5,
        "arch_handoff_revision": 12,
        "codebase_commit": "abc123"
      },
      "stale": false
    }
  ],
  "summary": {
    "open_critical": 1, "open_warning": 0, "open_info": 0,
    "acknowledged": 0, "resolved": 0, "dismissed": 0
  }
}
```

**Lifecycle**:
```
open  ──[architect sees]──>  acknowledged  ──[fixed]──>  resolved
                                                ╲
                                                 [waived]──>  dismissed
```

**Fingerprint**: sha256(`kind + proposal + theme + related_adr_ids + reason`)[:16]。同一问题重复 sync **不创建重复条目**，仅更新 `last_seen_at`。

**Stale 检测**: 2-revision 比较 — `is_stale = (prior.arch_handoff_revision != current) OR (prior.state_revision != current)`。
- `arch_handoff_revision`: `.arch-handoff.json::arch_complete_revision`（writer 每次 arch-done +1，per Wave 4 contract v2.1 additive）
- `state_revision`: `.planner-state.json::state_revision`（writer 每次语义变化 +1；排除 `last_sync_at`/`last_sync_status`/`sprint_started_at`/自身）
- `codebase_commit`: 保留为 `computed_from` informational metadata，**不**作为 stale 触发器（消除 doc-only commit 噪声）

### 2.X. Resolved Revival Semantics（Wave 4 Change 3）

`FeedbackEntry` 新增 `reopened_count: int = 0` 与 `advisory_warning: Optional[str] = None`。

**触发条件**: `compute_planner_feedback` 在 fingerprint match 时，若 prior 条目 `status == "resolved"`，则视为"修订未真正生效"——将该条目翻转为 `status = "open"`，`reopened_count = prior.reopened_count + 1`，**保留** `resolved_at` / `resolved_by`（审计追溯）。后续 cycle 中，若该条目已为 `open` 且 fingerprint 仍命中，则 `reopened_count` **保留**不变（不是无界累计）。

**非对称**: `dismissed` 条目在 fingerprint match 时**不**复活——`dismissed` 语义是"豁免 / 主动弃忽略"，与"已解决但复发"是不同状态。

**Advisory Warning**: `reopened_count >= 3` 时条目携带 `advisory_warning: "high_reopen_count"`，供 `rdd-arch status` 展示。语义：反复复活的条目 = 真实回归未修复，需人工干预（re-attach theme、补 ADR、或重新规划）。

### 3. arch-handoff.json 正式化 v2（无字段变动）

`_lib/schemas/arch_handoff_schema.json` 已有 contract v2（`properties.version.enum: [1, 2]`），writer 已写 `"version": 2`。Stage 3 不 bump version，**仅在 schema 注释中明确**：

> contract v2 = base + v2_additive(`roadmap_fragments_dir`, `adr_regex`) + v2_additive_routing(`planner_feedback` 在独立文件 `.planner-feedback.json` 持有)

**零迁移**：所有 v1 consumer (guide-plan intake, detectors, actions, scan-state) 仍能消费 v2 handoff（顶层 `additionalProperties: true`，新字段被忽略）。

### 4. CLI 表面（取代 v2.x `--clear`）

```bash
# planner 侧
rddf planner feedback                                  # 列出所有 open
rddf planner feedback --status open                    # 过滤
rddf planner feedback --kind unmapped_proposal         # 过滤
rddf planner feedback --json                           # JSON 输出
rddf planner feedback --recompute                      # 强制重新计算
rddf planner feedback --acknowledge <FEEDBACK_ID>      # open → acknowledged
rddf planner feedback --resolve    <FEEDBACK_ID>       # → resolved
rddf planner feedback --dismiss    <FEEDBACK_ID>       # → dismissed
rddf planner feedback --prune-resolved                 # 清理历史

# arch 侧（advisory read-only）
rddf arch status     # 一行: 'rdd-arch: phase-X | N ADRs | Planner: N critical, M warning, K stale'
rddf arch handoff    # dump .arch-handoff.json
rddf arch feedback   # read-only view of .planner-feedback.json
```

### 5. guide-arch shim（向后兼容）

`skill_use("guide-arch")` 保留至 v5.x + 2 minor（per D1a 渐进策略）：
- SKILL.md 替换为 5 行 DEPRECATED banner + 转发说明
- `skills/guide_arch.py` 与 `skills/rdd_arch.py` 双 Python 代理同时路由到 `skills/rdd-arch/scripts/`
- `tests/integration/test_legacy_guide_arch_shim.bats` 锁定 shim 契约

### 6. session identity 迁移

`rddf-session` 中 `intent: guide-arch` 自动映射到 canonical `rdd-arch`（session 复用，不新建）。Stage 阶段字段 `stage_arch` 保持不变。

## Consequences

### 正面
- ✅ arch 与 planner 双向契约明确，角色边界无冲突
- ✅ 反馈持久化 + lifecycle，arch 可以追踪未解决问题
- ✅ fingerprint 去重防止反馈刷屏
- ✅ 2-revision stale 检测防止基于陈旧数据行动（codebase_commit 仅 informational，doc-only commit 不再触发 stale 噪声）
- ✅ branch/worktree 字段支持未来多 worktree 并行（沿用 ADR-0034 模式）
- ✅ 无现有消费者 migration cost（contract v2 已存在）
- ✅ 5 行 shim 兼容 Stage 3 之前的 `skill_use("guide-arch")` 调用

### 负面 / 风险
- ⚠️ `.planner-feedback.json` 累积大量 acknowledged/resolved/dismissed 条目 → 需 `--prune-resolved` 定期清理（默认 dry-run 提示）
- ⚠️ planner sync 与 arch-done 不强制同步顺序 → arch 可能看到 planner 已修复的旧 feedback（stale indicator 缓解）
- ⚠️ 双向契约形成"软依赖"——若 planner 文件被手工编辑，arch 显示会失真（per-file FileLock 不防手工操作）

### 兼容性
- ✅ v1 consumer (guide-plan intake, detectors, actions, scan-state.sh) 仍能消费 v2 handoff
- ✅ `skill_use("guide-arch")` shim 至 v5.x + 2 minor
- ✅ `.rddf/improvements/*.md` 现有 226 个文件零修改

## References

- **ADR-0016** arch-discovery-contract (handoff schema v1/v2)
- **ADR-0028** role-model-per-phase (rdd-arch / rdd-planner role boundaries)
- **ADR-0034** rdd-verifier-verify-phase-architecture (5-stage architecture)
- **ADR-0037** feedback-contract (Stage 2.5 feedback entry schema)
- **ADR-0038** rdd-planner-crosscutting (planner scope)
- **ADR-0041** planner-sprint-lifecycle-and-history
- **Plan**: `docs/superpowers/plans/2026-09-03-rdd-workflow-stage3-rdd-arch-rename-and-bidirectional.md`
- **Integration docs**: `docs/architecture/rdd-arch-rdd-planner-integration.md`

## Implementation

- Change 0: `write_arch_handoff.py` FileLock + atomic_write (Oracle C-1 blocker)
- Change 1: `git mv skills/guide-arch → skills/rdd-arch` + shim + blast radius
- Change 2: `_lib/planner_feedback.py` + schema v1 + 持久化模型
- Change 3: `rddf planner feedback --acknowledge|--resolve|--dismiss|--prune-resolved`
- Change 4: `_lib/cli/rdd_arch_cmd.py` + `_lib/rdd_arch_status.py` 聚合器
- Change 5: 本 ADR + consumer-side compat 测试 + 集成文档