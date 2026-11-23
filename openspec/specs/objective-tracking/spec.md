# objective-tracking Specification

## Purpose
Give the roadmap a first-class objective track: objective files with a validated
frontmatter and section layout, CLI commands to list, show and revise them, doctor
checks that keep them honest, and a sentinel block that publishes them into AGENTS.md.
## Requirements
### Requirement: objective-files-declare-nine-frontmatter-fields

An objective file's frontmatter SHALL declare exactly nine fields, including
`review_by` and `supersedes`.

#### Scenario: the required frontmatter has nine fields

- **WHEN** the objective module's required-frontmatter list is inspected
- **THEN** it SHALL contain exactly nine field names
- **AND** it SHALL include `review_by` and `supersedes`

### Requirement: objective-files-carry-the-required-and-optional-sections

An objective file SHALL carry every required section and MAY carry the optional
section; the section layout is closed.

#### Scenario: the required sections are fixed

- **WHEN** the objective module's required-section list is inspected
- **THEN** every entry SHALL be one of the required section headings
- **AND** the list SHALL contain exactly the required sections

#### Scenario: only one section is optional

- **WHEN** the objective module's optional-section list is inspected
- **THEN** it SHALL contain exactly the section marked optional

### Requirement: objective-ledger-kinds-are-closed

The objective tracking ledger's `kind` SHALL be drawn from a closed set of five
values, and every one of them SHALL be accepted.

#### Scenario: the ledger kind enum has five values

- **WHEN** the objective module's ledger-kind list is inspected
- **THEN** it SHALL contain exactly five kinds

#### Scenario: every ledger kind is accepted

- **WHEN** an objective's ledger carries any of the five kinds
- **THEN** the structure check SHALL report no finding

### Requirement: objective-deferred-sections-require-an-na-reason

A section that may be waived SHALL NOT be left silently empty: the waiver SHALL be
written as `N/A — <reason>`, and a bare `N/A` SHALL be rejected.

#### Scenario: a well-formed waiver is accepted

- **WHEN** a waived section carries `N/A` followed by a reason
- **THEN** the waiver SHALL be accepted

#### Scenario: a bare N/A is rejected

- **WHEN** a waived section carries `N/A` without a reason
- **THEN** the waiver SHALL be rejected

#### Scenario: the waiver needs text after the dash

- **WHEN** a waived section carries `N/A` with nothing after the dash
- **THEN** the waiver SHALL be rejected

### Requirement: roadmap-lists-objectives-with-status-filter

`rddf roadmap list-objectives` SHALL list the objectives of a project, and SHALL
support filtering them by status.

#### Scenario: the listing shows the project's objectives

- **WHEN** `rddf roadmap list-objectives` runs in a project with objective files
- **THEN** every objective file SHALL appear in the listing

#### Scenario: the listing can be filtered by status

- **WHEN** `rddf roadmap list-objectives --status <status>` runs
- **THEN** only the objectives with that status SHALL appear

#### Scenario: the collection layer skips unusable files

- **WHEN** the objective collection runs over a directory that also holds a
  malformed file
- **THEN** the malformed file SHALL be skipped rather than abort the collection

### Requirement: roadmap-shows-an-objective-with-its-derived-view

`rddf roadmap show-objective <id>` SHALL render the objective's full content
together with the view the CLI derives from it.

#### Scenario: the command renders the derived view

- **WHEN** `rddf roadmap show-objective <id>` runs for an existing objective
- **THEN** the output SHALL contain the objective's content
- **AND** it SHALL contain the derived view

### Requirement: roadmap-revises-an-objective-and-records-the-revision

`rddf roadmap revise-objective <id>` SHALL revise the objective and SHALL record the
revision in the objective's ledger, bumping its `last_revised` field.

#### Scenario: a revision appends a ledger row and bumps last_revised

- **WHEN** `rddf roadmap revise-objective <id>` runs
- **THEN** the objective's ledger SHALL gain a revision row
- **AND** the objective's `last_revised` SHALL be updated

### Requirement: objective-validation-rejects-invalid-frontmatter

The objective validator SHALL reject frontmatter whose values violate the declared
types, enumerations or date format.

#### Scenario: a valid objective is accepted

- **WHEN** an objective's frontmatter satisfies every rule
- **THEN** the validator SHALL accept it

#### Scenario: an invalid status is rejected

- **WHEN** an objective declares a status outside the status enumeration
- **THEN** the validator SHALL reject it

#### Scenario: an invalid priority is rejected

- **WHEN** an objective declares a priority outside the priority enumeration
- **THEN** the validator SHALL reject it

#### Scenario: an invalid owner is rejected

- **WHEN** an objective declares an owner outside the allowed owners
- **THEN** the validator SHALL reject it

#### Scenario: a non-list manual dependency list is rejected

- **WHEN** an objective declares its manual dependencies as something other than a list
- **THEN** the validator SHALL reject it

#### Scenario: a non-ISO review date is rejected

- **WHEN** an objective declares a review date that is not an ISO date
- **THEN** the validator SHALL reject it

### Requirement: objective-validation-distinguishes-required-and-waived-sections

The objective validator SHALL distinguish the sections that must be present, the
sections that are optional, and the sections that may carry a waiver instead.

#### Scenario: a missing optional section is accepted

- **WHEN** an objective omits the optional section
- **THEN** the validator SHALL accept it

#### Scenario: a missing required section is rejected

- **WHEN** an objective omits a required section
- **THEN** the validator SHALL reject it

#### Scenario: a bare waiver in a required section is rejected

- **WHEN** a required section carries a bare `N/A`
- **THEN** the validator SHALL reject it

#### Scenario: a waiver with a reason in a required section is accepted

- **WHEN** a required section carries `N/A — <reason>`
- **THEN** the validator SHALL accept it

### Requirement: doctor-checks-objective-lifecycle

The doctor's objective-lifecycle category SHALL check the objectives' review schedule:
an active objective whose review date has passed SHALL be reported, and an objective
that is completed or archived SHALL not be.

#### Scenario: the lifecycle check passes on well-formed objectives

- **WHEN** the objective-lifecycle category runs on the project's objective files
- **THEN** it SHALL report no finding

#### Scenario: a missing review date produces a finding

- **WHEN** an objective file has no `review_by` field
- **THEN** the doctor SHALL report a finding

#### Scenario: an overdue active objective is reported

- **WHEN** an active objective's review date has passed
- **THEN** the grace period SHALL be exceeded

#### Scenario: a future review date is within grace

- **WHEN** an active objective's review date is in the future
- **THEN** the grace period SHALL NOT be exceeded

#### Scenario: a completed objective is not overdue

- **WHEN** a completed objective's review date has passed
- **THEN** the grace period SHALL NOT be exceeded

#### Scenario: an archived objective is not overdue

- **WHEN** an archived objective's review date has passed
- **THEN** the grace period SHALL NOT be exceeded

### Requirement: doctor-checks-objective-structure

The doctor's objective-structure category SHALL check the structural invariants of the
objective files: the ledger kinds must be from the closed set, and the review date
must be present.

#### Scenario: the structure check passes on well-formed objectives

- **WHEN** the objective-structure category runs on the project's objective files
- **THEN** it SHALL report no finding

#### Scenario: an unknown ledger kind produces a finding

- **WHEN** an objective's ledger carries a kind outside the closed set
- **THEN** the doctor SHALL report a finding

### Requirement: agents-md-carries-the-objectives-sentinel

The project's AGENTS.md SHALL carry an auto-generated sentinel block that lists the
project's objectives with their status and priority.

#### Scenario: the sentinel block is present

- **WHEN** the project's AGENTS.md is read
- **THEN** it SHALL contain the objectives sentinel block

#### Scenario: the sentinel lists the project's objectives

- **WHEN** the sentinel block is rendered
- **THEN** each of the project's objectives SHALL appear in it

#### Scenario: the sentinel shows status and priority

- **WHEN** the sentinel block is rendered
- **THEN** each listed objective SHALL carry its status and priority

#### Scenario: an archived objective is left out

- **WHEN** an objective has been archived
- **THEN** it SHALL NOT appear in the sentinel block
