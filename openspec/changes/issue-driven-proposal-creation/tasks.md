## Implementation Tasks

- [ ] Create `skills/_lib/gh_repo_detect.py` with 3-step fallback chain (env > gh > git remote)
- [ ] Create `skills/add-improve/scripts/from_issue.env.py` env-var contract module
- [ ] Create `skills/add-improve/scripts/from_issue.py` — main logic (repo detection → issue fetch → dedup → scaffold → register)
- [ ] Create `skills/add-improve/scripts/from_issue.sh` — bash wrapper (Oracle C1: env-var only)
- [ ] Add entry to `skills/guide-design/SKILL.md` Phase 2 menu (item 3, "🐙 从 GitHub issue 创建提案")
- [ ] Fix `_lib/close_issues.py:180` — replace "Fixed in rdd-workflow" with repo-neutral phrasing
- [ ] Create `tests/unit/test_gh_repo_detect.py` — 3 fallback scenarios + subprocess mock + gh missing
- [ ] Create `tests/integration/test_from_issue.bats` — happy path + dedup + slug collision + gh missing
- [ ] Verify scope isolation: `from-issue` / `from-roadmap` / `free` 3 modes share env-var cleanup correctly
- [ ] Run `./test.sh --full --regression` and verify no new failures (KNOWN_FAILURES.txt baseline)
- [ ] Create `docs/adr/ADR-0029-issue-driven-proposal-creation.md` (note: 0029 because add-phase-role-model occupies 0028)
