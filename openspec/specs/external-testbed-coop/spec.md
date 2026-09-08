# external-testbed-coop Specification

## Purpose
TBD - created by archiving change add-e2e-test-plan-phase5. Update Purpose after archive.
## Requirements
### Requirement: external-testbed-coop

The rdd-workflow repository SHALL maintain a co-op contract with `chisuhua/rdd-workflow-e2e` external testbed for complementary e2e coverage:
- (1) This repo owns single-skill prose UX + isolation contract (per `2026-09-08-e2e-test-plan-design.md` §6)
- (2) External testbed owns multi-stage full-flow integration + 36 rddf CLI smoke
- (3) Both repos share a versioned scenario JSON schema v1 and verdict JSON schema v1
- (4) Either side's full-flow failure triggers the other side's single-skill re-test to localize the fault domain

#### Scenario: scenario JSON schema v1 compatibility

- **WHEN** external testbed reads `tests/e2e/agent/scenarios/*.json` as fixtures
- **THEN** every scenario JSON contains the 5 required fields: `scenario_id`, `skill`, `input`, `golden_output`, `isolation`
- **AND** `golden_output` has at least one of: `files`, `fields`, `stdout_contains`, `history_jsonl`

#### Scenario: verdict JSON schema v1 compatibility

- **WHEN** external testbed reads `.rddf/state/.ac-verdict-*.json` mock_output
- **THEN** all 6 VERDICT_ITEM_SCHEMA fields are present per item: `ac_id`, `description`, `status`, `confidence`, `evidence`, `reasoning`
- **AND** `status ∈ {pass, fail, partial}`; `confidence ∈ [0.0, 1.0]`

#### Scenario: workflow 触发条件合规

- **WHEN** GitHub Actions workflows are evaluated by external testbed
- **THEN** `.github/workflows/e2e-nightly.yml` has `continue-on-error: true` for credential-missing skip
- **AND** `.github/workflows/test.yml` includes `--e2e-smoke` step for A-layer CI gate
- **AND** `test.sh` exposes both `--e2e-smoke` and `--e2e-agent` modes

