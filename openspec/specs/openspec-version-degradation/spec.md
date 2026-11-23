# openspec-version-degradation Specification

## Purpose
TBD - created by archiving change refine-plan-openspec-integration. Update Purpose after archive.
## Requirements
### Requirement: CLI 版本检测与降级

The system SHALL parse `openspec --version` at guide-plan intake. When the version is below 1.7.0, the system SHALL emit an upgrade warning and set a degradation flag causing DAG-dependent behavior (fill ordering, required-set computation) to fall back to the pre-existing hardcoded path. Degradation MUST NOT hard-fail the workflow.
<!-- v4-residue:allow=history -->
> **已退役（2026-11-21）**：本 Requirement 描述的 openspec CLI 版本检测与降级（低于 1.7.0 设 `OPENSPEC_DAG_AVAILABLE=false` 并回退到硬编码 design→tasks 顺序）在 v4 阶段合并中已删除 —— `OPENSPEC_DAG_AVAILABLE` 在 `_lib/` 与 `skills/` 全仓 0 命中，承载它的 v3 plan intake 脚本（`plan_intake.sh`）在仓库中亦不存在。原文保留以备查。

#### Scenario: 旧版本回退

- GIVEN openspec CLI 1.4.1
- WHEN guide-plan intake runs
<!-- v4-residue:allow=history -->
- THEN an upgrade warning is shown, `OPENSPEC_DAG_AVAILABLE=false` is set, and fill uses the hardcoded design→tasks order (behavior identical to before this change)

#### Scenario: 新版本启用 DAG

- GIVEN openspec CLI 1.7.0 or newer
- WHEN guide-plan intake runs
<!-- v4-residue:allow=history -->
- THEN the DAG path is enabled without warnings

