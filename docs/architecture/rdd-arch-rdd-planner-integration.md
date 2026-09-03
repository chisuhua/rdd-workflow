# rdd-arch ↔ rdd-planner 双向反馈闭环集成指南

> **Stage**: 3 (per ADR-0042)
> **Status**: 已采纳 (2026-09-03)
> **Audience**: rdd-workflow 用户 + 集成 agent

## 1. 架构概述

Stage 3 之后，`rdd-arch` 与 `rdd-planner` 通过**两个独立状态文件**协作，遵循 ADR-0028 role 边界：

```
                    ┌──────────────────────────────────┐
                    │  rdd-arch (Phase 6 arch-done)    │
                    └──────────────────┬───────────────┘
                                       │ write .arch-handoff.json
                                       │ (FileLock + atomic_write_json)
                                       ▼
                ┌────────────────────────────────────────┐
                │  .rddf/state/.arch-handoff.json (v2)    │
                │  owner: rdd-arch                       │
                └────────────────────────────────────────┘
                                       │ read by rdd-planner (adhoc)
                                       ▼
                    ┌──────────────────────────────────┐
                    │  rdd-planner (sync / audit)       │
                    │  compute_planner_feedback()       │
                    └──────────────────┬───────────────┘
                                       │ write .planner-feedback.json
                                       │ (FileLock + atomic_write_json)
                                       ▼
                ┌────────────────────────────────────────┐
                │  .rddf/state/.planner-feedback.json   │
                │  owner: rdd-planner (NOT arch)        │
                └────────────────────────────────────────┘
                                       │ read by rdd-arch Phase 1
                                       ▼
                    ┌──────────────────────────────────┐
                    │  rdd-arch Phase 1 display:        │
                    │  "rdd-arch: phase-X | N ADRs |    │
                    │   Planner: N critical, M warning" │
                    └──────────────────────────────────┘
```

**关键约束**:
- rdd-arch **不写** `.planner-feedback.json`（角色边界，per ADR-0028）
- rdd-planner **不写** `.arch-handoff.json`（角色边界）
- 两文件独立 FileLock（`.arch-handoff.json.lock` 与 `.planner-feedback.json.lock`），互不阻塞

## 2. 双契约载体

### 2.1 `.rddf/state/.arch-handoff.json`（rdd-arch owns）

Owner: rdd-arch。Schema: `_lib/schemas/arch_handoff_schema.json` v2（per ADR-0016）。

```json
{
  "arch_complete_at": "2026-09-03T10:00:00Z",
  "adr_count": 41,
  "completed_adr_ids": ["0003", "0016", "0017", "0025", "0034", "0041", "0042"],
  "roadmap_exists": true,
  "current_phase": "phase-1",
  "plan_started_at": null,
  "adr_dir": "docs/adr",
  "roadmap_path": "roadmap.md",
  "roadmap_fragments_dir": ".rddf/roadmap",
  "architecture_dir": "docs/architecture",
  "adr_pattern": "ADR-*.md",
  "adr_regex": "^ADR-(\\d{4})-.*\\.md$",
  "discovered": {...},
  "version": 2
}
```

**v2 字段（per ADR-0016 + ADR-0042）**:
- `roadmap_fragments_dir` — 新增（v2_additive）
- `adr_regex` — 新增（v2_additive，Python regex 与 adr_pattern glob 区分）
- 顶层 `additionalProperties: true` — 未来字段可平滑扩展

**消费者** (per ADR-0016):
- guide-plan intake (via `read_arch_handoff`)
- detectors.py / actions.py
- scan-state.sh
- propose / roadmap
- gate.py

### 2.2 `.rddf/state/.planner-feedback.json`（rdd-planner owns）

Owner: rdd-planner。Schema: planner-feedback-v1（per ADR-0042）。

```json
{
  "schema": "planner-feedback-v1",
  "version": 1,
  "owner": "rdd-planner",
  "branch": "master",
  "worktree_root": "/workspace/project/rdd-workflow",
  "codebase_commit": "abc123",
  "arch_handoff_revision": 12,
  "planner_state_last_sync_at": "2026-09-03T10:00:00Z",
  "feedbacks": [
    {
      "feedback_id": "pf-20260903-001",
      "kind": "unmapped_proposal",
      "severity": "critical",
      "status": "open",
      "fingerprint": "a3f7b2c1e9d4f5a8",
      "proposal": "feat-cross-repo-auth",
      "theme": "",
      "related_adr_ids": [],
      "message": "proposal 'feat-cross-repo-auth' (P1) lacks theme_ref",
      "suggested_action": "add theme_ref to frontmatter or add matching Phase Skeleton theme",
      "created_at": "2026-09-03T10:00:00Z",
      "last_seen_at": "2026-09-03T10:00:00Z",
      "acknowledged_at": null,
      "resolved_at": null,
      "resolved_by": null,
      "dismissed_at": null,
      "dismissed_by": null,
      "computed_from": {
        "planner_state_revision": 5,
        "arch_handoff_revision": 12,
        "codebase_commit": "abc123"
      },
      "stale": false
    }
  ],
  "summary": {
    "open_critical": 1,
    "open_warning": 0,
    "open_info": 0,
    "acknowledged": 0,
    "resolved": 0,
    "dismissed": 0
  }
}
```

**字段语义**:

| 字段 | 语义 |
|---|---|
| `feedback_id` | 唯一 ID `pf-YYYYMMDD-NNN` |
| `kind` | enum: `unmapped_proposal` / `coverage_gap` / `adr_drift` / `roadmap_staleness` |
| `severity` | enum: `critical` / `warning` / `info` |
| `status` | enum: `open` / `acknowledged` / `resolved` / `dismissed` |
| `fingerprint` | sha256(kind+proposal+theme+related_adr_ids+reason)[:16]，幂等键 |
| `computed_from.codebase_commit` | git HEAD hash at compute time |
| `computed_from.arch_handoff_revision` | arch_complete_revision at compute time |
| `stale` | true if computed_from 任意字段与当前不匹配 |
| `branch` + `worktree_root` | 多 worktree 隔离 (沿用 ADR-0034) |

**Lifecycle**:
```
open  ──[architect sees]──>  acknowledged  ──[fixed]──>  resolved
                                                ╲
                                                 [waived]──>  dismissed
```

## 3. CLI 接口

### 3.1 planner 侧（写入反馈）

```bash
# 列出反馈
rddf planner feedback                                  # 列出所有（默认 open）
rddf planner feedback --status open                    # 过滤 status
rddf planner feedback --kind unmapped_proposal         # 过滤 kind
rddf planner feedback --json                           # JSON 输出

# 触发计算
rddf planner feedback --recompute                      # 从文件系统重算

# Lifecycle transitions
rddf planner feedback --acknowledge <FEEDBACK_ID>      # open → acknowledged
rddf planner feedback --resolve <FEEDBACK_ID>          # → resolved
rddf planner feedback --dismiss <FEEDBACK_ID>          # → dismissed

# 清理
rddf planner feedback --prune-resolved                 # 删除 resolved/dismissed
```

### 3.2 arch 侧（只读消费）

```bash
# 一行摘要（Phase 1 入口展示）
rddf arch status
# 输出: rdd-arch: phase-1 | 41 ADRs | Planner: 1 critical, 0 warning, 0 stale
# 或:   rdd-arch: (no arch-done yet) | Planner: No planner feedback

# 详细 handoff
rddf arch handoff
# 输出 .arch-handoff.json 内容

# 详细 feedback（read-only）
rddf arch feedback
# 输出 planner feedback 表格
```

## 4. 端到端流程

### 4.1 Happy Path（完全匹配）

```bash
# Step 1: 架构师定义 ADR + roadmap theme
cat > docs/adr/ADR-0043-foo.md <<EOF
> **状态**: 已采纳 (2026-09-03)
> **主题**: cross-repo-protocol
EOF

# Step 2: 改进提案带 theme_ref
cat > .rddf/improvements/feat-cross-repo-auth.md <<EOF
---
name: feat-cross-repo-auth
priority: P1
theme_ref: cross-repo-protocol
---
# feat-cross-repo-auth
EOF

# Step 3: arch-done
rddf arch status   # 触发 arch-done gate
# 输出: rdd-arch: phase-1 | 42 ADRs | Planner: No planner feedback

# Step 4: planner sync
rddf planner sync --apply
# 输出: ✓ State written | Sprint: sprint-2026-09

# Step 5: planner 触发 feedback recompute
rddf planner feedback --recompute
# 输出: ✓ Recomputed 0 feedback entry(ies)

# Step 6: 验证
rddf planner feedback
# 输出: No active planner feedback.
```

### 4.2 Revision Loop（未映射 → 修订 → 解决）

```bash
# Step 1: 初始状态 - 提案未映射
cat > .rddf/improvements/feat-cross-repo-auth.md <<EOF
---
name: feat-cross-repo-auth
priority: P1
# 故意不写 theme_ref
---
EOF

# Step 2: planner sync 检测
rddf planner sync --apply
rddf planner feedback --recompute
# 输出: ✓ Recomputed 1 feedback entry(ies)

# Step 3: 架构师看到反馈
rddf arch status
# 输出: rdd-arch: phase-1 | 41 ADRs | Planner: 1 critical, 0 warning, 0 stale

rddf arch feedback
# 输出:
#   | pf-20260903-001 | unmapped_proposal | critical | open | feat-cross-repo-auth | no |
#   Summary: {'open_critical': 1, 'open_warning': 0, ...}

# Step 4: 架构师修订
# 4a: 创建 ADR
rddf arch   # Phase 2 创建 ADR-0043

# 4b: 添加 roadmap theme（手工编辑 roadmap.md）

# 4c: 补 proposal theme_ref
sed -i 's/^---$/---\nname: feat-cross-repo-auth\ntheme_ref: cross-repo-protocol/' \
  .rddf/improvements/feat-cross-repo-auth.md

# Step 5: 重新 arch-done → arch_handoff_revision++
rddf arch status

# Step 6: planner 重新 sync → fingerprint 命中, computed_from.arch_handoff_revision 更新
rddf planner sync --apply
rddf planner feedback --recompute
# 输出: ✓ Recomputed 0 feedback entry(ies)  # 旧条目自动 resolved（proposal 现在已映射）

# Step 7: 验证 - 反馈已解决
rddf planner feedback --status resolved
# 输出: | pf-20260903-001 | resolved | ... |

# Step 8: 清理
rddf planner feedback --prune-resolved
# 输出: ✓ Pruned 1 resolved/dismissed feedback entry(ies)
```

### 4.3 Stale Detection（commit 切换）

```bash
# Step 1: planner 写反馈时绑定 commit
rddf planner sync --apply
rddf planner feedback --recompute
# .planner-feedback.json: codebase_commit = "abc123"

# Step 2: 架构师切换分支
git checkout feature-branch  # codebase_commit → "def456"

# Step 3: 重新 sync → arch_handoff_revision 不变, codebase_commit 变化
rddf planner sync --apply
rddf planner feedback --recompute
# 旧条目标记 stale=True（computed_from.codebase_commit 不匹配）

# Step 4: arch 显示 stale 警告
rddf arch status
# 输出: rdd-arch: phase-1 | 41 ADRs | Planner: 1 critical, 0 warning, 1 stale
```

## 5. Branch / Worktree 隔离

每个 worktree 拥有独立的 `.rddf/state/`：
- `.arch-handoff.json` 和 `.planner-feedback.json` 都带 `branch` 字段
- `worktree_root` 字段标记绝对路径
- 不同 worktree 的反馈不会互相串扰（fingerprint + computed_from 隔离）
- 沿用 ADR-0034 模式（verifier 已采用 branch identity）

## 6. 错误处理表

| 情况 | planner feedback write exit | arch-done gate | 主状态写入 | 反馈写入 |
|---|---:|---|---|---|
| `.arch-handoff.json` 缺失 | 0 (warning) | unchanged | 正常 | 写 (computed_from arch_handoff_revision=null) |
| `.arch-handoff.json` 损坏 | 3 | unchanged | 不覆盖 | 不写 |
| `.planner-feedback.json` 损坏 | 2 (rebuild) | unchanged | 不覆盖 | 重建为空 + 重新 compute |
| 反馈 lock 超时 (5s) | 3 | unchanged | 不覆盖 | 不写 |
| `.planner-state.json` schema 不匹配 | 3 | unchanged | 不写 | 不写 |
| `compute_planner_feedback` 异常 | 3 | unchanged | 保留旧 state | 不写 |
| `--acknowledge/resolve/dismiss` 反馈 id 不存在 | 2 | unchanged | — | 不写 |

## 7. 兼容性矩阵

| 用户入口 | canonical | legacy shim 行为 |
|---|---|---|
| `rddf arch` | `rdd-arch` | — |
| `skill_use("rdd-arch")` | `rdd-arch` | — |
| `skill_use("guide-arch")` | — | shim: 打印 DEPRECATED warning, 转发到 `rdd-arch`（保留至 v5.x + 2 minor release） |
| `rddf planner` | `rdd-planner` | — |
| `rddf planner feedback --clear` | — | 不支持（旧 v2.x `--clear` 语义模糊，已被 `--acknowledge/--resolve/--dismiss` 三命令取代） |
| `report-issue --phase guide-arch` | — | shim: 内部映射到 `rdd-arch` |

## 8. 消费者兼容（contract v2）

`.arch-handoff.json` v2 顶层 `additionalProperties: true`，所有 v1 consumer 仍能消费：
- `state_reader.read_arch_handoff()` — 透传所有字段
- `guide-plan/scripts/plan_intake.sh` — jq 提取 `adr_dir/roadmap_path/adr_pattern/adr_regex/version` 全部成功
- `detectors.py` / `actions.py` — 通过 `state_reader` 间接消费
- `scan-state.sh` — 推荐字符串更新（Stage 3 Change 1 已修复）

测试: `tests/unit/test_arch_handoff_v2_schema.py` 锁定 v1/v2 双向兼容（6 tests）。

## 9. References

- [ADR-0042](https://internal/adr/0042) — rdd-arch rename + bidirectional feedback contract
- [ADR-0016](https://internal/adr/0016) — arch-discovery-contract (handoff schema v1/v2)
- [ADR-0028](https://internal/adr/0028) — role-model-per-phase (rdd-arch / rdd-planner boundaries)
- [ADR-0034](https://internal/adr/0034) — 5-stage architecture + branch identity
- [ADR-0038](https://internal/adr/0038) — rdd-planner crosscutting scope
- [ADR-0041](https://internal/adr/0041) — planner sprint lifecycle
- [Plan](https://internal/plans/2026-09-03-rdd-workflow-stage3-rdd-arch-rename-and-bidirectional) — Stage 3 implementation plan