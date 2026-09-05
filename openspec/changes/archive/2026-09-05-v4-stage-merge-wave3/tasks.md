## Tasks

### Task 1: Delete `skills/guide-{design,plan,ship}/` directories

- [x] **Step 1**: Remove guide-design/ + all SKILL.md/scripts (21 files)
- [x] **Step 2**: Remove guide-plan/ + all SKILL.md/scripts (15 files)
- [x] **Step 3**: Remove guide-ship/ + all SKILL.md/scripts (12 files)

### Task 2: Delete integration bats for removed skills

- [x] **Step 1**: Remove 17 `tests/integration/test_guide_*.bats` files
- [x] **Step 2**: Remove `tests/integration/test_legacy_guide_*_shim.bats`
- [x] **Step 3**: Run bats recursive; verify no orphan failures from missing skill files

### Task 3: Delete Wave 2 telemetry + shim

- [x] **Step 1**: Remove `_lib/shim_usage.py` (no longer needed after guide-* deletion)
- [x] **Step 2**: Remove `tests/unit/test_shim_usage.py` (7 tests for removed module)

### Task 4: Update `install.sh` + `skills/INSTALL.md`

- [x] **Step 1**: Remove guide-{arch,design,plan,ship} references from install.sh verbose usage
- [x] **Step 2**: Update INSTALL.md sub-skill table (remove 3 guide-* rows)
- [x] **Step 3**: Update AGENTS.md stage table (5-stage → 4-stage v4)

### Task 5: Add ADR-0044 (Wave 3 decision record)

- [x] **Step 1**: Draft ADR-0044-v4-stage-merge-wave3-hard-removal.md
- [x] **Step 2**: Document trigger condition override rationale
- [x] **Step 3**: Add ADR-0044 to docs/adr/README.md index

### Task 6: Single worktree commit (per AGENTS.md discipline)

- [x] **Step 1**: Single commit with all DELETE/UPDATE/NEW files
- [x] **Step 2**: Merge wave3 branch into master (commit `d5b152a`)

## Summary

Wave 3 hard removal implemented in commit `1095cec feat(v4-stage-merge): Wave 3 hard removal of guide-* skills`. 76 files changed: 48 deleted (3 skill dirs), 17 test files deleted, 5 files updated (install.sh, AGENTS.md, docs/adr/README.md), 2 new files (ADR-0044, openspec/changes/v4-stage-merge-wave3/{proposal,tasks}.md).

Trigger override rationale per ADR-0044: user explicitly authorized hard removal despite spec §4.3 triggers not being met (internal testing/decision-validation use case). 4 follow-up items documented in ADR-0044 (dead-code cleanup, batch test fill, push-after-prior-failures-check, force-field safety).
