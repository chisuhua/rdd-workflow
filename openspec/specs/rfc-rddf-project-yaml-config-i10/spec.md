# rfc-rddf-project-yaml-config-i10 Specification

## Purpose
Let a project configure its own ADR naming and directory, its openspec tracking mode and
its verification provider through `project.yaml`, instead of hard-coding those choices
in the tool.
## Requirements
### Requirement: adr-catalog-honours-a-project-configured-pattern

The ADR catalog SHALL honour the `adr.pattern` configured in `project.yaml`, so that a
project whose ADRs use a three-digit number has them recognised; the default four-digit
behaviour SHALL be preserved when no pattern is configured.

#### Scenario: a three-digit pattern is recognised

- **WHEN** `project.yaml` configures `adr.pattern` for three-digit ADR numbers
- **THEN** `scan_adr_catalog` SHALL recognise the ADRs matching that pattern

#### Scenario: the default four-digit behaviour is preserved

- **WHEN** no ADR pattern is configured
- **THEN** `scan_adr_catalog` SHALL keep its default four-digit behaviour

### Requirement: arch-discovery-reads-the-configured-adr-directory

The architecture discovery SHALL read the ADR directory configured in `project.yaml` and
report that it found one.

#### Scenario: the configured ADR directory is discovered

- **WHEN** `project.yaml` configures `adr.dir`
- **THEN** the discovery SHALL report that the ADR directory was found
- **AND** it SHALL use the configured directory

#### Scenario: without a configuration the discovery finds nothing

- **WHEN** no `project.yaml` is present, or it configures no `adr.dir`
- **THEN** the discovery SHALL report that no ADR directory was found
- **AND** the caller SHALL fall back to its own default

### Requirement: verifier-can-delegate-to-an-external-hook

With `verification.provider: hook` configured, `rddf rdd-verify` SHALL call the external
hook and write the verdict into the cache; the hook's exit code SHALL map to the
verifier's result, and a hook outside the allowed directory SHALL be rejected.

#### Scenario: the hook's result is written into the verdict cache

- **WHEN** `rddf rdd-verify` runs with `verification.provider: hook`
- **THEN** the external hook SHALL be invoked
- **AND** its verdict SHALL be written into the verdict cache
- **AND** the hook's exit code SHALL determine the verifier's result

#### Scenario: a hook outside the allowed directory is rejected

- **WHEN** the configured hook lives outside the allowed directory
- **THEN** the verifier SHALL reject it
