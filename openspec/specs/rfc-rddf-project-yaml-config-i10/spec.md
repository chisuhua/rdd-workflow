# rfc-rddf-project-yaml-config-i10 Specification

## Purpose
TBD - created by archiving change rfc-rddf-project-yaml-config-i10. Update Purpose after archive.
## Requirements
### Requirement: acceptance-1

The system SHALL `project.yaml` 设 `adr.pattern: "ADR-\\d{3}"` 后，ChipForge 的 ADR-040/041/042 可被 `scan_adr_catalog` 识别.

#### Scenario: `project.yaml` 设 `adr.pattern: "ADR-\\d{3}"` 后，ChipForge 的 A

- **WHEN** the change is applied
- **THEN** `project.yaml` 设 `adr.pattern: "ADR-\\d{3}"` 后，ChipForge 的 ADR-040/041/042 可被 `scan_adr_catalog` 识别

### Requirement: acceptance-2

The system SHALL `project.yaml` `adr.dir` 被 `discover-arch-artifacts.sh` 读取，`DISCOVERED_ADR_DIR_FOUND=true`.

#### Scenario: `project.yaml` `adr.dir` 被 `discover-arch-artifacts.sh` 读取，`

- **WHEN** the change is applied
- **THEN** `project.yaml` `adr.dir` 被 `discover-arch-artifacts.sh` 读取，`DISCOVERED_ADR_DIR_FOUND=true`

### Requirement: acceptance-3

The system SHALL `git.openspec_tracked: false` 时 guide-ship 强制轻量模式，archive 无 git merge/commit 错误.

#### Scenario: `git.openspec_tracked: false` 时 guide-ship 强制轻量模式，archive 无 

- **WHEN** the change is applied
- **THEN** `git.openspec_tracked: false` 时 guide-ship 强制轻量模式，archive 无 git merge/commit 错误

### Requirement: acceptance-4

The system SHALL `verification.provider: hook` 时 `rddf rdd-verify` 调用外部 hook，verdict 写入缓存.

#### Scenario: `verification.provider: hook` 时 `rddf rdd-verify` 调用外部 hook，

- **WHEN** the change is applied
- **THEN** `verification.provider: hook` 时 `rddf rdd-verify` 调用外部 hook，verdict 写入缓存

### Requirement: acceptance-5

The system SHALL 无 `project.yaml` 时所有现有行为不变（零回归）.

#### Scenario: 无 `project.yaml` 时所有现有行为不变（零回归）

- **WHEN** the change is applied
- **THEN** 无 `project.yaml` 时所有现有行为不变（零回归）

### Requirement: acceptance-6

The system SHALL `test_priority_project_yaml_over_loop_yaml` 单测通过（project.yaml > loop.yaml > env）.

#### Scenario: `test_priority_project_yaml_over_loop_yaml` 单测通过（project.yam

- **WHEN** the change is applied
- **THEN** `test_priority_project_yaml_over_loop_yaml` 单测通过（project.yaml > loop.yaml > env）

### Requirement: acceptance-7

The system SHALL `test_three_digit_adr_pattern` 单测通过.

#### Scenario: `test_three_digit_adr_pattern` 单测通过

- **WHEN** the change is applied
- **THEN** `test_three_digit_adr_pattern` 单测通过

### Requirement: acceptance-8

The system SHALL `tests/integration/test_guide_ship_execution_mode.bats` 新增 openspec_tracked=false 场景全绿.

#### Scenario: `tests/integration/test_guide_ship_execution_mode.bats` 新增 o

- **WHEN** the change is applied
- **THEN** `tests/integration/test_guide_ship_execution_mode.bats` 新增 openspec_tracked=false 场景全绿

### Requirement: acceptance-9

The system SHALL `tests/integration/test_rdd_verifier.bats` 新增 provider=hook 场景全绿.

#### Scenario: `tests/integration/test_rdd_verifier.bats` 新增 provider=hook 

- **WHEN** the change is applied
- **THEN** `tests/integration/test_rdd_verifier.bats` 新增 provider=hook 场景全绿

### Requirement: acceptance-10

The system SHALL `./test.sh --full --regression` 全绿后才允许 archive.

#### Scenario: `./test.sh --full --regression` 全绿后才允许 archive

- **WHEN** the change is applied
- **THEN** `./test.sh --full --regression` 全绿后才允许 archive

### Requirement: acceptance-11

The system SHALL 新建 ADR（如 `ADR-0xxx-project-level-config`）记录本次决策.

#### Scenario: 新建 ADR（如 `ADR-0xxx-project-level-config`）记录本次决策

- **WHEN** the change is applied
- **THEN** 新建 ADR（如 `ADR-0xxx-project-level-config`）记录本次决策

### Requirement: acceptance-12

The system SHALL 引用相关 ADR（配置优先级、AC 验证、ship 执行模式）.

#### Scenario: 引用相关 ADR（配置优先级、AC 验证、ship 执行模式）

- **WHEN** the change is applied
- **THEN** 引用相关 ADR（配置优先级、AC 验证、ship 执行模式）

### Requirement: acceptance-13

The system SHALL M1 单独立 PR 提交 + 合并，merge 顺序测试通过后再启 M2/M3/M4.

#### Scenario: M1 单独立 PR 提交 + 合并，merge 顺序测试通过后再启 M2/M3/M4

- **WHEN** the change is applied
- **THEN** M1 单独立 PR 提交 + 合并，merge 顺序测试通过后再启 M2/M3/M4

### Requirement: acceptance-14

The system SHALL M2/M3/M4 可并行，但合入前需 M1 已合入 master.

#### Scenario: M2/M3/M4 可并行，但合入前需 M1 已合入 master

- **WHEN** the change is applied
- **THEN** M2/M3/M4 可并行，但合入前需 M1 已合入 master

### Requirement: acceptance-15

The system SHALL M5 在所有里程碑合入后合并.

#### Scenario: M5 在所有里程碑合入后合并

- **WHEN** the change is applied
- **THEN** M5 在所有里程碑合入后合并

