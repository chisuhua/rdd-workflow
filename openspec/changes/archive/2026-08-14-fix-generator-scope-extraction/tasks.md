## Implementation Tasks

- [x] Add prefix-match logic for numbered items (`1. `, `2. `, `1) `, etc.) in `_extract_scope_items()`
- [x] Add sub-item attachment logic (indented `- ` lines appended to parent)
- [x] Add empty-section fallback: return `- (no items specified)` for missing In Scope / Out Scope
- [x] Split constraint items by MUST vs MUST NOT into Capabilities / Impact
- [x] Create `tests/unit/test_generate_full_proposal_scope.py` with 5 fixture scenarios
- [x] Verify backward compatibility: existing 138+ bullet-style files still extract correct item count
- [x] Verify `generate_full_proposal.py` delta ≤ 50 lines (line budget per proposal)
- [x] Run `./test.sh --python --unit` and confirm all green
- [ ] Run `./test.sh --full --regression` and verify no new failures (KNOWN_FAILURES.txt baseline)
- [ ] Update `proposal.md` for the change if implementation reveals assumptions incorrect
