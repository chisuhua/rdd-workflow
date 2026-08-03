## 1. Setup

- [ ] 1.1 Read `proposal.md`, `design.md`, `improvements/add-known-failures-baseline.md` and confirm In Scope / Out of Scope boundaries
- [ ] 1.2 Verify current failure baseline: run `bats tests/ --recursive 2>&1 | grep -c '^not ok'` on master to confirm the 41 known failures; capture exact `not ok N <test name>` output format
- [ ] 1.3 Inspect `.github/workflows/test.yml` last step (`bats tests/ --recursive`) and `tests/README.md` layout section; confirm bats version (>= 1.10)

## 2. Implementation (TDD 5 步)

- [ ] 2.1 Write failing tests: add bats/unit cases for the regression report parser — baseline filtering (known failures counted but not failing), incremental failure detection (new failure → exit non-zero + listed), zero-regression (0 new → exit 0), refresh script round-trip (generated file diffable against KNOWN_FAILURES.txt), and comment-preserving refresh
- [ ] 2.2 Verify tests fail (red): confirm `tests/scripts/report_regression.sh` / `refresh_known_failures.sh` / `tests/KNOWN_FAILURES.txt` do not exist yet and no CI incremental-failure gate exists
- [ ] 2.3 Implement change: create `tests/KNOWN_FAILURES.txt` (41 items with reason/env-dependency comments); create `tests/scripts/report_regression.sh` (run full bats → extract `not ok` test names → `comm -23` vs baseline → report incremental failures, exit non-zero only on new failures; always show "N 个已知失败" count); create `tests/scripts/refresh_known_failures.sh` (generate current full failure list, merge-preserving existing comments); update `tests/README.md` with KNOWN_FAILURES maintenance notes (add/remove/refresh); add CI gate step in `.github/workflows/test.yml` after the bats step (fail only on incremental failures)
- [ ] 2.4 Verify tests pass (green): zero-regression run shows "0 新增" and exits 0; deliberately break a file (e.g. `echo broken >> skills/guide/SKILL.md` temporary) → report flags "1 新增失败" and exits non-zero; refresh script regenerates a baseline diffable against the current KNOWN_FAILURES.txt
- [ ] 2.5 Refactor + commit: confirm CI and local use the same comparison script (single source), no known failures silently swallowed (count always shown), refresh never auto-adds incremental failures, diff is proposal-only scope, then commit

## 3. Verification

- [ ] 3.1 Run `openspec validate add-known-failures-baseline --json` — 接受 specs/ 缺失 ERROR (本次 fill 不写 specs/, plan 阶段决策)
- [ ] 3.2 Run `bash tests/scripts/report_regression.sh` on clean tree → "0 新增" + exit 0 (known 41 filtered to count)
- [ ] 3.3 Negative check: introduce a temporary failure (modify one test file), re-run report → "1 新增失败" + exit non-zero; revert the breakage
- [ ] 3.4 Run `bash tests/scripts/refresh_known_failures.sh` → regenerated baseline diffable against KNOWN_FAILURES.txt; comments preserved on unchanged entries
- [ ] 3.5 Run `npm test` full bats regression + `python3 -m pytest tests/unit/ tests/integration/ -q` — zero regression
- [ ] 3.6 Confirm `.github/workflows/test.yml` incremental-failure gate step present after the bats step; confirm `tests/README.md` contains KNOWN_FAILURES maintenance section
- [ ] 3.7 Run `git show HEAD:openspec/changes/add-known-failures-baseline/design.md` (artifact committed)

## 4. Documentation

- [ ] 4.1 Add `tests/README.md` KNOWN_FAILURES section documenting add/remove/refresh workflow
- [ ] 4.2 Add entry to `CHANGELOG.md` (if present)
- [ ] 4.3 Confirm no ADR change needed (out of scope per proposal)
