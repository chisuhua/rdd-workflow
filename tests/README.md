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
    ├── test_*_skill.bats       # structural / metadata coverage per skill (9 files)
    ├── test_*_subagent.bats    # subagent integration tests
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
| guide            | `tests/integration/test_guide_skill.bats`                  |
| guide-arch       | `tests/integration/test_guide_arch_skill.bats`             |
| guide-plan       | `tests/integration/test_guide_plan_skill.bats`             |
| guide-ship       | `tests/integration/test_guide_ship_skill.bats`             |
| feature          | `tests/integration/test_feature_skill.bats`                |
| rddf-session     | `tests/integration/test_rddf_session_skill.bats`           |
| propose          | `tests/integration/test_propose_skill.bats`                |
| execute          | `tests/integration/test_execute_skill.bats`                |
| status           | `tests/integration/test_status_skill.bats`                 |
| roadmap          | `tests/integration/test_roadmap_skill.bats`                |
| deps             | `tests/integration/test_deps_skill.bats`                   |
| rdd-workflow/writing-plans | (locked by TDD discipline in `test_execute_skill.bats`) |
| (cross-skill)    | `tests/integration/test_skill_metadata_consistency.bats`   |
| (helper)         | `tests/_lib/test_skill.bats` (8 cases for `skill.bash`)    |

> `prometheus-planning.md` is intentionally excluded — it is
> invoked by `guide-ship` rather than tested in isolation.
