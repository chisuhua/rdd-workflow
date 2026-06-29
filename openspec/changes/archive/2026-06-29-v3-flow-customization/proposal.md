## Why

ADR-0012 builds on ADR-0011's step pipeline to expose a **flow customization layer** to users. Today, every spec-workflow project follows the same default phase step sequence. Real-world projects need to:

- Insert custom steps inside a phase (e.g. compliance review after `generate_proposal`)
- Replace default skills for a step (e.g. swap `prometheus-planning` for an internal planner)
- Trigger steps conditionally (e.g. only run security audit when `changes.any(has_security_impact)`)
- Handle step failures with strategy (back-to / skip / abort / escalate to human)

ADR-0012 introduces `.spec-workflow/flow.yaml` using an **incremental override** model: users declare only deltas (insert / replace / insert_before) and the default template is merged automatically — so spec-workflow upgrades that add new default steps do not break user customizations.

The design also addresses safety: trigger expressions use a restricted DSL (no `eval`, no arbitrary Python) and step failures are bounded by `on_failure_max_retries` to prevent infinite back-to loops.

## What Changes

- **`.spec-workflow/flow.yaml` schema**: Versioned configuration file with `customizations.<phase>` containing `insert_after` / `insert_before` / `replace` directives
- **`FlowCustomizer`**: Merge engine (~250 LOC) that combines user deltas with the default `phase_templates.yaml` to produce the final effective step sequence per phase
- **`TriggerEngine`**: Restricted DSL parser (~200 LOC) supporting `always` / `never` / `changes.any(predicate)` / `state.*` field access / `and` / `or` / `not` / comparisons — **without** `eval` or `exec`
- **Failure handling**: `on_failure` strategies (`back_to:<step>` / `skip` / `abort` / `escalate_to_human`) bounded by `on_failure_max_retries`
- **`CustomSkillInterface` ABC**: Strict interface (`execute(context, params) -> StepResult`) every user-defined custom step must implement
- **Verification reuse**: Custom steps can opt into ADR-0005 verification modes (`human` / `multi_model` / `script` / `auto`)
- **Backward compatibility**: Without `.spec-workflow/flow.yaml`, the effective step sequence equals the default template — zero behavior change
