# fix-rddf-init-broken-layout — Tasks

> Schema: spec-driven
> Created: 2026-08-05
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## 1. Setup & Discovery

- [ ] 1.1 Confirm working tree clean (`git status`) before `git mv`
- [ ] 1.2 Document current package layout baseline (screenshot of `ls skills/_lib/`)
- [ ] 1.3 Capture PTX-EMU 11 subcommand output snapshots as regression baseline

## 2. Layout Flatten (the core refactor)

- [ ] 2.1 `git mv skills/_lib/ _lib/` (preserve history, no `mv`)
- [ ] 2.2 Verify `__pycache__/` regenerated in new location
- [ ] 2.3 Create `skills/_lib/__init__.py` as re-export shim: `from _lib import *`
- [ ] 2.4 Create `skills/_lib/<subdir>/__init__.py` re-export shims for each subdirectory under `_lib/`
- [ ] 2.5 Verify `from skills._lib import X` still works (backward-compat smoke test)

## 3. Bug Fix: __main__.py:154 RDDF_PROJECT_ROOT

- [ ] 3.1 Edit `skills/_lib/cli/__main__.py:154`: `os.environ["X"] = Y` → `os.environ.setdefault("X", Y)`
- [ ] 3.2 Verify `RDDF_PROJECT_ROOT=~/.agents/skills/rdd-workflow rddf init /tmp/x` no longer overrides user input
- [ ] 3.3 Run existing bats tests to confirm no regression

## 4. Bug Fix: init_cmd.py:_INSTALL_SOURCES

- [ ] 4.1 Audit `_INSTALL_SOURCES` list in `skills/_lib/cli/init_cmd.py:26`
- [ ] 4.2 Adjust copytree source paths to match new top-level `_lib/` location
- [ ] 4.3 Verify init creates `/tmp/x/.opencode/skills/rdd-workflow/{skills/, _lib/, package.json, rddf.sh}` (4 files present)
- [ ] 4.4 Verify init target's `python3 -c "from _lib.cli import init_cmd"` works (import smoke test)

## 5. Install Script Updates

- [ ] 5.1 Update `install.sh` PYTHONPATH: `${PACKAGE_DIR}/skills/_lib` → `${PACKAGE_DIR}/_lib`
- [ ] 5.2 Verify `rddf.sh` shim's `PACKAGE_DIR` resolution unchanged (BASH_SOURCE based)
- [ ] 5.3 Verify `.pth` file creation logic still writes correct path
- [ ] 5.4 Update `pyrightconfig.json` paths referencing `_lib`
- [ ] 5.5 Update `pyproject.toml` paths referencing `_lib`

## 6. Regression Test Suite

- [ ] 6.1 Create `tests/integration/test_init_smoke.bats` covering:
  - Scenario 1: `RDDF_PROJECT_ROOT=... rddf init /tmp/x` succeeds with 4 files
  - Scenario 2: init target `from _lib.cli import init_cmd` import succeeds
  - Scenario 3: `from skills._lib import X` backward-compat works
- [ ] 6.2 Add python unit test for `setdefault` semantics in `__main__.py:154`
- [ ] 6.3 Run full `pytest tests/` and confirm 0 failures (no skip allowed)
- [ ] 6.4 Run full `bats tests/` (smoke + static + git-worktree) and confirm 0 failures

## 7. Cross-Subcommand Regression Check

- [ ] 7.1 From PTX-EMU: capture output of `rddf version` (baseline)
- [ ] 7.2 From PTX-EMU: capture output of `rddf guide` (baseline)
- [ ] 7.3 From PTX-EMU: capture output of `rddf dashboard` (baseline)
- [ ] 7.4 From PTX-EMU: capture output of `rddf status` (baseline)
- [ ] 7.5 From PTX-EMU: capture output of `rddf feature` (baseline)
- [ ] 7.6 From PTX-EMU: capture output of `rddf sessions` (baseline)
- [ ] 7.7 From PTX-EMU: capture output of `rddf monitor` (baseline)
- [ ] 7.8 From PTX-EMU: capture output of `rddf validate` (baseline)
- [ ] 7.9 From PTX-EMU: capture output of `rddf cleanup` (baseline)
- [ ] 7.10 Post-fix: diff all 9 outputs (must be 0 line difference)
- [ ] 7.11 Post-fix: `rddf init` output changes from FAILURE to SUCCESS

## 8. Documentation & Changelog

- [ ] 8.1 Update `CHANGELOG.md` with breaking-change section: `### Breaking — package layout: skills/_lib → _lib`
- [ ] 8.2 Update `README.md` "Install" section to reflect new layout
- [ ] 8.3 Add new `_lib/__init__.py` explaining the layout change
- [ ] 8.4 Update `docs/architecture/` layout docs (if any reference old path)

## 9. PR & Archive

- [ ] 9.1 Single conventional commit: `fix(init): flatten package layout per fix-rddf-init-broken-layout`
- [ ] 9.2 PR includes success log from PTX-EMU `RDDF_PROJECT_ROOT=~/.agents/skills/rdd-workflow rddf init /tmp/x`
- [ ] 9.3 PR includes regression test output (bats + pytest both green)
- [ ] 9.4 Verify `git log --oneline | grep fix-rddf-init-broken-layout` shows the commit
- [ ] 9.5 Verify `openspec validate fix-rddf-init-broken-layout --json` exits 0
- [ ] 9.6 Verify proposal-approved.md entry unchanged (independent PR contract)