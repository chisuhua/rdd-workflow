# design-proposal-creation Specification

## Purpose
TBD - created by archiving change move-proposal-creation-to-design. Update Purpose after archive.
## Requirements
### Requirement: 批准即创建完整 openspec change

The system SHALL create a complete OpenSpec change when a proposal is approved in the design phase. Creation MUST include: `openspec new change <name>` scaffolding, a COMPLETE `proposal.md` converted from the improvement's 5-section content, `roadmap-meta.yaml` (including `change_type` mapped from the improvement's `**类型**` header), and an `iteration.json` entry with status=`planned`. The complete `proposal.md` MUST be presented to the user for confirmation before being written to disk. Creation MUST be idempotent: if `openspec/changes/<name>/` already exists, the system SHALL skip creation without error.

#### Scenario: 单条批准创建完整 change

- GIVEN a pending proposal with a complete `improvements/<name>.md` (5 sections present)
- WHEN the user approves it in design review (`y`)
- THEN the system generates a complete `proposal.md` draft via the fixed mapping (架构依据 → Why; 范围+关键场景 → What Changes; 技术约束涉及面 → Capabilities/Impact; 验收标准 → Acceptance)
- AND presents the draft for user confirmation before writing
- AND after confirmation writes `.openspec.yaml` + `proposal.md` + `roadmap-meta.yaml` and registers the change in `iteration.json` with status=`planned`

#### Scenario: 幂等保护

- GIVEN `openspec/changes/<name>/` already exists
- WHEN the approve action runs again for the same proposal
- THEN the system skips creation and does not overwrite any existing artifact

### Requirement: 元数据来源优先级

The system SHALL read `phase`/`category` from the improvement file's `**阶段**`/`**分类**` header fields when creating `roadmap-meta.yaml`. Fallback to `default`/`general` is allowed only when the header fields are absent, and MUST emit a warning. Hardcoding `default`/`general` without reading the header is forbidden.

#### Scenario: 头部字段优先

- GIVEN `improvements/<name>.md` has `**阶段**: v2.1` and `**分类**: planning`
- WHEN the change is created at approve time
- THEN `roadmap-meta.yaml` contains `phase: "v2.1"` and `category: "planning"` (not `default`/`general`)

