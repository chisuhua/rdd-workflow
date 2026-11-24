# add-skills-lib-api-doc Specification

## Purpose
Define the repository-level contract for the `skills/_lib/` documentation surface: a module catalog that distinguishes the real implementation layer from the shim layer, a helper entry-point guide bound to the project-root contract, and a guard that keeps both in step with the code.

## Requirements

### Requirement: README MUST document the two-layer module layout

`skills/_lib/README.md` MUST carry an H3 section titled `Overview` that distinguishes the real implementation layer (the repository-root `_lib/`) from the shim layer (`skills/_lib/`), and MUST state that the shim layer widens `__path__` rather than duplicating modules.

#### Scenario: The layout section distinguishes the two layers

- **WHEN** `skills/_lib/README.md` is searched for the H3 heading `Overview`
- **THEN** the section MUST name both the real implementation layer and the shim layer
- **AND** it MUST state that the shim layer widens `__path__` instead of copying modules

### Requirement: README MUST catalog the modules of both layers

`skills/_lib/README.md` MUST carry a section titled `Module Catalog` that lists the real implementation layer's modules and subpackages and the shim layer's forwarding modules. The catalog MUST cover every subpackage of the real implementation layer; a subpackage missing from the catalog makes the catalog a partial truth that reads as complete.

#### Scenario: The catalog covers every implementation subpackage

- **WHEN** the subpackage directories of the real implementation layer are enumerated on disk
- **THEN** every one of them MUST appear in the catalog section of `skills/_lib/README.md`

### Requirement: README MUST bind the helper guide to the project-root contract

`skills/_lib/README.md` MUST carry a section titled `Helper Entry Points` that names the contract file which governs project-root resolution, and MUST distinguish the canonical copy from the compatibility pointer. It MUST also carry a section titled `ADR References` whose every ADR identifier resolves to a file that exists on disk.

#### Scenario: The helper section names the canonical contract file

- **WHEN** `skills/_lib/README.md` is searched for the contract file name
- **THEN** the section MUST name the canonical contract file and MUST identify the compatibility pointer as such

#### Scenario: Every referenced ADR resolves on disk

- **WHEN** the ADR identifiers listed in `skills/_lib/README.md` are resolved against `docs/adr/`
- **THEN** every one of them MUST resolve to an existing file

### Requirement: README MUST give a continuous onboarding procedure

`skills/_lib/README.md` MUST carry a section titled `Onboarding Guide` whose steps are numbered consecutively, and MUST cover where the logic belongs, the per-layer conventions, the shim step, the contract-test step and the documentation step.

#### Scenario: The onboarding steps are numbered consecutively

- **WHEN** the numbered steps of the onboarding section are extracted
- **THEN** their numbers MUST form a consecutive sequence with no gap

### Requirement: README MUST state how cross-layer consistency is enforced

`skills/_lib/README.md` MUST carry a section titled `Cross-Layer Consistency` that names the contract test files which enforce parity between the bash and the Python helper layers, and MUST state that a deviation requires changing the contract and recording a decision.

#### Scenario: The consistency section names the enforcing tests

- **WHEN** the cross-layer consistency section is read
- **THEN** it MUST name the contract test files that enforce bash/Python parity

### Requirement: INDEX MUST provide a one-page quick reference

`skills/_lib/INDEX.md` MUST provide a quick reference grouped by use case, where each row names the helper, how it is imported or called, and what it is for. It MUST stay a reference sheet rather than growing into a manual.

#### Scenario: The quick reference is grouped by use case

- **WHEN** `skills/_lib/INDEX.md` is read
- **THEN** its rows MUST be grouped under use-case headings
- **AND** each row MUST name the helper, the import path and the purpose

