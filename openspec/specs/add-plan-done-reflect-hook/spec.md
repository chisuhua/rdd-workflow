# add-plan-done-reflect-hook Specification

## Purpose
TBD - created by archiving change add-plan-done-reflect-hook. Update Purpose after archive.
## Requirements
### Requirement: plan-done-reflect-hook

`skills/rdd-planner/scripts/planner_stage_exit.sh` MUST trigger `ReflectEngine(phase='plan').analyze()` after successfully writing `.planner-handoff.json`, mirroring the existing arch-done hook pattern (`write_arch_handoff.sh:48-66`). The hook is bypassable via `SKIP_WORKFLOW_REFLECTION=1` env var and is non-blocking (`2>/dev/null || true`).

Additionally, `skills/rdd-planner/SKILL.md` MUST include a "Phase Exit — Post-Flow Analysis" section mirroring `rdd-arch/SKILL.md:712-730` (with phase identifier swapped), instructing the AI agent to either call `orchestrator_finalize` (normal exit) or `orchestrator_finalize` + `rddf report-issue --phase rdd-planner` (abnormal exit).

#### Scenario: plan-done hook triggers on normal exit

- **WHEN** `skills/rdd-planner/scripts/planner_stage_exit.sh` completes successfully (writes `.planner-handoff.json`)
- **THEN** `ReflectEngine(phase='plan').analyze()` is invoked with failures sourced from `.rddf/state/event_log.json` last 20 entries filtered for `unrecovered_failure` / `execute_error` kinds
- **AND** the result is persisted to `.rddf/state/.plan-reflect-result.json`
- **AND** reflect engine exceptions are swallowed (`2>/dev/null || true`) — planner exit code remains 0

#### Scenario: SKIP_WORKFLOW_REFLECTION=1 bypasses bash hook

- **WHEN** `SKIP_WORKFLOW_REFLECTION=1` is set in env when `planner_stage_exit.sh` runs
- **THEN** the bash inline hook is NOT executed
- **AND** `planner_stage_exit.sh` still returns 0 (exit code unaffected)
- **AND** `.planner-handoff.json` is still written normally

#### Scenario: SKILL.md Phase Exit section is the agent-plane companion

- **WHEN** an AI agent finishes the rdd-planner phase normally
- **THEN** the SKILL.md "Phase Exit — Post-Flow Analysis" section instructs the agent to call `orchestrator_finalize`
- **AND** when the agent encounters an abnormal condition (per the section's trigger list), the section instructs `rddf report-issue --phase rdd-planner --exit-code <code> "<one-line>"`
- **AND** the bash hook and SKILL.md section operate independently (dual-plane per ADR-0027 §1.0) — neither blocks the other

