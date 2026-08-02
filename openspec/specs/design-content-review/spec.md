# design-content-review Specification

## Purpose
TBD - created by archiving change move-proposal-creation-to-design. Update Purpose after archive.
## Requirements
### Requirement: improvements 层内容审查

The system SHALL review `improvements/<name>.md` content at approve time, checking: 5-section completeness (架构依据/范围/关键场景/技术约束/验收标准), at least one `ADR-\d{4}` reference in 架构依据, quantifiable acceptance criteria, and presence of `**阶段**`/`**分类**` header fields. Failures are warnings by default; `STRICT_DESIGN_GATE=yes` MUST upgrade them to blocking errors.

#### Scenario: 缺段阻断（strict 模式）

- GIVEN `improvements/<name>.md` is missing the 验收标准 section and `STRICT_DESIGN_GATE=yes`
- WHEN the user attempts to approve the proposal
- THEN the approval is blocked and the failed checks are listed

#### Scenario: 默认 warning 放行

- GIVEN the same incomplete improvement without STRICT_DESIGN_GATE
- WHEN the user approves
- THEN warnings are printed but the approval proceeds

### Requirement: openspec proposal 层质量检查

After the complete `proposal.md` is generated, the system SHALL run the proposal-applicable subset of `propose_quality_check` (length ≥500 chars after skeleton-marker stripping, ≥1 ADR reference, In/Out Scope sections) and `openspec validate <name> --json`. Validation ERRORs from `openspec validate` MUST always block, regardless of strict mode. The tasks-completeness and roadmap-alignment checks SHALL remain in the plan phase (their targets do not exist at design time).

#### Scenario: 完整 proposal 通过检查

- GIVEN a generated `proposal.md` with ≥500 chars, an ADR reference, and In/Out Scope sections
- WHEN the openspec proposal layer runs
- THEN all 3 quality checks pass and `openspec validate <name> --json` reports no ERROR

