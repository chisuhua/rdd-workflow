# Tests

Bats-core test infrastructure for the spec-workflow skill pack.

## Layout

```
tests/
├── README.md          # this file
├── test_helper.bash   # common setup/teardown + assertion helpers
├── smoke.bats         # basic infrastructure sanity checks
├── _lib/              # bash helpers loaded via `load_lib <name>` in test files
│                       # (populated in T2 with extracted lib functions)
└── integration/       # cross-component / CLI integration tests
                        # (populated in T2/T3+ with .bats files)
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

## Conventions

- All test files use `.bats` extension.
- `load test_helper` at the top of every `.bats` file gives you:
  - `$REPO_ROOT` (absolute path to repo root)
  - `setup()` / `teardown()` stubs
  - `load_lib <name>` to source `tests/_lib/<name>.bash`
  - `assert_file_exists`, `assert_file_contains`, `assert_cmd_succeeds`
- Test data files belong in `tests/_lib/` (versioned) or `$BATS_TMPDIR` (auto-cleaned, ephemeral).
- Use bash builtins; **do not add** mocking/coverage frameworks.
- Tests must be runnable from repo root: `bats tests/`.

## Coverage Expectations

- T2: extract pure functions from guide-spec / guide-ship into `lib/` and add `tests/_lib/` unit tests.
- T3: add prometheus declaration round-trip tests under `tests/integration/`.
- Future audit fixes: add `tests/integration/test_<issue-id>.bats` for each P0/P1 fix.
