## Context

ADR-0011 defines a step-pipeline execution model that replaces the current monolithic phase execution (arch/plan/ship as black boxes) with composable step sequences. This enables custom step insertion, skill replacement, and condition-based triggers. The ADR is 456 lines with complete design, YAML templates, and code samples.

## Goals / Non-Goals

**Goals:**
- `skills/_lib/phase_templates.yaml` — YAML template defining step sequences for arch/plan/ship
- `skills/_lib/step_pipeline.py` — StepPipeline executor with step-level event logging, skip-completed (interruption recovery), and run-step-by-step
- `skills/loop_engine.py` — Revise `match_actions()` to trigger phase templates
- Full test coverage for StepPipeline

**Non-Goals:**
- Modifying existing guide-arch/guide-plan/guide-ship skill files (phase templates replace their bash logic, not the skills themselves)
- Implementing the ADR-0012 flow customization layer (depends on this change)
- Breaking v2.0 behavior when no custom templates exist

## Decisions

### Decision 1: YAML, not Python, for phase templates

Phase templates are YAML so users can customize without writing Python. `phase_templates.yaml` ships as built-in default. Users can override via `.spec-workflow/phase-templates.yaml`.

### Decision 2: StepPipeline is a new module, not embedded in loop_engine.py

Separation of concerns: loop_engine.py handles the scan→plan→execute→verify→adapt cycle; step_pipeline.py handles the internal execution of a selected phase. The `match_actions()` method becomes a thin bridge.

### Decision 3: No template = fallback to v2.0 behavior

If `phase_templates.yaml` is missing or a phase has no template, `match_actions()` falls back to the current direct-action dispatch. Zero breakage.

### Decision 4: Interruption recovery via step status tracking

StepPipeline tracks `completed_steps` per phase in the state vector. On re-entry, it skips completed steps and resumes from the first uncompleted step.

## Architecture

```
LoopEngine.match_actions()
  → trigger_phase("plan", change)
    → StepPipeline.run("plan", change)
      → load phase_templates.yaml
      → filter completed steps (from state vector)
      → for each uncompleted step:
          → execute step (call detector function or action function)
          → log event (step-level)
          → mark completed in state vector
      → return execution result

State vector storage:
  step_pipeline_state: {
    phase: "plan",
    completed_steps: ["scan_candidates", "select_changes"],
    current_step: null,
    started_at: "...",
    error: null
  }
```