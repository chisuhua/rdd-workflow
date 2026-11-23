# sync-package-skills-to-disk Specification

## Purpose
Install the on-disk sub-skills and the shared helper library into the target skill
directory — `~/.agents/skills/` for a global install, `.opencode/skills/rdd-workflow/`
for a project install — so a consuming project discovers the same skills the package
ships and the Python/bash helper layer stays importable.
## Requirements
### Requirement: sync-package-skills-to-disk

`install.sh` SHALL install the on-disk sub-skills into the target skill directory.
A global install SHALL create one symlink per sub-skill under `~/.agents/skills/`, and
every such symlink SHALL resolve to a directory that contains a `SKILL.md`. A project
install SHALL copy the `skills/` tree and the `_lib/` helper layer into
`<target>/.opencode/skills/rdd-workflow/`.

#### Scenario: global install creates one working symlink per sub-skill

- **WHEN** `bash install.sh --global` runs
- **THEN** `~/.agents/skills/<name>` SHALL be a symlink for each installed sub-skill
- **AND** every such symlink SHALL resolve to a directory containing a `SKILL.md`

#### Scenario: project install copies the skills tree and the helper layer

- **WHEN** `bash install.sh <target>` runs
- **THEN** `<target>/.opencode/skills/rdd-workflow/skills/` SHALL contain the sub-skills
- **AND** the `_lib/` helper layer SHALL be copied alongside it
- **AND** the `__pycache__` / `plugins` / `schedulers` directories SHALL be excluded

