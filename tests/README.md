# Tests

Bats-core test infrastructure for the rdd-workflow skill pack.

## Layout

```
tests/
├── README.md          # this file
├── test_helper.bash   # common setup/teardown + assertion helpers (load_lib resolver)
├── smoke.bats         # basic infrastructure sanity checks (7 cases)
├── _lib/              # bash helpers + per-helper unit tests
│   ├── skill.bash              # shared frontmatter/metadata/commands/section parsers
│   ├── deps-subagent.bash      # deps subagent step-3 validation
│   ├── test_skill.bats         # unit tests for skill.bash (8 cases)
│   └── test_worktree.bats      # unit tests for skills/_lib/worktree.sh
└── integration/       # cross-component / CLI integration tests
    ├── test_<issue-id>.bats    # regression locks for P0/P1/P2/P3 fixes
    ├── test_*_skill.bats       # structural / metadata coverage per skill
    ├── test_*_subagent.bats    # subagent integration tests
    ├── scan_state.bats         # guide recommender routing (rdd-* v4 names)
    ├── test_rdd_arch_cli.bats  # rdd-arch CLI surface
    ├── test_rdd_builder_phases.bats  # rdd-builder phase state machine
    ├── test_rdd_verifier_*.bats      # rdd-verifier (9 files)
    ├── test_rddf_session_*.bats/.py  # rddf-session lifecycle & concurrency
    └── test_skill_metadata_consistency.bats  # package.json ↔ skills/ ↔ smoke.bats agreement
```

## Running

```bash
# All tests
bats tests/

# Single file
bats tests/smoke.bats

# Via npm script
npm test
```

## Known failure baseline

`tests/KNOWN_FAILURES.txt` contains the current, reviewed set of pre-existing Bats failures. Each line uses the Bats test name followed by a reason/environment comment. Known failures remain visible in the Bats output and are reported as `已知失败`; they do not fail the incremental gate.

Run the shared local/CI comparison with:

```bash
bash tests/scripts/report_regression.sh
```

A failure not present in the baseline is reported as `新增失败` and returns non-zero. Do not add it automatically. After confirming the failure is environmental or otherwise intentionally accepted, review the reason and run the explicit refresh command:

```bash
bash tests/scripts/refresh_known_failures.sh
```

Review the resulting diff before committing. Remove a fixed test from the baseline by refreshing after confirming the test is green. CI runs the same report script after the recursive Bats step, so local and CI use one comparison implementation.

### Selective refresh (added 2026-10-08, per add-known-failures-selective-refresh)

The refresh script now operates in **selective** mode by default — it preserves all comment lines verbatim, drops entries that no longer fail, and appends newly-discovered failures with `# reason required (added YYYY-MM-DD by refresh_known_failures.sh)` placeholders. After a refresh, **you must triage the placeholders**: replace each with a real reason (link to a follow-up issue/ADR, or note the doc-drift/script-drift root cause). Use `bash skills/rdd-doctor/scripts/doctor.sh --category baseline-freshness` to detect un-triaged placeholders.

#### Flags

```bash
# Default: run bats on tests/integration/, then selective diff
bash tests/scripts/refresh_known_failures.sh

# Preview the diff without writing (safe)
bash tests/scripts/refresh_known_failures.sh --dry-run

# Use a pre-collected failure set (works around bats-core 1.13.0
# `bats tests/ --recursive` infinite-loop bug; see collect helper below)
bash tests/scripts/refresh_known_failures.sh --actual /tmp/actual.txt

# Narrow scope to a single test file (faster iteration)
bash tests/scripts/refresh_known_failures.sh \
    --scope tests/integration/test_known_failures_baseline.bats
```

#### Helper: collect failures (bypasses bats-core 1.13.0 bug)

`bats tests/ --recursive` triggers an infinite loop in bats-core 1.13.0 (`test_list_file.txt: No such file or directory` race). `tests/scripts/collect_bats_failures.sh` works around this by running each `.bats` file individually with a per-file timeout:

```bash
# Default: 30s timeout per file, output to /tmp/bats-failures.txt
bash tests/scripts/collect_bats_failures.sh

# Faster (but may miss failures in slow files)
BATS_TIMEOUT=10 bash tests/scripts/collect_bats_failures.sh tests/integration/ /tmp/actual.txt

# Then feed into the refresh script
bash tests/scripts/refresh_known_failures.sh --actual /tmp/actual.txt
```

#### Identity-merge shim pattern

Modules promoted from `skills/_lib/` to top-level `_lib/` need a backward-compat shim so `from skills._lib.X import Y` and `from _lib.X import Y` resolve to the same module object (so `isinstance()` and module-level state — caches, locks, registries — are shared). The pattern:

```python
# skills/_lib/<X>.py — 28-line identity-merge shim
import os as _os, sys as _sys, types as _types
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_HERE))  # adjust depth for nested shims
_REAL_PATH = _os.path.join(_REPO_ROOT, "_lib", "<X>.py")
_real = _sys.modules.get("_lib.<X>")
if _real is None or getattr(_real, "__file__", None) == __file__:
    _real = _types.ModuleType("_lib.<X>")
    _real.__file__ = _REAL_PATH
    _real.__name__ = "_lib.<X>"
    _sys.modules[_real.__name__] = _real
    with open(_REAL_PATH, encoding="utf-8") as _f:
        exec(compile(_f.read(), _REAL_PATH, "exec"), _real.__dict__)
_sys.modules[__name__] = _real
```

**Critical** — the `if _real is None or _real.__file__ == __file__` check is NOT `if _real is None`. When the shim is loaded via `import _lib.<X>` (rather than `import skills._lib.<X>`), Python adds the shim itself to `sys.modules` BEFORE the shim body runs, so a plain `is None` check would skip the exec and leave the shim empty. The `__file__ == __file__` guard catches this case (per add-shim-coverage-lint 2026-10-08).

The CI lint at `tests/unit/test_skills_lib_shim_coverage.py` enforces:
1. Every actively-imported `from skills._lib.X` has a shim at `skills/_lib/X.py`
2. Every imported shim has a real module at `_lib/X.py`
3. Every imported shim that has a real counterpart performs identity-merge (`sys.modules[__name__] = _real`)

## Conventions

- All test files use `.bats` extension.
- `load test_helper` at the top of every `.bats` file gives you:
  - `$REPO_ROOT` (absolute path to repo root)
  - `setup()` / `teardown()` stubs
  - `load_lib <name>` to source `tests/_lib/<name>.bash`
  - `assert_file_exists`, `assert_file_contains`, `assert_cmd_succeeds`
- Skill metadata tests use the `load_lib skill` helper, which provides
  `skill_field`, `skill_meta_field`, `skill_commands`, `skill_has_section`,
  and `skill_frontmatter_block` for parsing skill Markdown files.
- Test data files belong in `tests/_lib/` (versioned) or `$BATS_TMPDIR` (auto-cleaned, ephemeral).
- **Bats tmpdir variables** (don't conflate):
  - `$BATS_TMPDIR` — per-run directory shared by all tests in a run; set by bats-core.
  - `$BATS_TEST_TMPDIR` — per-test directory auto-cleaned after each test; set by bats-core.
  - `mktemp -d` — explicit subdir; preferred when a single test needs its own scratch root.
  - Six legacy tests assume `$BATS_TMPDIR` is per-run (shared); new tests should prefer
    `mktemp -d` or `$BATS_TEST_TMPDIR` to avoid cross-test contamination.
- Use bash builtins; **do not add** mocking/coverage frameworks.
- Tests must be runnable from repo root: `bats tests/`.

## Coverage Expectations

- T2: extract pure functions from guide-spec / guide-ship into `lib/` and add `tests/_lib/` unit tests.
- T3: add prometheus declaration round-trip tests under `tests/integration/`.
- Future audit fixes: add `tests/integration/test_<issue-id>.bats` for each P0/P1 fix.

## Skill coverage map

Each skill has a dedicated integration test file that locks its
frontmatter, dependency declarations, and command/section surface.
Together with the cross-skill consistency check, these guard against
metadata drift between `package.json`, `skills/<name>/SKILL.md`, and `smoke.bats`.`

| Skill            | Test file                                                  |
|------------------|------------------------------------------------------------|
| INSTALL          | `tests/integration/test_install_skill.bats`                |
| guide            | `tests/integration/scan_state.bats` (routing) + `tests/smoke.bats` (existence) |
| rdd-arch         | `tests/integration/test_rdd_arch_cli.bats` + `test_arch_*_extraction.bats` |
| rdd-planner      | `tests/integration/test_planner_cmd.bats` + `test_arch_handoff_extraction.bats` |
| rdd-builder (plan+ship) | `tests/integration/test_rdd_builder_phases.bats` + `test_filter_guide_ship.bats` |
| rdd-verifier     | `tests/integration/test_rdd_verifier_*.bats` (9 files)     |
| rdd-quick        | `tests/integration/test_rdd_quick.bats`                    |
| feature          | `tests/integration/test_feature_skill.bats`                |
| rddf-session     | `tests/integration/test_rddf_session_{current,status,auto_archive,owner_stability,hook_required,sub_phase,workflow_group}.bats` + `test_rddf_session_*.py` |
| propose          | `tests/integration/test_propose_skill.bats`                |
| execute          | `tests/integration/test_execute_skill.bats`                |
| status           | `tests/integration/test_status_skill.bats`                 |
| roadmap          | `tests/integration/test_roadmap_skill.bats`                |
| deps             | `tests/integration/test_deps_skill.bats`                   |
| rdd-doctor       | `tests/integration/test_rdd_doctor.bats` (+ `tests/smoke.bats` registration) |
| rdd-workflow-writing-plans | (locked by TDD discipline in `test_execute_skill.bats`) |
| (cross-skill)    | `tests/integration/test_skill_metadata_consistency.bats`   |
| (helper)         | `tests/_lib/test_skill.bats` (8 cases for `skill.bash`)    |

> `prometheus-planning.md` is intentionally excluded — it is
> invoked by `guide-ship` rather than tested in isolation.

## Characterization tests

Pytest tests marked with `@pytest.mark.characterization` lock the **current behavior** of the system under test, regardless of whether that behavior is correct. They serve as a baseline for future refactoring and provide evidence for fix proposals when characterization reveals genuine bugs.

Run only characterization tests:

```bash
pytest -m characterization
```

Exclude them from functional test runs:

```bash
pytest -m "not characterization"
```

Characterization tests do not assert a specific pass/fail outcome. They assert that the behavior is consistent and reproducible. If a future change intentionally alters the behavior, both the test and the design must be updated.
