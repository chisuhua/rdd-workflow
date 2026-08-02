# openspec-version-degradation Specification

## Purpose
TBD - created by archiving change refine-plan-openspec-integration. Update Purpose after archive.
## Requirements
### Requirement: CLI 版本检测与降级

The system SHALL parse `openspec --version` at guide-plan intake. When the version is below 1.7.0, the system SHALL emit an upgrade warning and set a degradation flag causing DAG-dependent behavior (fill ordering, required-set computation) to fall back to the pre-existing hardcoded path. Degradation MUST NOT hard-fail the workflow.

#### Scenario: 旧版本回退

- GIVEN openspec CLI 1.4.1
- WHEN guide-plan intake runs
- THEN an upgrade warning is shown, `OPENSPEC_DAG_AVAILABLE=false` is set, and fill uses the hardcoded design→tasks order (behavior identical to before this change)

#### Scenario: 新版本启用 DAG

- GIVEN openspec CLI 1.7.0 or newer
- WHEN guide-plan intake runs
- THEN the DAG path is enabled without warnings

