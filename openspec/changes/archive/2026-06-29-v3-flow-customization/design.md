## Context

ADR-0012 (625 lines) defines the flow customization layer on top of ADR-0011's step pipeline. Users customize phase templates via `.rdd-workflow/flow.yaml` using incremental override patterns (insert_after, replace, insert_before). No customization = default behavior unchanged.

## Goals / Non-Goals

**Goals:**
- `FlowCustomizer` — merges user `flow.yaml` customizations with default phase templates
- `TriggerEngine` — evaluates trigger conditions (restricted syntax, no eval)
- `.rdd-workflow/flow.yaml` — user configuration file
- Backward compatibility — no flow.yaml = identity merge
- Full test coverage

**Non-Goals:**
- Modifying existing guide-arch/guide-plan/guide-ship skills
- Implementing custom skill plugins (interface only)
- Multi-project flow sharing

## Decisions

### Decision 1: FlowCustomizer is a new module

Separate from step_pipeline.py. FlowCustomizer takes (template, flow_config) → merged template. StepPipeline runs the merged template.

### Decision 2: Trigger conditions use restricted syntax

Only `changes.any(predicate)` and `step.<id>.status == value`. No arbitrary eval. Safety by construction.

### Decision 3: flow.yaml is at project root, user-managed

`.rdd-workflow/flow.yaml` is gitignored (like other .zcf files). Users create it manually. Missing file = default behavior.

## Architecture

```
flow.yaml → FlowCustomizer → merged template → StepPipeline.run()
                ↑
         TriggerEngine (condition evaluation)
                ↑
         CustomSkillInterface (ABC for plugins)
```