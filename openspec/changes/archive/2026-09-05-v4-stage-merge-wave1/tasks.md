## Tasks

### Task 1: Setup worktree + OpenSpec change skeleton

- [x] **Step 1**: Branch + worktree created (`openspec/v4-stage-merge-wave1` branch, `.rddf/wt/v4-stage-merge-wave1/` directory)
- [x] **Step 2**: OpenSpec change directory created with proposal.md
- [x] **Step 3**: Spec file accessible from worktree (1003 lines verified)
- [x] **Step 4**: Plan file accessible from worktree (3329 lines verified)
- [x] **Step 5**: Defer commit (per execute.md convention)

### Task 2: Slim rdd-arch — remove roadmap fields from arch-handoff writer

- [x] **Step 1**: Write failing test for writer omitting removed fields
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Modify writer to omit roadmap fields
- [x] **Step 4**: Run test to verify it passes
- [x] **Step 5**: Run all arch-handoff tests; verify regression gate

### Task 3: Remove `_check_roadmap_defined` from gate.py + arch_done registration

- [x] **Step 1**: Write failing test asserting function absence
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Remove `_check_roadmap_defined` from gate.py
- [x] **Step 4**: Update existing test references
- [x] **Step 5**: Run all related tests; verify pass

### Task 4: Bump arch-handoff schema to v3 + extend test coverage

- [x] **Step 1**: Write failing test for v3 contract
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Update schema
- [x] **Step 4**: Run test to verify it passes
- [x] **Step 5**: Add v2 backward-compat test

### Task 5: Create rdd-planner SKILL.md wrapper

- [x] **Step 1**: Write failing bats test asserting manifest exists
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Write minimal SKILL.md
- [x] **Step 4**: Run test to verify it passes
- [x] **Step 5**: Verify discoverability

### Task 6: Create planner_handoff.py + schema

- [x] **Step 1**: Write failing test for write_planner_handoff
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Implement planner_handoff.py
- [x] **Step 4**: Create schema file
- [x] **Step 5**: Run test to verify it passes

### Task 7: Create _lib/builder_handoff.py + schema (per-change layout)

- [x] **Step 1**: Write failing test for per-change handoff
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Implement builder_handoff.py
- [x] **Step 4**: Create schema
- [x] **Step 5**: Run test to verify it passes

### Task 8: Create _lib/builder_deps.py (Phase 1.5)

- [x] **Step 1**: Write failing test for execution_mode decision
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Implement builder_deps.py
- [x] **Step 4**: Run test to verify it passes
- [x] **Step 5**: Run existing deps tests to verify reuse works

### Task 9: Create _lib/builder_retry.py (verifier verdict routing)

- [x] **Step 1**: Write failing test for verifier verdict routing
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Implement builder_retry.py
- [x] **Step 4**: Create schema
- [x] **Step 5**: Run test to verify it passes

### Task 10: Create _lib/builder_feedback_router.py (cross-stage feedback)

- [x] **Step 1**: Write failing test for feedback routing
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Implement builder_feedback_router.py
- [x] **Step 4**: Run test to verify it passes
- [x] **Step 5**: Run full test suite to verify no regression

### Task 11: Create _lib/cli/builder_cmd.py

- [x] **Step 1**: Write failing test for CLI dispatch
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Implement builder_cmd.py
- [x] **Step 4**: Register in _lib/cli/__init__.py
- [x] **Step 5**: Run test to verify it passes

### Task 12: Create rdd-builder SKILL.md + 6 phase scripts

- [x] **Step 1**: Write failing bats test asserting manifest + scripts exist
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Write SKILL.md
- [x] **Step 4**: Create 6 phase scripts
- [x] **Step 5**: Run test to verify it passes

### Task 13: Update install.sh + INSTALL.md

- [x] **Step 1**: Write failing test for 4-stage symlink completeness
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Modify install.sh
- [x] **Step 4**: Update skills/INSTALL.md
- [x] **Step 5**: Run test to verify it passes

### Task 14: rddf-session stage mapping

- [x] **Step 1**: Write failing test for stage intent mapping
- [x] **Step 2**: Run test to verify it fails
- [x] **Step 3**: Implement stage mapping in session manager
- [x] **Step 4**: Run test to verify it passes
- [x] **Step 5**: Run existing rddf-session tests

### Task 15: Write ADR-0043

- [x] **Step 1**: Write ADR template
- [x] **Step 2**: Verify ADR numbering
- [x] **Step 3**: Update docs/adr/README.md
- [x] **Step 4**: Run ADR validation if exists
- [x] **Step 5**: Defer commit

### Task 16: Run full regression gate

- [x] **Step 1**: Run Python unit tests
- [x] **Step 2**: Run bats integration tests
- [x] **Step 3**: Run full regression gate (`./test.sh --full --regression`)
- [x] **Step 4**: Verify AC coverage
- [x] **Step 5**: Final review

### Task 17: Demo run

- [x] **Step 1**: Setup demo project
- [x] **Step 2**: Run rdd-arch
- [x] **Step 3**: Run rdd-planner
- [x] **Step 4**: Run rdd-builder full
- [x] **Step 5**: Append demo output to spec §9

### Task 18: Update proposal.md + tasks.md + design.md

- [x] **Step 1**: Fill proposal.md
- [x] **Step 2**: Fill tasks.md
- [x] **Step 3**: Fill design.md
- [x] **Step 4**: Validate via openspec CLI
- [x] **Step 5**: Defer commit

### Task 19: Final smoke test + handoff to execute skill

- [x] **Step 1**: Final verification
- [x] **Step 2**: Update tasks.md (mark Wave 1 done)
- [x] **Step 3**: Hand off to execute skill (already running)
- [x] **Step 4**: Update proposal-suggestions.md
- [x] **Step 5**: Single commit (per worktree discipline)