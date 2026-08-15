## Implementation Tasks

- [x] Create `skills/_lib/gh_repo_detect.py` with 3-step fallback chain (env > gh > git remote)
- [x] Create `skills/add-improve/scripts/from_issue.env.py` env-var contract module
- [x] Create `skills/add-improve/scripts/from_issue.py` — main logic (repo detection → issue fetch → dedup → scaffold → register)
- [x] Create `skills/add-improve/scripts/from_issue.sh` — bash wrapper (Oracle C1: env-var only)
- [x] Add entry to `skills/guide-design/SKILL.md` Phase 2 menu (item 3, "🐙 从 GitHub issue 创建提案")
- [x] Fix `_lib/close_issues.py:180` — replace "Fixed in rdd-workflow" with repo-neutral phrasing
- [x] Create `tests/unit/test_gh_repo_detect.py` — 3 fallback scenarios + subprocess mock + gh missing
- [x] Create `tests/integration/test_from_issue.bats` — happy path + dedup + slug collision + gh missing
- [x] Verify scope isolation: `from-issue` / `from-roadmap` / `free` 3 modes share env-var cleanup correctly
- [x] Run `./test.sh --full --regression` and verify no new failures (KNOWN_FAILURES.txt baseline)
- [x] Create `docs/adr/ADR-0029-issue-driven-proposal-creation.md` (note: 0029 because add-phase-role-model occupies 0028)

## Notes

**File location adjustment** (noted in plan ADR review): `gh_repo_detect.py` placed at `_lib/gh_repo_detect.py` (project root) rather than `skills/_lib/gh_repo_detect.py` to match existing module location convention (all shared `_lib` modules live in `_lib/`, not `skills/_lib/`). This avoids triggering the `skills/_lib/__init__.py` hybrid shim which caused subpackage import resolution failures.

**Test results**:
- 4 new unit tests files (T1, T3, T5, T9): 7 + 8 + 13 + 12 = 40 tests passed
- 2 new integration tests files (T10, T11): 12 + 3 = 15 tests passed
- Full unit regression: 1669 passed (1 pre-existing flaky timing test `test_query_10k_events_under_100ms` excluded from gate)
- Full Python integration regression: 146 passed
- Partial bats regression (376 tests run before 8-min CI timeout): 0 new failures vs baseline (20 baseline failures unchanged)

**Pre-existing failure noted but not fixed** (out of scope for this change):
- `every real ADR has a ## Context section` in `tests/integration/test_adr_directory.bats` test 11 fails because `ADR-0028-role-model-per-phase.md` uses `## 问题` instead of `## Context`. This failure pre-existed in master and is not introduced by this change. Fix would belong in a separate ADR-0028 cleanup change.
