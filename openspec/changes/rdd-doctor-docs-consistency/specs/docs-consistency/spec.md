## ADDED Requirements

### Requirement: docs-consistency-check
`rdd-doctor --category docs-consistency` SHALL run 6 deterministic checks on the repository and emit CRITICAL / WARNING / INFO issues for each drift category.

#### Scenario: User invokes --category docs-consistency
- **WHEN** user runs `bash skills/rdd-doctor/scripts/doctor.sh --category docs-consistency`
- **THEN** system runs all 6 checks (skill_count, stage_count, npm_test_caveat, version_consistency, adr_list_completeness, role_frontmatter) and exits non-zero if any CRITICAL is found

#### Scenario: User invokes --category all
- **WHEN** user runs `bash skills/rdd-doctor/scripts/doctor.sh --category all`
- **THEN** system includes docs-consistency in addition to existing 5 categories
