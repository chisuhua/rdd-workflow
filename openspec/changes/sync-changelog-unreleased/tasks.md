## 1. Verify drift baseline

- [ ] 1.1 Run `git log --oneline afc369a..HEAD` and confirm ≥ 20 commits returned
- [ ] 1.2 Run `git log --oneline afc369a..HEAD -- CHANGELOG.md` and confirm 0 commits (CHANGELOG untouched)
- [ ] 1.3 Run `git log --oneline -1 CHANGELOG.md` and confirm last commit is `afc369a`

## 2. Sync CHANGELOG [Unreleased] section

- [ ] 2.1 Add `### rddf orchestrate (Python orchestrator for phase subprocess detection)` group with 11 commits
- [ ] 2.2 Add `### env-check gh_available field` group with 1 commit
- [ ] 2.3 Add `### archive close hook: lightweight mode` group with 1 commit
- [ ] 2.4 Verify `git diff --stat CHANGELOG.md` shows ≥ 30 added lines

## 3. Sync ADR-0027 cross-reference

- [ ] 3.1 Verify `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` already references `db355a0` (per `git log --oneline -1 -- docs/adr/ADR-0027-continuous-evolution-feedback-loop.md`)
- [ ] 3.2 Add Changelog category note in ADR-0027 (if missing)

## 4. Pre-commit verification

- [ ] 4.1 Run `git diff HEAD CHANGELOG.md` and verify 0 conflicts
- [ ] 4.2 Run `git log --oneline afc369a..HEAD -- CHANGELOG.md` and confirm ≥ 1 commit (CHANGELOG now committed)
- [ ] 4.3 Run `python3 -m pytest tests/unit/` and confirm 0 regression
- [ ] 4.4 Run `bash tests/scripts/report_regression.sh` and confirm 0 new failures

## 5. ADR-0027 dogfooding verification

- [ ] 5.1 BEFORE archive: confirm `_lib/issue_reporter.py::detect_issue` would detect "CHANGELOG drift" if run against current state
- [ ] 5.2 AFTER archive: confirm no new issue filed for this drift (gap fixed)
- [ ] 5.3 Update `iteration.json` to mark this change as `closed`
- [ ] 5.4 Verify close hook (`close_issues_for_change_hook`) keeps the test/issues symmetric in dual-mode (worktree + lightweight)
