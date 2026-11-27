# status-issue-visibility Specification

## Purpose
TBD - created by archiving change fix-status-issue-list-truncation. Update Purpose after archive.

## Requirements

### Requirement: Status issue lists SHALL NOT be silently truncated

`rddf status` SHALL list every improvement issue it reports: the heading count SHALL equal the number of listed entries, and any entry not shown SHALL be announced by an explicit remainder line naming the count and pointing at the full view (`rddf dashboard`). Status snippets SHALL be trimmed at a safe boundary and end with an ellipsis, so markdown emphasis or quotes are never cut in half. Snippet cleaning SHALL reuse the classifier's markdown stripping — one implementation.

#### Scenario: Six reported issues are all listed

- **WHEN** six improvements carry stale status lines and `rddf status` runs
- **THEN** the heading states six issues, six issue lines are printed, and no remainder line appears
