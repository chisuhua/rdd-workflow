# add-proposal-source-tracking — Implementation Tasks

## Implementation

- [x] Extend `_lib/iteration/store.py::add_or_update_change` to support `source_session_id` and `audit_source` fields
- [x] Add `proposal_source_fields()` helper reading `RDDF_PROPOSAL_SOURCE_SESSION` / `RDDF_PROPOSAL_AUDIT_SOURCE` env vars (graceful None when unset)
- [x] Update `skills/guide-design/scripts/approve_proposal.sh` to record both fields on the iteration.json planned entry

## Tests

- [x] Write `tests/unit/test_proposal_source_tracking.py` with 5 unit tests (env auto-fill / audit_source / backward compat / graceful None / accepts new fields)
- [x] Verify all 5 tests pass (`pytest tests/unit/test_proposal_source_tracking.py -v`)
- [x] Regression: existing iteration store tests still pass (101 passed)