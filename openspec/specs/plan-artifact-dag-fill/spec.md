# plan-artifact-dag-fill Specification

## Purpose
TBD - created by archiving change refine-plan-openspec-integration. Update Purpose after archive.
## Requirements
### Requirement: 传递闭包计算必需 artifact 集合

The system SHALL compute the required artifact set as the transitive closure of `applyRequires` over each artifact's `requires` edges from `openspec status --change <name> --json`. Checking only the root `applyRequires` entries is forbidden.

#### Scenario: 闭包包含间接依赖

- GIVEN `applyRequires: ["tasks"]` with `tasks.requires=["specs","design"]` and `specs.requires=["proposal"]`, `design.requires=["proposal"]`
- WHEN the required set is computed
- THEN it contains `tasks`, `specs`, `design`, and `proposal`

### Requirement: DAG 驱动的 fill 执行

The fill phase SHALL loop: query `openspec status --change <name> --json`, select ready (not blocked) incomplete artifacts in the returned topological order, obtain content guidance via `openspec instructions <artifact> --change <name> --json`, write the artifact, and re-query status. Artifacts already done MUST be skipped. Hardcoded artifact ordering SHALL only be used when the CLI does not expose the DAG (degradation path).

#### Scenario: 拓扑序补全

- GIVEN a change with only `proposal.md` done
- WHEN the DAG-driven fill runs
- THEN `specs` and `design` are filled before `tasks` (their dependent), and `proposal` is skipped

#### Scenario: blocked 工件等待依赖

- GIVEN `tasks` is blocked with `missingDeps: ["design"]`
- WHEN the fill loop runs
- THEN `tasks` is not attempted until `design` is written and a subsequent status query reports it ready

### Requirement: propose instructions 循环实装

The propose phase SHALL create all artifacts via the `openspec instructions <artifact> --change <name> --json` loop. The HALF-IMPLEMENTED pseudo-code block in `skills/propose/SKILL.md` MUST be removed.

#### Scenario: 伪代码清零

- GIVEN the propose skill after this change
- WHEN its Phase 4 executes
- THEN every artifact is produced by a real `instructions --json` call, and no pseudo-code marker remains in the skill file

