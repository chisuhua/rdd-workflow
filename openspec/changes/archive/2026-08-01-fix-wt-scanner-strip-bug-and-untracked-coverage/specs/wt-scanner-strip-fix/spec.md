## ADDED Requirements

### Requirement: scanner preserves two-character git status prefix and path
`_detect_working_tree_issues` SHALL parse `git status --short` output without stripping leading whitespace, so the two-character status code and the project-relative path are read correctly.

#### Scenario: Working-tree-only modification is preserved
- **GIVEN** `git status --short` outputs ` M improvements/check-project-setup.md`
- **WHEN** `_detect_working_tree_issues` parses the line
- **THEN** the prefix is parsed as ` M` and the path is parsed as `improvements/check-project-setup.md`

#### Scenario: Staged modification is preserved
- **GIVEN** `git status --short` outputs `M  improvements/fix-scanner-fallback-and-orphan-archival.md`
- **WHEN** `_detect_working_tree_issues` parses the line
- **THEN** the prefix is parsed as `M ` and the path is parsed as `improvements/fix-scanner-fallback-and-orphan-archival.md`

### Requirement: working-tree-only modification is reported as modified
A line whose two-character status prefix is ` M` SHALL be reported as `category="modified"` with the full path and `severity="needs_review"`.

#### Scenario: Modified file is not misclassified as staged
- **GIVEN** a tracked file has only working-tree modifications (`git status --short` shows ` M`)
- **WHEN** `_detect_working_tree_issues` is called
- **THEN** it returns one issue with `category="modified"`, `path="foo.md"`, and `detail="有未暂存的修改"`

### Requirement: staged modification is reported as staged
A line whose two-character status prefix is `M ` SHALL be reported as `category="staged"` with the full path and `severity="needs_review"`.

#### Scenario: Staged file is not misclassified as modified
- **GIVEN** a tracked file has been staged (`git status --short` shows `M `)
- **WHEN** `_detect_working_tree_issues` is called
- **THEN** it returns one issue with `category="staged"`, `path="foo.md"`, and `detail="已暂存但未提交"`

### Requirement: path truncation is eliminated
The first character of the project-relative path SHALL NOT be removed when the status prefix is ` M`.

#### Scenario: Path keeps its leading character
- **GIVEN** a tracked file path starts with `p` and the status prefix is ` M`
- **WHEN** `_detect_working_tree_issues` is called
- **THEN** the returned issue `path` equals the original path and `path[0]` equals the expected first character
