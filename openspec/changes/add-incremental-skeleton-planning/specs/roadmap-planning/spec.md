## ADDED Requirements

### Requirement: roadmap-category-validation
The system SHALL validate that a change's category matches its roadmap phase's valid categories.

For skeleton changes (`planned` status), validation SHALL be relaxed: the change SHALL only require a valid category assignment; it SHALL NOT require complete design documentation for category validation.

#### Scenario: Skeleton change passes category validation
- **WHEN** a skeleton change has `roadmap-meta.yaml` with `category: "core-impl"` and the current phase includes "core-impl" as a valid category
- **THEN** category validation SHALL pass
- **AND** no design.md is required for the validation

#### Scenario: Skeleton change with invalid category
- **WHEN** a skeleton change has `category: "unknown-cat"` not in the current phase's valid categories
- **THEN** category validation SHALL warn the user
- **AND** SHALL offer to reassign to a valid category or use "general"