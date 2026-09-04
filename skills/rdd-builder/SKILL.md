---
name: rdd-builder
description: |
  Proposal approval + plan + execute + archive. Stage 3 of v4 architecture.
  Implements 6-phase internal state machine: P0 (approval), P1 (plan gen),
  P1.5 (deps + execution_mode), P2 (worktree + execute), P2.5 (review),
  P3 (archive with verifier retry loop). Per spec §3.4.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, git 2.25+
  + rddf planner + rddf-verifier installed
metadata:
  author: rdd-workflow
  version: 1.0
  evolved-from: "guide-design + guide-plan + guide-ship"
  user-invocable: true
---

# rdd-builder Skill

Stage 3 of v4 architecture (per spec §3.4). 6-phase internal state machine:

```
P0 (approval) → P1 (plan) → P1.5 (deps + exec_mode) → P2 (execute) → P2.5 (review) → P3 (archive)
                                └─── verifier retry loop (P3 → P1 or P2, max 3) ───┘
```

Pause contract (per spec §5.2):
- HARD pause at P0 / P2.5
- SOFT pause at P1 / P1.5 / verifier back-route

Exit codes: 0 (success), 1 (P0 reject), 2 (plan quality), 3 (worktree/COMMIT), 4 (verifier halt), 5 (review revise), 6 (deps gate), 7 (archive gate).

Cross-stage feedback (per spec §3.5.2 batch 4):
- Phase 2 ADR-drift detection → `rddf feedback add --kind ac-fail --from rdd-builder`
- Routed via `_lib/builder_feedback_router.py` to `.planner-feedback.json`
- Architect reads via `rddf arch feedback` (advisory)