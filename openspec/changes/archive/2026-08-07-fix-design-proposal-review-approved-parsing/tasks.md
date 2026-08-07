# Tasks

- [x] Write failing unit tests in `tests/unit/test_parse_approved.py` (missing file / empty file / only `已批准提案` / only `已实施` / both sections dedup) and verify they fail.
- [x] Implement `skills/_lib/parse_approved.py` (`parse_approved_proposals(path: str) -> list[str]`, pure read-only, docstring per proposal SHOULDs) and verify unit tests pass.
- [x] Rewire `skills/guide-design/scripts/design_proposal_review.sh` approved-name parsing to the helper (Oracle C1 env-var pattern, no bash string interpolation).
- [x] Rewire `skills/guide/scripts/scan-state.sh` approved detection to the helper (same env-var pattern).
- [x] Rewire `skills/propose/scripts/propose_change.py:436` to import and call `parse_approved_proposals`.
- [x] Grep `skills/` for remaining `## 已实施` inline parsers; rewire any additional call site or record it as out of scope.
- [x] Add `tests/integration/test_approved_parsing_fix.bats` covering all three call sites (design review lists 0 false pending, scan-state approved count > 0, propose_change recognizes both-section entries).
- [x] Run `./test.sh --quick` and confirm green; confirm net new lines < 100.
- [x] Run the full regression gate (`./test.sh --full --regression`) before archive and record the result.
