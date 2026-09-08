# ci-e2e-integration Specification

## Purpose
TBD - created by archiving change add-e2e-test-plan-phase4. Update Purpose after archive.
## Requirements
### Requirement: ci-e2e-integration

The rdd-workflow repository SHALL provide continuous integration for the e2e test suite across two layers:
- (1) A-layer smoke runs on every PR/push via `.github/workflows/test.yml`,
- (2) C-layer agent simulation runs nightly 02:00 UTC via `.github/workflows/e2e-nightly.yml`.

#### Scenario: A-layer e2e smoke runs on PR and push

- **WHEN** a pull request is opened or a push to master occurs
- **THEN** `.github/workflows/test.yml` job executes `./test.sh --e2e-smoke`
- **AND** exit code 0 is required (CI gate)

#### Scenario: C-layer e2e agent runs nightly with graceful credential-missing skip

- **WHEN** the scheduled cron `0 2 * * *` triggers
- **THEN** `.github/workflows/e2e-nightly.yml` job executes `./test.sh --e2e-agent`
- **AND** if no agent CLI is available, the job continues with `continue-on-error: true` (not a CI failure)
- **AND** the workflow manually triggerable via `workflow_dispatch`

#### Scenario: README documents layered e2e strategy

- **WHEN** a developer reads `README.md` "测试基础设施" section
- **THEN** the section mentions A-layer (CI), C-layer (nightly), and external testbed (chisuhua/rdd-workflow-e2e) coverage
- **AND** links to `docs/superpowers/specs/2026-09-08-e2e-test-plan-design.md` for full design

