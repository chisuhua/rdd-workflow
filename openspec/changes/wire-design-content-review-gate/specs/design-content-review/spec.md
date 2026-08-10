# design-content-review Specification

## Purpose
Review improvements and proposals at design approve time. Modified by archiving change wire-design-content-review-gate.
## MODIFIED Requirements

### Requirement: improvements 层内容审查在 approve 流中实际被调用

The system SHALL invoke the existing `skills/guide-design/scripts/design_content_review.sh` as part of the `guide-design` approve execution path (both single-item and batch), so that improvements-layer content review (5-section completeness, ADR reference, quantifiable acceptance, head fields per ADR-0025 §D4) runs on every normal approve. Failures default to warning per ADR-0025 §D4; `STRICT_DESIGN_GATE=yes` MUST upgrade them to blocking errors; `SKIP_CONTENT_REVIEW=yes` MUST skip the review without affecting other approve semantics.

modifies: design-content-review

#### Scenario: 单项 approve 默认 warning 放行

- GIVEN the user invokes single-item approve on an improvement that fails improvements-layer review (e.g. missing ADR reference)
- AND `SKIP_CONTENT_REVIEW` is not `yes`
- AND `STRICT_DESIGN_GATE` is not `yes`
- WHEN the approve flow runs
- THEN `design_content_review.sh` is invoked once before any approve-side-effect
- AND the review warning is shown in terminal output
- AND the approve flow still completes successfully

#### Scenario: STRICT_DESIGN_GATE 阻断 approve-side-effect

- GIVEN the user invokes approve on an improvement that fails improvements-layer review
- AND `STRICT_DESIGN_GATE=yes`
- WHEN the approve flow runs
- THEN `design_content_review.sh` is invoked
- AND its blocking result prevents any approve-side-effect (status write, proposal landing, iteration.json mutation)

#### Scenario: SKIP_CONTENT_REVIEW 跳过 review 不影响其他语义

- GIVEN `SKIP_CONTENT_REVIEW=yes`
- WHEN the approve flow runs
- THEN `design_content_review.sh` is NOT invoked
- AND other approve gates and user-confirmation steps still run as before
- AND terminal output indicates the review was skipped via the escape hatch

#### Scenario: 批量 approve 逐项独立调用 review

- GIVEN the user invokes batch approve over multiple improvements
- WHEN the approve flow processes the batch
- THEN `design_content_review.sh` is invoked once per improvement, in the same shared helper path
- AND one item's blocking result does NOT silently bypass review for sibling items
- AND one item's warning does NOT swallow another item's blocking result

### Requirement: 既有 review 脚本不被复制或重写

The system MUST NOT duplicate or reimplement `design_content_review.py`'s checks, prompts, or severity rules inside the approve wrapper. The wrapper MUST reference the existing script as the single source of truth for improvements-layer review semantics, and MUST NOT introduce a second improvements-layer review implementation, an independent state format, or any new quality gate beyond ADR-0025 §D4.

modifies: design-content-review

#### Scenario: wrapper 仅调用既有脚本

- GIVEN the approve wrapper code
- WHEN a static check or script test inspects it
- THEN it only references the existing `design_content_review.sh` by path
- AND it does not contain duplicated check logic (regex re-implementations, severity tables, prompt strings) that mirror `design_content_review.py`