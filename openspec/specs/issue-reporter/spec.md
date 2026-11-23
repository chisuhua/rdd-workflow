# issue-reporter Specification

## Purpose
TBD - created by archiving change fix-adr-0027-issue-file-frontmatter. Update Purpose after archive.
## Requirements
### Requirement: fix-adr-0027-issue-file-frontmatter
The system SHALL implement fix-adr-0027-issue-file-frontmatter functionality per proposal.md scope.

#### Scenario: scenario-1
- **GIVEN** **WHEN** `_render_issue_body` 执行
- **WHEN** **THEN** 生成的 `.rddf/issues/phase-crash-<hash>.md` 含:
- **THEN** ```yaml
---
category: phase-crash
detected_at: 2026-08-24T10:23:45Z
rdd_workflow_version: 2.1.0
dedup_hash: a1b2c3d4
submitted: false
submitted_url: null
exit_code: 137
---

