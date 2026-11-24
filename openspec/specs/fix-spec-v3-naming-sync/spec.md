# fix-spec-v3-naming-sync Specification

## Purpose
Define the contract that keeps the live role-model capability spec in step with the skill frontmatter it describes, and that makes ownership drift detectable by an assertion instead of by manual review.

## Requirements

### Requirement: The live role-model spec MUST state rdd-arch ownership as the implementation does

The live capability spec that describes the role model MUST state rdd-arch's owned paths exactly as the arch skill's frontmatter declares them, and MUST NOT attribute roadmap artifacts to that skill.

The statement is a positive one: it names what the skill owns. The negative half — that roadmap artifacts are not owned — is asserted by a guard rather than written into the prose, so that the spec stays a description of the present instead of a discussion of an absent.

#### Scenario: The ownership statement lists the implemented owned paths

- **WHEN** the ownership assertion of the live role-model spec is read
- **THEN** it MUST name every path that the arch skill's frontmatter lists as owned
- **AND** it MUST NOT name any roadmap artifact

### Requirement: Ownership drift MUST be detectable by an assertion

The doc-drift contract test suite MUST carry a guard over an explicit list of live capability specs, and that guard MUST compare the ownership statement against the skill frontmatter it mirrors.

A guard that only checked for a forbidden word would miss a dropped owned path; the comparison MUST therefore be bidirectional — a forbidden attribution AND a positive item-by-item match.

#### Scenario: Restoring a forbidden attribution turns the guard red

- **WHEN** a roadmap attribution is reintroduced into the ownership statement of a live role-model spec
- **THEN** the guard MUST fail and MUST report the offending file and line

#### Scenario: The guard does not constrain historical snapshots

- **WHEN** a historical capability snapshot retains terminology that was correct when it was written
- **THEN** the guard MUST NOT fail

### Requirement: The guard MUST NOT overlap the exemption-marking guard

The ownership guard MUST NOT assert the absence of retired terminology: renamed-history annotations carrying their exemption marker are legitimate records and are governed by the residue guard, which checks exemption markers rather than ownership.

#### Scenario: Exempted rename history stays untouched

- **WHEN** a live role-model spec retains a renamed-history annotation with its exemption marker
- **THEN** the ownership guard MUST pass
- **AND** the annotation and its marker MUST remain unchanged

