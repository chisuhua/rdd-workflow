# workflow-design-phase Specification

## Purpose
TBD - created by archiving change add-guide-design-phase. Update Purpose after archive.
## Requirements
### Requirement: design Phase State Machine

The system SHALL provide a `guide-design` skill as a first-class workflow phase between `arch` and `plan`. The design phase SHALL own the proposal lifecycle (creation via integrated `add-improve`, review, approval/rejection/deferral) and SHALL produce `.rddf/state/.design-handoff.json` as its completion marker. The design phase SHALL expose exactly 5 phases: setup / intake / review / gate / exit.

#### Scenario: design phase entry

- GIVEN arch-done handoff (`.rddf/state/.arch-handoff.json`) exists
- WHEN user invokes `skill_use("guide-design")`
- THEN Phase 1 setup reads arch-handoff, creates rddf-session `stage_design` with parent=`stage_arch`, and displays arch context (ADR count, roadmap phase, gap analysis count)
- AND design phase SHALL hard-block with `return 1` if arch-handoff is missing, suggesting `skill_use("guide-arch")`

#### Scenario: proposal review interactions

- GIVEN design phase Phase 2 scans `improvements/` directory and `proposal-suggestions.md`
- WHEN user is shown a pending proposal
- THEN user can choose: `y` (approve → append to `proposal-approved.md`), `n` (reject → mark `已拒绝`), `d` (defer → mark `延迟`), `s` (skip), or `a` (batch approve all pending proposals, preserving current `arch_proposal_review.sh` behavior)
- AND each decision updates the `状态` column of `proposal-suggestions.md` to one of the exact values `{待讨论, 已批准, 已拒绝, 延迟}` (per `docs/proposal-suggestions-format.md`)

#### Scenario: design-done gate

- GIVEN user invokes design phase Phase 4
- WHEN every entry in `proposal-suggestions.md` has `状态` ∈ {`已批准`, `已拒绝`, `延迟`}
- THEN the gate passes
- AND if any entry still has `状态` = `待讨论`, the gate SHALL be blocked and list the undecided proposals

#### Scenario: design-done handoff writing

- GIVEN design-done gate passes
- WHEN Phase 5 exit executes
- THEN `.rddf/state/.design-handoff.json` SHALL be written via `write_design_handoff.{sh,py}` (env-var pattern) with: `design_complete_at` (ISO 8601 UTC), `proposals_reviewed` (int ≥ 0), `all_proposals_have_decision` (true), `version` (1)
- AND rddf-session `stage_design` SHALL be closed

#### Scenario: design phase re-run semantics

- GIVEN `.design-handoff.json` already exists
- WHEN user re-invokes `skill_use("guide-design")` AND no new pending proposals exist
- THEN the phase SHALL NOOP and hint "design-done 已完成,无新提案"
- WHEN user re-invokes AND new pending proposals exist
- THEN only the new proposals SHALL be reviewed, and the handoff SHALL be overwritten with refreshed `design_complete_at`

### Requirement: design-handoff Contract

The system SHALL define `.rddf/state/.design-handoff.json` as a v1-schema JSON document with exactly 4 required fields and `additionalProperties: false`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `design_complete_at` | string (ISO 8601) | yes | UTC timestamp when design-done gate passed |
| `proposals_reviewed` | integer ≥ 0 | yes | Count of proposals with decisions |
| `all_proposals_have_decision` | boolean | yes | True if all suggestions have decisions |
| `version` | integer (const 1) | yes | Schema version |

#### Scenario: schema validation rejection

- GIVEN `.design-handoff.json` exists but is missing a required field OR has `version != 1`
- WHEN plan phase reads it
- THEN plan intake SHALL reject with error "design-handoff validation failed" and suggest `skill_use("guide-design")`

### Requirement: arch Phase 5.5 Deprecation

The `guide-arch` skill SHALL no longer contain Phase 5.5. Proposal management SHALL be exclusively owned by `guide-design`. Old script paths SHALL be replaced by wrapper-function shims (not immediately-executing scripts).

#### Scenario: deprecation-text (single source of truth)

- The exact deprecation text SHALL be: `⚠️ DEPRECATED: guide-arch Phase 5.5 已迁移到 guide-design (v2.1);请使用 skill_use("guide-design")`
- This text SHALL be used identically in: the guide-arch SKILL.md deprecation notice box, the `arch_proposal_review.sh` shim stderr output, and the `approve_proposal.sh` shim stderr output

#### Scenario: deprecated shim as wrapper function

- GIVEN `skills/guide-arch/scripts/arch_proposal_review.sh` is replaced by a shim
- WHEN a caller sources the shim and then invokes `arch_proposal_review <args>`
- THEN the shim SHALL define `arch_proposal_review()` as a wrapper that prints the deprecation text to stderr and forwards to `design_proposal_review "$@"`
- AND the shim SHALL NOT execute any function at file scope when sourced
- AND the shim SHALL retain a `[[ "${BASH_SOURCE[0]}" == "${0}" ]]` guard for direct execution

#### Scenario: deprecation window

- Deprecated shims SHALL remain active through all v2.1.x patch releases and SHALL be removed in v2.2.0

#### Scenario: arch-done simplification

- GIVEN `guide-arch` Phase 5 gate passes
- WHEN Phase 6 (arch-done exit) executes
- THEN arch-done SHALL only check ADR count ≥ 1 + roadmap.md exists
- AND arch-done output SHALL NOT mention proposal counts
- AND arch-done output SHALL end with `💡 Next: skill_use("guide-design")`

### Requirement: plan Phase Design-done Gate (hard switch)

The `guide-plan` skill SHALL gate on `.design-handoff.json` after the arch-handoff check. The gate is enforced by default (hard switch).

#### Scenario: missing design-handoff (legacy break)

- GIVEN `.design-handoff.json` does not exist AND direct-create fallback does not apply
- WHEN user invokes `skill_use("guide-plan")`
- THEN plan intake SHALL fail with an error containing `skill_use("guide-design")`

#### Scenario: gate placement and SKIP_ARCH_HANDOFF exemption

- GIVEN `SKIP_ARCH_HANDOFF=yes` is set
- WHEN user invokes `skill_use("guide-plan")`
- THEN BOTH arch-handoff and design-handoff checks SHALL be skipped with a warning
- GIVEN `SKIP_DESIGN_HANDOFF=yes` is set (without SKIP_ARCH_HANDOFF)
- THEN only the design gate SHALL be skipped with a warning

#### Scenario: direct-create fallback exemption

- GIVEN a project has archived changes under `openspec/changes/archive/` (direct-create fallback applies)
- WHEN `.design-handoff.json` is missing
- THEN the design gate SHALL be exempted, consistent with the existing arch-handoff fallback behavior

#### Scenario: hard-switch banner co-commit

- The commit that enables the design gate SHALL also contain a prominent banner at the top of `README.md` and an updated four-phase table in `AGENTS.md`, instructing legacy projects to run `guide-design` first or set `SKIP_ARCH_HANDOFF=yes` temporarily

### Requirement: Dual-Scanner 4-State Recommender

Both workflow recommenders — `skills/_lib/cli/guide_cmd.py::_scan_state()` (Python, `rddf guide`) and `skills/guide/scripts/scan-state.sh::scan_state()` (bash, `guide` skill) — SHALL implement the identical 4-state priority ladder and SHALL emit identical recommendations for identical project states.

#### Scenario: full priority ladder preserved

- The ladder SHALL preserve ALL existing branches: ADR<1 recovery (→ `guide-arch`), stale plan-handoff (→ `guide-arch`), missing roadmap.md (→ `guide-arch`), worktree states (→ `guide-ship`), committed-change-in-HEAD (→ `guide-ship`)
- The ladder SHALL insert: arch-handoff present + design-handoff absent + ADR ≥ 1 → `guide-design`; design-handoff present + plan-handoff absent → `guide-plan`
- The ladder SHALL reroute: no handoffs + unapproved proposals → `guide-design` (was incorrectly `guide-plan`)

#### Scenario: scanner consistency

- GIVEN any of the 7 handoff-state combinations (arch-only / arch+design / arch+design+plan / plan-only / design+plan / none-with-pending-proposals / none-without-proposals)
- WHEN both scanners evaluate the same project state
- THEN both SHALL emit the same recommendation

### Requirement: Session Schema Additive Extension

The session subsystem SHALL accept `stage_design` as a session kind without migrating existing data.

#### Scenario: schema and type updates

- `skills/_lib/schemas/sessions_schema.json` `kind` enum SHALL include `stage_design`; `goal.intent` enum SHALL include `guide-design`; schema `version` SHALL remain `const: 1` (additive extension, existing sessions.json files remain valid)
- `skills/rddf-session/scripts/rddf_session_pkg/_types.py` `_VALID_KINDS` and `_KIND_ALIAS` SHALL include `stage_design`

#### Scenario: parent chain

- `parent_kind_map` SHALL map `stage_design → stage_arch` and `stage_plan → stage_design`
- GIVEN a user skips design and starts plan directly, WHEN parent resolution finds no `stage_design` session, THEN it SHALL degrade gracefully to `None` (existing `parents[0] if parents else None` behavior)
- GIVEN a full chain arch → design → plan completes, THEN the `stage_plan` session's ancestor chain SHALL contain all 3 stages

