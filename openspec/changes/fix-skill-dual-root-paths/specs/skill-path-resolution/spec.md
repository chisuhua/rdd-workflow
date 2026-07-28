# skill-path-resolution

## ADDED Requirements

### Requirement: Skill directory resolution independent of project root

The system SHALL provide a mechanism to resolve each skill's installation directory (`SKILL_DIR`) independently of the project root (`PROJECT_ROOT`), supporting both project-local installation (`.opencode/skills/`) and global installation (`~/.agents/skills/`).

The resolution SHALL follow this priority order:
1. `$PROJECT_ROOT/.opencode/skills/<skill-name>` — project-local installation
2. `$HOME/.agents/skills/<skill-name>` — global installation
3. `$RDD_WORKFLOW_SRC/skills/<skill-name>` — development source checkout

#### Scenario: Global installation in a different project

- **GIVEN** rdd-workflow is installed globally via `install.sh --global`
- **AND** the user is working in a project other than rdd-workflow (e.g., PTX-EMU)
- **WHEN** any skill's SKILL.md code block executes `resolve_rdd_skill_dir <name>`
- **THEN** the function SHALL return `$HOME/.agents/skills/<name>`

#### Scenario: Project-local installation

- **GIVEN** rdd-workflow skills are copied to `$PROJECT_ROOT/.opencode/skills/`
- **WHEN** any skill's SKILL.md code block executes `resolve_rdd_skill_dir <name>`
- **THEN** the function SHALL return `$PROJECT_ROOT/.opencode/skills/<name>`
- **AND** the global installation SHALL NOT be used

#### Scenario: Skill scripts reference _lib shared library

- **GIVEN** a shell script needs to source a shared library from `_lib/`
- **WHEN** the script executes `resolve_rdd_lib_dir`
- **THEN** the function SHALL return the `_lib` directory path following the same resolution order as skills
- **AND** `_lib` SHALL be symlinked to `~/.agents/skills/_lib` during global installation

### Requirement: install.sh shall symlink _lib during global installation

The `install.sh --global` command SHALL create a symlink for `skills/_lib` at `~/.agents/skills/_lib`, in addition to the existing per-skill symlinks.

#### Scenario: Fresh global installation

- **GIVEN** a user runs `install.sh --global` for the first time
- **WHEN** the installation completes
- **THEN** `~/.agents/skills/_lib` SHALL exist as a symlink to the rdd-workflow `skills/_lib` directory
- **AND** all 13 sub-skill symlinks SHALL also exist

#### Scenario: Existing global installation upgrade

- **GIVEN** rdd-workflow was previously installed globally without `_lib` symlink
- **WHEN** the user re-runs `install.sh --global`
- **THEN** the `_lib` symlink SHALL be created
- **AND** existing skill symlinks SHALL be preserved
