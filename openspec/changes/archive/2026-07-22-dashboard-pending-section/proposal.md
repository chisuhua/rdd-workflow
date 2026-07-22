# dashboard-pending-section

**Priority**: P2
**Phase**: v2.1
**Status**: proposed

## Why

Dashboard's Pending section only shows a count ("14 pending"), not the actual entries. Users can't see which suggestions are pending without scrolling back to the proposal-suggestions.md file.

## 范围

- **In Scope**:
  - Add `SuggestionEntry` dataclass to dashboard `__init__.py`
  - Add `suggestions: list[SuggestionEntry]` field to `DashboardData`
  - Render pending suggestions table in `renderer.py`'s `_section_pending_terminal()`
  - Update tests in `test_dashboard_renderer.py`
  - Populate `suggestions` in `collect()` from `proposal-suggestions.md`
  - 1 bats test: dashboard shows pending entries
- **Out Scope**:
  - No changes to openspec CLI
  - No changes to iteration.json schema

## 验收标准
- `rddf dashboard` Pending section shows name, priority, status, phase table
- Entries with status "已完成" are excluded
- Tests pass
