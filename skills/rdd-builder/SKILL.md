---
name: rdd-builder
description: |
  Proposal approval + plan + execute + archive. Stage 3 of v4 architecture.
  Implements 6-phase internal state machine: P0 (approval, 5-option per ADR-0048),
  P1 (plan gen), P1.5 (deps + execution_mode), P2 (worktree + execute),
  P2.5 (review), P3 (archive with verifier retry loop). Per spec §3.4.
  P0 5-option includes **dispatch-quick** (per ADR-0048 §Decision 3) which
  routes the change to `rdd-quick` fast-path when `recommended_route=simple`.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, git 2.25+
  + rddf planner + rddf-verifier installed
metadata:
  author: rdd-workflow
  version: 1.1
  evolved-from: "guide-design + guide-plan + guide-ship"
  user-invocable: true
role:
  title: "Builder (审批 + 执行 + 归档治理者)"
  perspective: "Think in terms of phase state machine progression, TDD discipline, verifier retry routing, AND dispatch-quick routing (per ADR-0048). Owns the actual change implementation lifecycle from approval to archive."
  boundaries:
    owns:
      - "openspec/changes/<name>/proposal.md (authoring via P0 approve, per ADR-0025)"
      - "openspec/changes/<name>/{tasks,design}.md"
      - ".rddf/wt/<name>/"
      - ".rddf/plans/<name>.md"
      - ".rddf/state/builder/<name>.json"
      - "openspec/specs/<name>/spec.md"
      - ".rddf/state/rdd-quick-context.json (临时, per ADR-0048)"
    not_owns:
      - "docs/adr/ADR-*.md"
      - "roadmap.md"
      - ".rddf/state/.planner-feedback.json"
      - ".rddf/plans/quick-*.md (rdd-quick owns, per ADR-0047)"
    human_involvement: "medium"
---

# rdd-builder Skill

Stage 3 of v4 architecture (per spec §3.4). 6-phase internal state machine:

```
P0 (approval, 5-option per ADR-0048) → P1 (plan) → P1.5 (deps + exec_mode)
                                       → P2 (execute) → P2.5 (review) → P3 (archive)
                                       └─── verifier retry loop (P3 → P1 or P2, max 3) ───┘
```

## P0 Approval Gate (5-option, per ADR-0048)

**入口**: rdd-planner 写完 `.planner-handoff.json` 后, 用户调用 `skill_use("rdd-builder")` 进入 P0.

**P0 读取**:
- `openspec/changes/<change>/proposal.md` (由 rdd-planner attach, 或 propose 子技能骨架, 或 P0 approve 时生成 per ADR-0025 D1/D2)
- `.rddf/state/.planner-handoff.json::recommended_route` (REQUIRED per ADR-0048)
- `openspec/changes/<change>/proposal.md` 中的 `## 验收标准` checkbox 数

**P0 prompt (HARD pause, 5-option)**:

```
══════════════════════════════════════════════
rdd-builder Phase 0: Approval Gate (HARD pause)
══════════════════════════════════════════════
变更: <change-name>
Planner advisory: recommended_route = simple|complex|unknown
AC 数量: N 个 (from proposal.md ## 验收标准)

💡 推荐选项 (per planner advisory):
   - recommended_route=simple AND AC ≤ 2 AND files ≤ 2 AND 无 public interface 改动
     → 💡 推荐选项 5 (dispatch-to-quick)
   - 其他情况
     → 选项 1 (approve) 是常规路径

请选择:
  1. ✅ approve       → 继续 Phase 1 plan gen
  2. ❌ reject        → rddf feedback add --kind rejected, exit 0 (no archive)
  3. ⏸ defer         → rddf feedback add --kind blocked, exit 0 (no archive)
  4. 🔄 revise        → rddf feedback add --kind needs-revision, exit 1
  5. ⚡ dispatch-quick → 转 rdd-quick (per ADR-0047 + ADR-0048 §Decision 3)
                       仅当 recommended_route=simple 时启用
                       → 创建 .rddf/state/rdd-quick-context.json 临时文件
                       → 委托 skill_use("rdd-quick") with --from-builder flag
                       → rdd-quick 完成后: 直接 openspec archive (跳过 P1-P3)
                                          或回 P0 重新决策 (用户选择)
══════════════════════════════════════════════
```

**P0 选项 5 (dispatch-quick) 触发逻辑** (per ADR-0048 §Decision 3):
- 前置条件: `recommended_route == "simple"`
- 写 `.rddf/state/builder/<change>.json::approval_status = "dispatched_to_quick"`
- 创建 `.rddf/state/rdd-quick-context.json` 临时文件, 包含:
  ```json
  {
    "change_name": "<change>",
    "proposal_path": "openspec/changes/<change>/proposal.md",
    "from_builder": true,
    "dispatched_at": "2026-09-09T...",
    "expected_outcome": "completed|escalated|unverified"
  }
  ```
- 关闭 `stage_builder` rddf-session
- 委托 `skill_use("rdd-quick") --from-builder`
- rdd-quick 完成时:
  - outcome=completed → 直接 `openspec archive <change> --yes` (跳过 P1-P3)
  - outcome=unverified → 回 P0 重新决策
  - outcome=escalated → 回 P0 重新决策 (失败升级契约 per ADR-0047 amendment)

**Pause contract** (per spec §5.2):
- HARD pause at P0 / P2.5 (用户必须显式选择,不能跳过)
- SOFT pause at P1 / P1.5 / verifier back-route (`--no-pause` 可跳过)

**Exit codes**: 0 (success), 1 (P0 reject), 2 (plan quality), 3 (worktree/COMMIT), 4 (verifier halt), 5 (review revise), 6 (deps gate), 7 (archive gate).

Cross-stage feedback (per spec §3.5.2 batch 4):
- Phase 2 ADR-drift detection → `rddf feedback add --kind ac-fail --from rdd-builder`
- Routed via `_lib/builder_feedback_router.py` to `.planner-feedback.json`
- Architect reads via `rddf arch feedback` (advisory)

P0 → rdd-quick dispatch 通道 (NEW per ADR-0048):
- 读取 `.planner-handoff.json::recommended_route` 作主信号
- 写 `.rddf/state/rdd-quick-context.json` 临时文件
- 委托 `skill_use("rdd-quick") --from-builder`