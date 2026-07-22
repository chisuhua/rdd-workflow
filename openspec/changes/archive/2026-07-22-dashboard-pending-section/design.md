## Design

Use the existing `_collect_suggestions()` in dashboard render flow. The
`SuggestionEntry` dataclass mirrors proposal-suggestions.md entry fields.
The dashboard `render()` function calls `_section_pending_terminal()` which
iterates `data.suggestions` to produce the table rows.

### Data Flow
```
collect()
  -> _collect_suggestions() reads proposal-suggestions.md
  -> filters out "已完成" entries
  -> populates data.suggestions (list[SuggestionEntry])
render()
  -> _section_pending_terminal()
  -> iterates data.suggestions for each table row
```

### Files
- `skills/_lib/dashboard/__init__.py`: SuggestionEntry dataclass + suggestions field + _collect_suggestions()
- `skills/_lib/dashboard/renderer.py`: table rendering loop
- `tests/unit/test_dashboard_renderer.py`: test fixture update + new test
