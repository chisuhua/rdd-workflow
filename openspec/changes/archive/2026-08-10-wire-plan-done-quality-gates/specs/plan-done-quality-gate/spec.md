# plan-done-quality-gate Specification

## Purpose
TBD - created by archiving change wire-plan-done-quality-gates. Update Purpose after archive.
## ADDED Requirements

### Requirement: run_plan_checks 在 plan_done_gate 正常执行路径中被调用

The system SHALL invoke `run_plan_checks` during the normal `guide-plan` `plan_done_gate` execution path so that existing plan-checks utilities produce visible results in the gate output. Default failures MUST be reported as warnings per ADR-0007 and MUST NOT block the plan-done gate.

#### Scenario: 默认环境下 warning 不阻断

- GIVEN `guide-plan` 正常执行到 `plan_done_gate`
- AND a change artifact under `openspec/changes/<name>/` is in scope
- WHEN `plan_done_gate` runs without `STRICT_CHANGE_GATE` set
- THEN `run_plan_checks` is invoked at least once per change
- AND any `run_plan_checks` failure is reported as a warning
- AND `plan_done_gate` still completes successfully

#### Scenario: 调用发生于检查资产可用但未生效的修复

- GIVEN `run_plan_checks` exists in the codebase but the current `plan_done_gate` path may not call it
- WHEN the wiring change is applied
- THEN `plan_done_gate` calls `run_plan_checks` via the documented entry point
- AND the call is observable in gate output or event log

### Requirement: change_alignment 接入 plan_done_gate 与 STRICT_CHANGE_GATE 升级语义

The system SHALL invoke `change_alignment` during the normal `plan_done_gate` path and SHALL preserve the existing independent `STRICT_CHANGE_GATE=yes` escalation defined by ADR-0019: default mode reports failures as warnings; strict mode upgrades `change_alignment` failures to errors that block the gate.

#### Scenario: 默认 warning

- GIVEN `change_alignment` returns a failure for a plan artifact
- WHEN `plan_done_gate` runs without `STRICT_CHANGE_GATE=yes`
- THEN the failure is reported as a warning
- AND `plan_done_gate` still completes successfully

#### Scenario: STRICT_CHANGE_GATE 升级为 error

- GIVEN `change_alignment` returns a failure
- WHEN `STRICT_CHANGE_GATE=yes` is set in the environment
- THEN the failure is escalated to an error
- AND `plan_done_gate` returns non-zero or equivalent failure status
- AND downstream phase transition is blocked

#### Scenario: 严格模式仅影响 change_alignment

- GIVEN `STRICT_CHANGE_GATE=yes`
- WHEN `plan_done_gate` runs
- THEN the escalation applies only to `change_alignment` failures
- AND `run_plan_checks` and other existing error checks retain their existing semantics

### Requirement: 检查结果在 gate 输出与事件记录中可见

The system SHALL make `run_plan_checks` and `change_alignment` results visible in `plan_done_gate` output and event records, including the check name, pass status, and failure reason, covering all three result classes: pass, warning, strict error.

#### Scenario: 通过状态可见

- GIVEN both `run_plan_checks` and `change_alignment` pass
- WHEN `plan_done_gate` runs
- THEN the gate output records both check names with passing status

#### Scenario: 失败原因不静默

- GIVEN a check returns a structured failure
- WHEN `plan_done_gate` summarizes results
- THEN the gate output identifies which check failed and why
- AND does not silently swallow the result
- AND does not escalate a default warning into a blocking error

### Requirement: 不修改既有检查规则与 ADR 既有语义

The system MUST NOT modify the existing rules of `run_plan_checks` or `change_alignment` to mask failures, and MUST NOT bypass results via default skip, silent exception handling, or renaming checks. The wiring MUST honor ADR-0007 (gate mechanism) and ADR-0019 (change alignment) without overriding their existing semantics.

#### Scenario: 既有检查规则不被重写

- GIVEN the existing `run_plan_checks` and `change_alignment` rule sets
- WHEN the wiring change is applied
- THEN the rule sets are unchanged
- AND only the invocation path and output surface are modified