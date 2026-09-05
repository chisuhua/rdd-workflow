---
name: rdd-planner
description: |
  Roadmap + proposal authoring orchestrator (Stage 2 of v4 architecture).
  Wraps existing `_lib/planner_*.py` lib (per ADR-0037/0038/0042) and adds
  stage entry/exit contract. Per spec 2026-09-04-rdd-workflow-v4-architecture-stage-merge.md
  §3.3 (promotion from horizontal orchestrator to full stage).

  Owns:
  - roadmap.md
  - proposal-suggestions.md / proposal-approved.md
  - .rddf/roadmap/features/*.md
  - .rddf/improvements/*.md (via add-improve)
  - openspec/changes/<name>/proposal.md (authoring only)

  Existing horizontal-orchestrator commands remain available:
  status / sync / feedback / attach / audit / history / advance-sprint

  Stage entry: planner_stage_entry.sh (emits .planner-handoff.json)
  Stage exit: planner_stage_exit.sh (consumes arch-handoff, emits planner-handoff)

  Backward compat: legacy .plan-handoff.json::execution_mode_decisions
  is read as fallback in rdd-builder Phase 1.5 during Wave 1 coexistence.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, git 2.25+
metadata:
  author: rdd-workflow
  version: 2.1
  evolved-from: "guide-design + roadmap"
  user-invocable: true
role:
  title: "Planner (路线图 + 提案治理者)"
  perspective: "Think in terms of roadmap coverage, proposal authoring workflow, and sprint lifecycle. Bridge arch definitions (rdd-arch) with execution (rdd-builder)."
  boundaries:
    owns:
      - "roadmap.md"
      - "proposal-suggestions.md"
      - "proposal-approved.md"
      - ".rddf/roadmap/features/*.md"
      - ".rddf/improvements/*.md"
      - "openspec/changes/<name>/proposal.md (authoring only)"
      - ".rddf/state/.planner-state.json"
      - ".rddf/state/.planner-feedback.json"
      - ".rddf/state/.planner-handoff.json"
    not_owns:
      - "docs/adr/ADR-*.md"
      - "openspec/changes/<name>/{design,tasks}.md"
      - ".rddf/wt/<name>/"
      - ".rddf/plans/<name>.md"
      - ".rddf/state/builder/<name>.json"
    human_involvement: "medium"
---

# rdd-planner Skill

Stage 2 of v4 architecture (per spec §3.3). 4-stage flow:

```
rdd-arch (v3 slim) → rdd-planner → rdd-builder (P0/P1/P1.5/P2/P2.5/P3) → rdd-verifier
```

## Entry / Exit Contract

**Stage entry** (run after rdd-arch done):
```bash
bash skills/rdd-planner/scripts/planner_stage_entry.sh [change-name]
# Writes .rddf/state/.planner-handoff.json (schema v1)
```

**Stage exit** (run before rdd-builder starts):
```bash
bash skills/rdd-planner/scripts/planner_stage_exit.sh [change-name]
# Emits .planner-handoff.json with proposals_authored + features_active
```

## Cross-stage feedback channel

Per ADR-0042: planner writes feedback to `.rddf/state/.planner-feedback.json`
(schema `planner-feedback-v1`). Architect (rdd-arch) reads via `rddf arch feedback`
(advisory, read-only).

Per spec §3.5.2 (batch 4): rdd-builder Phase 2 ADR-drift can promote feedback
(kind=ac-fail + ref_change match) to `.planner-feedback.json` via
`_lib/builder_feedback_router.py`. Default ON in v4; architect opt-in via
`rddf planner feedback --accept-builder-source {yes|no}`.

## See also

- `skills/roadmap/` — roadmap CRUD (rddf roadmap add-feature, etc.)
- `skills/add-improve/` — proposal authoring entry
- `_lib/planner_*.py` — Stage 1/2 lib (unchanged)
- `_lib/planner_handoff.py` — NEW in Wave 1: stage handoff r/w