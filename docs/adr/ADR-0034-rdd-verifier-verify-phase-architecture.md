# ADR-0034: rdd-verifier 验证回环阶段架构

> **状态**: 已采纳 (2026-08-26)
> **日期**: 2026-08-26
> **修订**: 2026-08-26 — fix-rdd-verifier-lifecycle-dashboard 落地后补充存储契约、branch-identity、bypass 审计
> **决策者**: sisyphus

## 问题

rdd-workflow v2.1+ 4 阶段架构缺独立的验证回环阶段。`_lib/archive.sh::archive_gate_check` 已自动调用 ac-verifier 技能（v1.0，2026-08-17），但默认 `STRICT_AC_GATE=no`（warning-only），且：
1. AC 验证仅是 archive 内嵌步骤，无用户可见阶段菜单
2. 缺失败回环机制（AC fail 后用户需手动判断去 plan 还是 ship）
3. 缺批量能力（一次只能验证一个 change）
4. 缺 SHA 指纹缓存（archive_gate_check 与外部 LLM 调用可能重复）
5. 队列发现错误的 `ship-done` 状态（非真实生命周期字段）
6. 全局 `.verifier-loop.json` 串改多 change 的重试历史
7. cache 缺 `verification_state` / `failed_acs`，archive gate 无法做严格合同校验

## 决策

新增第 5 阶段 `rdd-verifier`（arch → design → plan → ship → **verify** → archive），采用 **Approach C 混合形态**：

- **位置**: ship 完成后、archive 前的独立验证步骤
- **属性**: 条件必经（默认必走，`SKIP_RDD_VERIFIER=yes` 跳过）；非线性必经节点
- **人工介入**: high（AI 分类 + 用户确认 + 失败回环决策）
- **失败回环**: 启发式分类（implementation_gap / proposal_drift）+ 用户确认 + 跳回 plan 或 ship，最多重试 3 次
- **与 ac-verifier 关系**: 复用 sub-skill，不重写 LLM
- **SHA 指纹 verdict 缓存**: `.rddf/state/.ac-verdict-<name>.json` 绑 `codebase_commit`，避免 archive_gate_check 与 rdd-verifier 双跑 LLM

### 修订要点（fix-rdd-verifier-lifecycle-dashboard, 2026-08-26）

#### 1. 真实生命周期发现（Task 5-6）

`discover_eligible` 用真实 lifecycle (`in_worktree`/`completed`) + `tasks_done == tasks_total > 0` 取代 `ship-done`。`ship-done` 是阶段级事件而非 per-change 状态，不能作为发现源。

#### 2. Per-change loop state（Task 2）

loop state 从 `.rddf/state/.verifier-loop.json` 迁至 `.rddf/state/verifier/<change>.json`。两 change 并发验证时，各自状态独立，不会互相覆盖重试历史。Legacy 单文件仅当 `change` 字段匹配唯一 eligible change 时迁移。

#### 3. Branch identity fail-closed（Task 5）

verdict 必须绑到 `openspec/<change>` 分支 tip：
- 分支缺失 → halted
- detached HEAD → halted
- 轻量模式 branch 不匹配 → 阻断 archive

#### 4. Cache v2 schema（Task 3）

`.ac-verdict-<change>.json` 新增字段：
- `schema_version: 2`
- `verification_state` (passed/failed/error/skipped/halted/bypassed)
- `failed_acs: [string]`
- `source` / `ran_by` (`rdd-verifier` 或 `archive_gate_check`)
- `implementation_ref` (e.g., `openspec/ch-x`)

archive_gate_check 直接调用 ac-verifier 时（fallback）必须写结构化 verdict 到 canonical cache（`ran_by=archive_gate_check`）。

#### 5. Gate precedence（Task 11）

`archive_gate_check` 接受 archive 的唯一条件：

```text
verification.state ∈ (passed, bypassed) AND archive_ready == true
AND verdict_sha == current implementation branch tip
AND cache verdict contains no failed AC
```

`STRICT_AC_GATE` 仅控制 legacy direct ac-verifier fallback；不影响 cached verifier 状态。
`SKIP_RDD_VERIFIER` 写 `bypassed`（带 audit reason），不绕过 `FEATURE_ARCHIVE_GATE=hard` 或 `FORCE_ARCHIVE_INCOMPLETE=yes`。

#### 6. SKIP_RDD_VERIFIER 审计（Task 10）

`SKIP_RDD_VERIFIER=yes` 必须配 `RDDF_VERIFIER_BYPASS_REASON`。两者都设置时：
- `verification.state = bypassed`
- `bypass_source = SKIP_RDD_VERIFIER`
- `bypass_reason = <reason>`
- `archive_ready = true`
- audit log 写 `bypassed` 事件

缺失 reason 时 `rddf rdd-verify` 失败关闭（exit 3）。

#### 7. 退出码扩展

| Code | Meaning |
|------|---------|
| 0 | 全部 pass 或 bypassed（archive 可继续） |
| 1 | AC fail（implementation_gap / proposal_drift），触发回环 |
| 2 | SKIP_RDD_VERIFIER=yes 跳过 |
| 3 | ac-verifier 内部错误（LLM 失败、API key 缺失）或 SKIP 无 reason |
| **4 (halted)** | **max_loops 触发或 branch missing，archive halted** |

Aggregate 优先级: `halted (4) > error (3) > failed (1) > bypassed/passed (0)`。

#### 8. Storage ownership（4 层）

| Layer | File | Owns |
|-------|------|------|
| Iteration summary | `.rddf/state/iteration.json` | `verification.{state, verdict_sha, archive_ready, ...}` |
| Per-change loop | `.rddf/state/verifier/<change>.json` | retry history, classification_history, halt_reason |
| Cache | `.rddf/state/.ac-verdict-<change>.json` | raw verdict, codebase_commit, ran_by, schema_version |
| Audit log | `.rddf/state/verifier/<change>.audit.jsonl` | append-only events |

写顺序: loop → cache → iteration summary → audit。任何一步失败：保留 in-progress state，non-zero exit，不提升到 passed。

#### 9. Dashboard 三维度

`ChangeEntry` 增加 `verification` 字段与派生 `verification_state` / `archive_ready` 属性：
- active change 无 verification → `unknown`
- archived change 无 verification → `legacy`（永不伪造为 passed）
- 8 个状态：pending, running, passed, failed, halted, bypassed, legacy, unknown

#### 10. 角色模型（ADR-0028 扩展）

- `role.owns`:
  - `.rddf/state/verifier/<change>.json`
  - `.rddf/state/verifier/<change>.audit.jsonl`
  - `.rddf/state/.ac-verdict-<change>.json`
- `role.not_owns`:
  - `openspec/changes/<name>/`
  - `docs/adr/`
  - merge / archive / branch deletion / worktree cleanup（属于 guide-ship）
- `role.human_involvement`: `high`

## 后果

**正面**:
- AC 验证成为用户可见阶段而非内嵌步骤
- 失败自动回环避免人工跟踪
- SHA 指纹缓存避免 LLM 双跑（省钱 + 省时间）
- 启发式分类无需额外 LLM 调用
- 真实 lifecycle 发现消除 `ship-done` 误用
- per-change loop 状态消除并发串改
- branch-identity 严格合同消除 stale verdict 滥用
- bypass 审计避免静默跳过

**负面**:
- 5 阶段架构文档更新成本（AGENTS.md / guide 推荐器菜单）
- 启发式分类误判需用户确认兜底（ambiguous 默认 implementation_gap）
- 严格 archive gate 可能暴露历史依赖 warning-only 的 change（通过 bypass 显式审计保留旧行为）

**中立**:
- 不修改现有 4 阶段职责边界（verify 属 ship 后、archive 前的回环，不属新增设计/规划阶段）
- 不并发跑 LLM（v1 串行，避免 token 峰值 + 输出交错难审计）
- 保留 archive_gate_check 内的 ac-verifier 调用作为兜底（用户绕过 rdd-verifier 直接 archive 时仍守门，且 fallback 写结构化 cache）
- 不为历史已归档 change 伪造 verification 数据（dashboard 显示 `legacy`）

## 参考

- ADR-0003: 三阶段架构
- ADR-0025: design 阶段独立化（四阶段）
- ADR-0028: role model per phase
- ADR-0017: rddf-session
- ADR-0024: deps-driven execution mode
- Spec: `openspec/changes/fix-rdd-verifier-lifecycle-dashboard/specs/verifier-lifecycle/spec.md`
- Spec: `openspec/changes/fix-rdd-verifier-lifecycle-dashboard/specs/archive-gate-verification/spec.md`
- Spec: `openspec/changes/fix-rdd-verifier-lifecycle-dashboard/specs/dashboard-verification-status/spec.md`
- Plan: `.rddf/plans/fix-rdd-verifier-lifecycle-dashboard.md`

## 设计文档

- Spec: `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md`
- Plan: `docs/superpowers/plans/2026-08-26-rdd-verifier-implementation.md`
