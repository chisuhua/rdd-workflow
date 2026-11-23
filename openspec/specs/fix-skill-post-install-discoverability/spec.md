# fix-skill-post-install-discoverability Specification

## Purpose
Make the tool discoverable right after installation: a skill's first layer SHALL stand
on its own, the installer SHALL ship only the documentation those skills reference, and
`rddf setup ai-context` SHALL be able to drop the Layer 0 usage block into the AI
configuration files a project already uses.
## Requirements
### Requirement: skill-layer-1-does-not-reference-external-docs

A skill's first layer SHALL NOT point at files outside the package — it has to stand on
its own for an agent that only read that layer.

#### Scenario: no skill references a path outside the package

- **WHEN** the skill documents are searched for references to `../docs/` or `../../docs/`
- **THEN** no skill SHALL contain such a reference

#### Scenario: the roadmap skill's first layer is self-contained

- **WHEN** the roadmap skill's documentation is read
- **THEN** it SHALL NOT reference an external docs/ path

#### Scenario: the rdd-hub-bootstrap skill's first layer is self-contained

- **WHEN** the rdd-hub-bootstrap skill's documentation is read
- **THEN** it SHALL NOT reference an external docs/ path

### Requirement: install-with-docs-copies-only-the-referenced-subset

`bash install.sh --with-docs` SHALL copy only the documentation that the installed skills
actually reference, into the tool's own subdirectory — never the whole docs tree, and
never into the project root.

#### Scenario: the referenced subset is copied

- **WHEN** `bash install.sh --with-docs` runs
- **THEN** the referenced documents SHALL be copied

#### Scenario: the whole docs tree is not copied

- **WHEN** `bash install.sh --with-docs` runs
- **THEN** it SHALL NOT copy the entire docs/ tree

#### Scenario: the documents land in the tool subdirectory

- **WHEN** `bash install.sh --with-docs` runs
- **THEN** the copied documents SHALL land in the tool's subdirectory
- **AND** they SHALL NOT land in the project root

### Requirement: install-default-copies-no-documentation

A default `bash install.sh` run SHALL NOT copy documentation — the documentation is
copied only when `--with-docs` is passed.

#### Scenario: a default install copies no documentation

- **WHEN** `bash install.sh` runs without `--with-docs`
- **THEN** it SHALL NOT create a docs/ directory

### Requirement: rddf-setup-ai-context-is-registered

`rddf setup ai-context` SHALL be a registered subcommand, listed in the setup
command's own help.

#### Scenario: the setup help lists the ai-context subcommand

- **WHEN** `rddf setup --help` is read
- **THEN** it SHALL list the `ai-context` subcommand

### Requirement: setup-ai-context-creates-the-layer-0-block

In a project without AI configuration files, `rddf setup ai-context` SHALL create an
`AGENTS.md` holding the Layer 0 block. The block SHALL be at most thirty lines and SHALL
carry its five structural segments.

#### Scenario: an empty project gets an AGENTS.md with the block

- **WHEN** `rddf setup ai-context` runs in an empty project
- **THEN** an `AGENTS.md` SHALL be created
- **AND** it SHALL contain the Layer 0 block

#### Scenario: the block stays within thirty lines

- **WHEN** the deployed Layer 0 block is measured
- **THEN** it SHALL be at most thirty lines

#### Scenario: the block carries its five segments

- **WHEN** the deployed Layer 0 block is read
- **THEN** all five structural segments SHALL be present

### Requirement: setup-ai-context-appends-to-existing-config-files

When AI configuration files already exist, `rddf setup ai-context` SHALL append the
Layer 0 block to them — to every one of them when several are present.

#### Scenario: an existing .cursorrules receives the block

- **WHEN** `rddf setup ai-context` runs in a project that already has a `.cursorrules`
- **THEN** the Layer 0 block SHALL be appended to it

#### Scenario: every present configuration file receives the block

- **WHEN** `rddf setup ai-context` runs in a project with several AI configuration files
- **THEN** each of them SHALL receive the Layer 0 block

### Requirement: setup-ai-context-is-idempotent

Running `rddf setup ai-context` twice SHALL NOT inject the block twice.

#### Scenario: a second run does not duplicate the block

- **WHEN** `rddf setup ai-context` runs twice in the same project
- **THEN** the Layer 0 sentinel SHALL appear only once

### Requirement: setup-ai-context-dry-run-writes-nothing

`rddf setup ai-context --dry-run` SHALL preview the deployment without writing anything.

#### Scenario: a dry run writes no file

- **WHEN** `rddf setup ai-context --dry-run` runs
- **THEN** no file SHALL be written

### Requirement: setup-ai-context-uninstall-removes-the-block

`rddf setup ai-context --uninstall` SHALL remove the Layer 0 block from every AI
configuration file and leave the rest of each file intact.

#### Scenario: uninstall removes the sentinel block

- **WHEN** `rddf setup ai-context --uninstall` runs
- **THEN** the Layer 0 sentinel block SHALL be removed from the configuration files

### Requirement: layer-0-block-matches-the-template

The deployed Layer 0 block SHALL be byte-identical to the single-source template
`_lib/templates/layer0_rdd_workflow_usage.md`, so that the two cannot drift apart.

#### Scenario: the deployed block matches the template

- **WHEN** the deployed Layer 0 block is compared with the template
- **THEN** they SHALL be identical

### Requirement: rddf-init-suggests-setup-ai-context

A successful `rddf init` SHALL point the user at the Layer 0 deployment step.

#### Scenario: the init output includes the setup hint

- **WHEN** `rddf init` succeeds
- **THEN** its output SHALL include a hint pointing at `rddf setup ai-context`

### Requirement: layer-0-and-hub-sentinels-coexist-deterministically

Deploying, re-running and removing the Layer 0 block SHALL NOT disturb the Hub
sentinel block that may already live in the same configuration file.

#### Scenario: deploying Layer 0 leaves the Hub sentinel in place

- **WHEN** the Layer 0 block is deployed into a configuration file that already carries
  a Hub sentinel block
- **THEN** the Hub sentinel block SHALL still be present
- **AND** its position SHALL NOT have changed

#### Scenario: a repeated setup does not move the Hub block

- **WHEN** the Layer 0 block is deployed again into the same configuration file
- **THEN** the Hub sentinel block SHALL still be in its original position

#### Scenario: uninstall removes only the Layer 0 block

- **WHEN** the Layer 0 block is uninstalled from a configuration file that also carries
  a Hub sentinel block
- **THEN** the Layer 0 block SHALL be removed
- **AND** the Hub sentinel block SHALL be kept

### Requirement: ai-context-doctor-category-reports-the-deployment-state

The `ai-context-bootstrap` doctor category SHALL distinguish a project with no AI
configuration files, a project whose configuration carries the block, and a project
whose configuration files exist but carry no block.

#### Scenario: a project without AI configuration files is warned about

- **WHEN** the ai-context-bootstrap category runs in a project without AI configuration files
- **THEN** it SHALL report a warning

#### Scenario: a project whose configuration carries the block is healthy

- **WHEN** the ai-context-bootstrap category runs in a project whose configuration file
  carries the Layer 0 block
- **THEN** it SHALL report the project as healthy

#### Scenario: configuration files without the block are warned about

- **WHEN** the ai-context-bootstrap category runs in a project whose configuration files
  exist but carry no Layer 0 block
- **THEN** it SHALL report a warning
