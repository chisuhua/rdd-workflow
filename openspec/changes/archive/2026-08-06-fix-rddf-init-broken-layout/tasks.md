# fix-rddf-init-broken-layout — Tasks

> Schema: spec-driven
> Created: 2026-08-05
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## 1. Setup & Discovery

- [x] 1.1 Confirm working tree clean (`git status`) before `git mv`
- [x] 1.2 Document current package layout baseline (screenshot of `ls skills/_lib/`)
- [x] 1.3 Capture PTX-EMU 11 subcommand output snapshots as regression baseline

## 2. Layout Flatten (the core refactor)

- [x] 2.1 `git mv skills/_lib/ _lib/` (preserve history, no `mv`)
- [x] 2.2 Verify `__pycache__/` regenerated in new location
- [x] 2.3 Create `skills/_lib/__init__.py` as re-export shim: `from _lib import *`
- [x] 2.4 Create `skills/_lib/<subdir>/__init__.py` re-export shims for each subdirectory under `_lib/`
- [x] 2.5 Verify `from skills._lib import X` still works (backward-compat smoke test)

## 3. Bug Fix: __main__.py:154 RDDF_PROJECT_ROOT

- [x] 3.1 Edit `skills/_lib/cli/__main__.py:154`: `os.environ["X"] = Y` → `os.environ.setdefault("X", Y)`
- [x] 3.2 Verify `RDDF_PROJECT_ROOT=~/.agents/skills/rdd-workflow rddf init /tmp/x` no longer overrides user input
- [x] 3.3 Run existing bats tests to confirm no regression

## 4. Bug Fix: init_cmd.py:_INSTALL_SOURCES

- [x] 4.1 Audit `_INSTALL_SOURCES` list in `skills/_lib/cli/init_cmd.py:26`
- [x] 4.2 Adjust copytree source paths to match new top-level `_lib/` location
- [x] 4.3 Verify init creates `/tmp/x/.opencode/skills/rdd-workflow/{skills/, _lib/, package.json, rddf.sh}` (4 files present)
- [x] 4.4 Verify init target's `python3 -c "from _lib.cli import init_cmd"` works (import smoke test)

## 5. Install Script Updates

- [x] 5.1 Update `install.sh` PYTHONPATH: `${PACKAGE_DIR}/skills/_lib` → `${PACKAGE_DIR}/_lib`
- [x] 5.2 Verify `rddf.sh` shim's `PACKAGE_DIR` resolution unchanged (BASH_SOURCE based)
- [x] 5.3 Verify `.pth` file creation logic still writes correct path
- [x] 5.4 Update `pyrightconfig.json` paths referencing `_lib`
- [x] 5.5 Update `pyproject.toml` paths referencing `_lib`

## 6. Regression Test Suite

- [x] 6.1 Create `tests/integration/test_init_smoke.bats` covering:
  - Scenario 1: `RDDF_PROJECT_ROOT=... rddf init /tmp/x` succeeds with 4 files
  - Scenario 2: init target `from _lib.cli import init_cmd` import succeeds
  - Scenario 3: `from skills._lib import X` backward-compat works
- [x] 6.2 Add python unit test for `setdefault` semantics in `__main__.py:154`
- [x] 6.3 Run full `pytest tests/` and confirm 0 failures (no skip allowed)
- [x] 6.4 Run full `bats tests/` (smoke + static + git-worktree) and confirm 0 failures

## 7. Cross-Subcommand Regression Check

- [x] 7.1 From PTX-EMU: capture output of `rddf version` (baseline)
- [x] 7.2 From PTX-EMU: capture output of `rddf guide` (baseline)
- [x] 7.3 From PTX-EMU: capture output of `rddf dashboard` (baseline)
- [x] 7.4 From PTX-EMU: capture output of `rddf status` (baseline)
- [x] 7.5 From PTX-EMU: capture output of `rddf feature` (baseline)
- [x] 7.6 From PTX-EMU: capture output of `rddf sessions` (baseline)
- [x] 7.7 From PTX-EMU: capture output of `rddf monitor` (baseline)
- [x] 7.8 From PTX-EMU: capture output of `rddf validate` (baseline)
- [x] 7.9 From PTX-EMU: capture output of `rddf cleanup` (baseline)
- [x] 7.10 Post-fix: diff all 9 outputs (must be 0 line difference)
- [x] 7.11 Post-fix: `rddf init` output changes from FAILURE to SUCCESS

## 8. Documentation & Changelog

- [x] 8.1 Update `CHANGELOG.md` with breaking-change section: `### Breaking — package layout: skills/_lib → _lib`
- [x] 8.2 Update `README.md` "Install" section to reflect new layout
- [x] 8.3 Add new `_lib/__init__.py` explaining the layout change
- [x] 8.4 Update `docs/architecture/` layout docs (if any reference old path)

## 9. PR & Archive

- [x] 9.1 Single conventional commit: `fix(init): flatten package layout per fix-rddf-init-broken-layout`
- [x] 9.2 PR includes success log from PTX-EMU `RDDF_PROJECT_ROOT=~/.agents/skills/rdd-workflow rddf init /tmp/x`
- [x] 9.3 PR includes regression test output (bats + pytest both green)
- [x] 9.4 Verify `git log --oneline | grep fix-rddf-init-broken-layout` shows the commit
- [x] 9.5 Verify `openspec validate fix-rddf-init-broken-layout --json` exits 0
- [x] 9.6 Verify proposal-approved.md entry unchanged (independent PR contract)
