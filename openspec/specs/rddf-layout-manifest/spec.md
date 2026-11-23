# rddf-layout-manifest Specification

## Purpose
Give the `.rddf/` layout a machine-readable manifest — one place that says which paths
exist, who reads and writes them, and when they are required — so that the layout
doctor and the tooling around it share a single source of truth.
## Requirements
### Requirement: layout-manifest-entries-are-well-formed

The layout manifest SHALL list every managed `.rddf/` path with a closed set of fields —
`path`, `kind`, `read_by`, `write_by`, `required_when`, `transient`, `class` and
`severity` — whose values come from closed domains, and the listed paths SHALL be unique
and relative to `.rddf/`.

#### Scenario: every entry carries all the contract fields

- **WHEN** the layout manifest is inspected
- **THEN** every entry SHALL carry all eight contract fields
- **AND** each field's value SHALL come from its closed domain

#### Scenario: the listed paths are unique and relative to .rddf/

- **WHEN** the layout manifest is inspected
- **THEN** no path SHALL be listed twice
- **AND** every listed path SHALL be relative to the `.rddf/` directory

#### Scenario: the reader and writer facts match the real owners

- **WHEN** the manifest's `read_by` and `write_by` are compared with who actually reads
  and writes those paths
- **THEN** every entry the rdd does not write SHALL name exactly the owner that writes it
- **AND** the state directory SHALL list both rdd and the agent as writers
- **AND** the agent SHALL NOT be listed as a reader of rdd's state internals

### Requirement: layout-json-output-carries-the-contract

`rddf layout --json` SHALL emit the manifest as a JSON payload whose entries carry the
same contract fields.

#### Scenario: the JSON payload has the expected shape

- **WHEN** `rddf layout --json` runs
- **THEN** the payload SHALL be valid JSON
- **AND** every entry in it SHALL carry the contract fields

### Requirement: layout-json-output-is-deterministic

Two consecutive runs of `rddf layout --json` on the same tree SHALL produce the same
output: the entries are sorted by path and no timestamp is included.

#### Scenario: the entries are sorted by path

- **WHEN** the manifest is rendered
- **THEN** its entries SHALL be sorted by path

#### Scenario: the payload carries no timestamp

- **WHEN** `rddf layout --json` runs
- **THEN** the payload SHALL NOT contain a timestamp field

### Requirement: layout-doctor-is-clean-on-this-repository

The layout doctor category SHALL report no finding on this repository.

#### Scenario: this repository yields zero findings

- **WHEN** the layout doctor category runs on this repository
- **THEN** it SHALL report no finding

### Requirement: layout-doctor-detects-layout-deviations

The layout doctor SHALL distinguish the kinds of deviation it can see.

#### Scenario: a missing always-required path yields a warning

- **WHEN** a directory that the manifest marks as always required is removed
- **THEN** the layout doctor SHALL report a warning

#### Scenario: an unregistered top-level entry yields an info

- **WHEN** an unregistered directory is created under `.rddf/`
- **THEN** the layout doctor SHALL report an info

#### Scenario: a class that disagrees with .gitignore yields a warning

- **WHEN** an entry's class disagrees with the repository's ignore rules
- **THEN** the layout doctor SHALL report a warning

### Requirement: layout-doctor-never-emits-critical

The layout doctor category SHALL NOT report a critical finding.

#### Scenario: the category never escalates to critical

- **WHEN** the layout doctor category reports a deviation
- **THEN** the finding's severity SHALL NOT be critical

### Requirement: layout-doctor-is-silent-without-rdd-state

When the project has no `.rddf/` directory, the layout doctor category SHALL report no
finding — the project simply does not use rdd.

#### Scenario: a project without .rddf yields no findings

- **WHEN** the layout doctor category runs on a project that has no `.rddf/` directory
- **THEN** it SHALL report no finding

### Requirement: layout-manifest-covers-the-real-defaults

The manifest SHALL cover every path the toolchain's own defaults and module constants
use, and each entry's class SHALL agree with what the ignore rules actually say.

#### Scenario: the defaults are covered by the manifest

- **WHEN** the toolchain's default paths are compared with the manifest
- **THEN** every default path SHALL be covered by a manifest entry

#### Scenario: each entry's class matches the ignore reality

- **WHEN** each manifest entry's class is compared with the repository's ignore rules
- **THEN** they SHALL agree

### Requirement: layout-architecture-doc-exists-and-is-indexed

The layout architecture document SHALL exist and SHALL be listed in the architecture
document map.

#### Scenario: the architecture document exists and is indexed

- **WHEN** the architecture document map is read
- **THEN** it SHALL list the layout architecture document
- **AND** that document SHALL exist

### Requirement: state-and-events-doc-uses-v4-handoff-names

The state-and-events document's handoff table and diagram SHALL use the v4 handoff file
names.

#### Scenario: the handoff table uses the v4 names

- **WHEN** the state-and-events document's handoff table is read
- **THEN** it SHALL name the v4 handoff files

### Requirement: adr-0026-points-at-the-machine-readable-form

ADR-0026 SHALL point at the machine-readable layout manifest.

#### Scenario: the ADR points at the manifest

- **WHEN** ADR-0026 is read
- **THEN** it SHALL reference the machine-readable layout form

### Requirement: rdd-doctor-skill-doc-carries-no-hardcoded-category-count

The rdd-doctor skill's description SHALL NOT state a fixed number of categories, and its
usage line's category list SHALL match the registered checkers.

#### Scenario: the skill description carries no category count

- **WHEN** the rdd-doctor skill documentation is read
- **THEN** its description SHALL NOT state how many categories there are

#### Scenario: the usage line lists every registered category

- **WHEN** the rdd-doctor skill's usage line is compared with the registered checkers
- **THEN** every registered category SHALL appear in the usage line
- **AND** the usage line SHALL NOT list a category that is not registered
