# install-integration Specification

## Purpose
Define how the spoke-system-prompt-injection deployment integrates with the main `install.sh` script.

## ADDED Requirements

### Requirement: spoke-init-subcommand

The install.sh script SHALL support `--spoke-init` as a subcommand to invoke the deployment script.

#### Scenario: Standalone spoke-init
- **WHEN** `install.sh --spoke-init` is invoked
- **THEN** it SHALL call `deploy.sh --tools all` (or appropriate default)
- **AND** exit with the deploy.sh exit code

#### Scenario: Spoke-init with tool list
- **WHEN** `install.sh --spoke-init --tools cursor,claude` is invoked
- **THEN** it SHALL call `deploy.sh --tools cursor,claude`

### Requirement: no-auto-cross-repo-approval

The install.sh integration SHALL explicitly configure the prohibition on automatic cross-repo approval.

#### Scenario: install.sh does not enable auto-approve
- **WHEN** `install.sh --spoke-init` completes
- **THEN** there SHALL be no configuration that enables automatic cross-repo approval
- **AND** the templates SHALL contain the explicit prohibition

### Requirement: idempotent-install

Running `install.sh --spoke-init` multiple times SHALL be idempotent.

#### Scenario: Second invocation is no-op
- **WHEN** `install.sh --spoke-init` runs twice consecutively
- **THEN** the second invocation SHALL report "Already initialized"
- **AND** not modify any files

### Requirement: install-shutdown-uninstall

The `install.sh --spoke-init` deployment SHALL be reversible via `deploy.sh --uninstall`.

#### Scenario: Uninstall via deploy.sh
- **WHEN** `deploy.sh --uninstall --tools all` runs after installation
- **THEN** it SHALL remove all injected protocol content
- **AND** restore files to pre-installation state
