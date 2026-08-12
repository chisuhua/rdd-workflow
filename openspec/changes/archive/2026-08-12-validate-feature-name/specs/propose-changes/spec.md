## ADDED Requirements

### Requirement: parent-feature-name-validation

The system SHALL validate `parent_feature` values at propose and approve entry points by comparing against existing features collected from `.rddf/state/iteration.json`, warning (default) or erroring (when `STRICT_FEATURE_VALIDATION=yes`) on values not in the existing set, and excluding the synthetic `__ungrouped__` key from the comparison set.

#### Scenario: Typo detection warns but proceeds (default)
- **WHEN** `iteration.json` contains a change with `parent_feature="wave-core"` and propose creates a new change with `parent_feature="wave-cores"` (typo)
- **THEN** propose SHALL output a WARNING containing the existing feature list
- **AND** the change SHALL still be written to disk (non-blocking default)

#### Scenario: Correct spelling passes silently
- **WHEN** `iteration.json` contains a change with `parent_feature="wave-core"` and propose creates a new change with `parent_feature="wave-core"` (correct)
- **THEN** propose SHALL NOT emit a warning
- **AND** the change SHALL be written to disk

#### Scenario: Empty iteration.json passes all values
- **WHEN** `.rddf/state/iteration.json` does not exist or contains zero changes
- **THEN** propose SHALL NOT emit a parent_feature validation warning for any `parent_feature` value
- **AND** the change SHALL be written to disk (first-feature case)

#### Scenario: STRICT mode blocks typo
- **WHEN** `STRICT_FEATURE_VALIDATION=yes` is set
- **AND** propose creates a change with `parent_feature="brand-new"` (not in existing)
- **THEN** propose SHALL exit with a non-zero status code
- **AND** the error output SHALL include the list of existing features

#### Scenario: Synthetic __ungrouped__ excluded
- **WHEN** `iteration.json` contains a change with `parent_feature="__ungrouped__"`
- **THEN** the existing-feature list SHALL NOT include `__ungrouped__`
- **AND** proposing `parent_feature="__ungrouped__"` SHALL NOT trigger a warning

#### Scenario: Approve entry point validates (bash)
- **WHEN** `guide-design/scripts/approve_proposal.sh` writes `roadmap-meta.yaml` with `parent_feature="wave-cores"` (typo)
- **THEN** the script SHALL output a WARNING matching the same format as the Python entry point
- **AND** the change SHALL still be written (default behavior consistent across paths)
