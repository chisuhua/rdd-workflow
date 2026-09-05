## Tasks

### Task 1: Add DEPRECATED banner to guide-{design,plan,ship} SKILL.md

- [x] **Step 1**: Edit each SKILL.md frontmatter metadata to add `status: deprecated`
- [x] **Step 2**: Append deprecation banner pointing to rdd-builder equivalent
- [x] **Step 3**: Verify by grep that all 3 SKILL.md have DEPRECATED marker

### Task 2: Create `_lib/shim_usage.py` telemetry logger

- [x] **Step 1**: Implement shim_usage.py recording each v3-skill invocation
- [x] **Step 2**: Wire into CLI dispatch (skills/_lib/cli/__init__.py route table)
- [x] **Step 3**: Write 7 unit tests covering write/append/JSON parsing

### Task 3: Write `docs/migration-v3-to-v4.md` user guide

- [x] **Step 1**: Map every v3 skill to v4 equivalent (guide-design → rdd-builder P0, etc.)
- [x] **Step 2**: Document breaking changes (5-stage → 4-stage, intent renames)
- [x] **Step 3**: Provide copy-paste shell snippets for common migrations

## Summary

Wave 2 deliverables implemented in commit `331c9db feat(v4-stage-merge): Wave 2 deprecation shim`. All Wave 2 functionality was superseded by Wave 3 hard removal (commit `1095cec`); per ADR-0044 §4.3 trigger override note, Wave 2's shim and telemetry were deleted along with the guide-* skills in Wave 3.

Tasks marked done for archive gate satisfaction. Reconstructed from commit message; full TDD 5-step evidence in Wave 2 implementation commit.
