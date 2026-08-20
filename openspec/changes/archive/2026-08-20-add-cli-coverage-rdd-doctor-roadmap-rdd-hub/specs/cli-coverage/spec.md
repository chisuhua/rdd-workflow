# CLI Coverage — `rddf` 子命令暴露

## Purpose
Add CLI thin-wrappers for the `rdd-doctor`, `roadmap`, and `rdd-hub-bootstrap`
skills so their functionality is reachable via `rddf <subcommand>`.

## ADDED Requirements

### Requirement: `rddf doctor` 子命令

`rddf` CLI SHALL 暴露 `doctor` 子命令，转发到 `rdd-doctor` skill 的 `doctor.sh` 脚本，并透传 exit code。

#### Scenario: `rddf doctor --help` 显示 8 个 category
- **WHEN** 用户运行 `rddf doctor --help`
- **THEN** exit code 为 0
- **AND** stdout 包含 `--category {state,plan-tdd,roadmap-meta,proposal-table,tasks-checkbox,migration-residue,orphan-gates,roadmap-refs}`

#### Scenario: `rddf doctor --version` 输出版本
- **WHEN** 用户运行 `rddf doctor --version`
- **THEN** exit code 为 0
- **AND** stdout 包含 `rdd-doctor`

#### Scenario: exit code 透传
- **WHEN** 用户运行 `rddf doctor --category bogus-category`（底层脚本会失败）
- **THEN** exit code 为底层脚本退出码（2 = bad input）
- **AND** 不是恒为 0

### Requirement: `rddf roadmap` 子命令

`rddf` CLI SHALL 暴露 `roadmap` 子命令，转发到 `roadmap` skill 的 migrate / validate-fragments 脚本，并透传 exit code。

#### Scenario: `rddf roadmap --help` 显示 subcommand 列表
- **WHEN** 用户运行 `rddf roadmap --help`
- **THEN** exit code 为 0
- **AND** stdout 包含 `migrate` 和 `validate-fragments`

#### Scenario: `rddf roadmap migrate --dry-run` 透传
- **WHEN** 用户运行 `rddf roadmap migrate --dry-run`
- **THEN** exit code 为底层 `roadmap_migrate.sh --dry-run` 的退出码

### Requirement: `rddf rdd-hub-bootstrap` 子命令

`rddf` CLI SHALL 暴露 `rdd-hub-bootstrap` 子命令，转发到 `rdd-hub-bootstrap` skill 的脚本，并透传 exit code。

#### Scenario: `rddf rdd-hub-bootstrap --help` 显示 subcommand 列表
- **WHEN** 用户运行 `rddf rdd-hub-bootstrap --help`
- **THEN** exit code 为 0
- **AND** stdout 包含 `init` 等 bootstrap subcommand

### Requirement: `rddf --help` 路由表更新

`rddf --help` SHALL 列出 3 个新子命令，且不删除任何现有子命令。

#### Scenario: 3 个新子命令出现在 `rddf --help`
- **WHEN** 用户运行 `rddf --help`
- **THEN** stdout 包含 `doctor`、`roadmap`、`rdd-hub-bootstrap` 三行
- **AND** 原有 19 个 subcommand 行保持不变

### Requirement: Skill 内部不动

本 change MUST NOT 修改 `rdd-doctor` / `roadmap` / `rdd-hub-bootstrap` skill 的内部（scripts、Python、SKILL.md frontmatter）。

#### Scenario: skill 文件未修改
- **WHEN** 检查 git diff
- **THEN** `skills/rdd-doctor/`、`skills/roadmap/`、`skills/rdd-hub-bootstrap/` 下无修改
- **AND** 新增文件仅在 `_lib/cli/` 与 `tests/`