## Why

ADR-0011 addresses a core conflict in the v2.0 Loop engine (ADR-0004): phases (`arch`/`plan`/`ship`) currently execute as **opaque black boxes** invoked by `match_actions()`. This means:

- Users cannot insert custom steps inside a phase (e.g. compliance review inside `plan`)
- Users cannot substitute the default skill for a phase step with their own (e.g. swap `prometheus-planning` for a custom planner)
- There is no fine-grained observability into what is happening mid-phase
- Interruption recovery is coarse-grained (resume the whole phase, not the next un-completed step)

ADR-0011 introduces a **step pipeline execution model** that splits each phase into a sequenced list of steps defined in `phase_templates.yaml`, while remaining compatible with ADR-0004's dynamic-matching dispatch. This change is the prerequisite for ADR-0012 (flow customization), which depends on step-level insertion points.

## What Changes

- **`phase_templates.yaml`**: New declarative template file defining the default step sequence for each phase (`arch`, `plan`, `ship`) — detectors and actions, per ADR-0011 §"步骤模板定义"
- **`StepPipeline` executor**: New `skills/_lib/step_pipeline.py` (~350 LOC) that runs a template's steps in order, supports per-step skip on already-completed state, and records step-level events
- **`StepContext`**: Shared mutable data passed between steps within a single pipeline execution
- **`match_actions()` revision**: Updated per ADR-0011 §"与 ADR-0004 的关系" — `match_actions` now returns `trigger_phase(name)` triggers instead of direct action invocations; the trigger invokes `StepPipeline` for the named phase
- **Step-level event log entries**: New event types `step_started` / `step_completed` / `step_skipped` alongside existing `phase_started` / `phase_completed`
- **Interruption recovery**: Pipeline resumes from the last un-completed step instead of restarting the whole phase
- **Backward compatibility**: When `phase_templates.yaml` is absent or empty, the engine falls back to the v2.0 black-box behavior so no existing workflow breaks
