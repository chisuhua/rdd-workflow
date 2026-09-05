## Tasks

### Task 1: Setup worktree + OpenSpec change skeleton

- [x] **Step 1**: Branch + worktree created (`openspec/v4-stage-merge-wave1` branch, `.rddf/wt/v4-stage-merge-wave1/` directory)
- [x] **Step 2**: OpenSpec change directory created with proposal.md
- [x] **Step 3**: Spec file accessible from worktree (1003 lines verified)
- [x] **Step 4**: Plan file accessible from worktree (3329 lines verified)
- [x] **Step 5**: Defer commit (per execute.md convention)

### Task 2: Slim rdd-arch — remove roadmap fields from arch-handoff writer

- [ ] **Step 1**: Write failing test for writer omitting removed fields
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Modify writer to omit roadmap fields
- [ ] **Step 4**: Run test to verify it passes
- [ ] **Step 5**: Run all arch-handoff tests; verify regression gate

### Task 3: Remove `_check_roadmap_defined` from gate.py + arch_done registration

- [ ] **Step 1**: Write failing test asserting function absence
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Remove `_check_roadmap_defined` from gate.py
- [ ] **Step 4**: Update existing test references
- [ ] **Step 5**: Run all related tests; verify pass

### Task 4: Bump arch-handoff schema to v3 + extend test coverage

- [ ] **Step 1**: Write failing test for v3 contract
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Update schema
- [ ] **Step 4**: Run test to verify it passes
- [ ] **Step 5**: Add v2 backward-compat test

### Task 5: Create rdd-planner SKILL.md wrapper

- [ ] **Step 1**: Write failing bats test asserting manifest exists
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Write minimal SKILL.md
- [ ] **Step 4**: Run test to verify it passes
- [ ] **Step 5**: Verify discoverability

### Task 6: Create planner_handoff.py + schema

- [ ] **Step 1**: Write failing test for write_planner_handoff
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Implement planner_handoff.py
- [ ] **Step 4**: Create schema file
- [ ] **Step 5**: Run test to verify it passes

### Task 7: Create _lib/builder_handoff.py + schema (per-change layout)

- [ ] **Step 1**: Write failing test for per-change handoff
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Implement builder_handoff.py
- [ ] **Step 4**: Create schema
- [ ] **Step 5**: Run test to verify it passes

### Task 8: Create _lib/builder_deps.py (Phase 1.5)

- [ ] **Step 1**: Write failing test for execution_mode decision
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Implement builder_deps.py
- [ ] **Step 4**: Run test to verify it passes
- [ ] **Step 5**: Run existing deps tests to verify reuse works

### Task 9: Create _lib/builder_retry.py (verifier verdict routing)

- [ ] **Step 1**: Write failing test for verifier verdict routing
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Implement builder_retry.py
- [ ] **Step 4**: Create schema
- [ ] **Step 5**: Run test to verify it passes

### Task 10: Create _lib/builder_feedback_router.py (cross-stage feedback)

- [ ] **Step 1**: Write failing test for feedback routing
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Implement builder_feedback_router.py
- [ ] **Step 4**: Run test to verify it passes
- [ ] **Step 5**: Run full test suite to verify no regression

### Task 11: Create _lib/cli/builder_cmd.py

- [ ] **Step 1**: Write failing test for CLI dispatch
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Implement builder_cmd.py
- [ ] **Step 4**: Register in _lib/cli/__init__.py
- [ ] **Step 5**: Run test to verify it passes

### Task 12: Create rdd-builder SKILL.md + 6 phase scripts

- [ ] **Step 1**: Write failing bats test asserting manifest + scripts exist
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Write SKILL.md
- [ ] **Step 4**: Create 6 phase scripts
- [ ] **Step 5**: Run test to verify it passes

### Task 13: Update install.sh + INSTALL.md

- [ ] **Step 1**: Write failing test for 4-stage symlink completeness
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Modify install.sh
- [ ] **Step 4**: Update skills/INSTALL.md
- [ ] **Step 5**: Run test to verify it passes

### Task 14: rddf-session stage mapping

- [ ] **Step 1**: Write failing test for stage intent mapping
- [ ] **Step 2**: Run test to verify it fails
- [ ] **Step 3**: Implement stage mapping in session manager
- [ ] **Step 4**: Run test to verify it passes
- [ ] **Step 5**: Run existing rddf-session tests

### Task 15: Write ADR-0043

- [ ] **Step 1**: Write ADR template
- [ ] **Step 2**: Verify ADR numbering
- [ ] **Step 3**: Update docs/adr/README.md
- [ ] **Step 4**: Run ADR validation if exists
- [ ] **Step 5**: Defer commit

### Task 16: Run full regression gate

- [ ] **Step 1**: Run Python unit tests
- [ ] **Step 2**: Run bats integration tests
- [ ] **Step 3**: Run full regression gate (`./test.sh --full --regression`)
- [ ] **Step 4**: Verify AC coverage
- [ ] **Step 5**: Final review

### Task 17: Demo run

- [ ] **Step 1**: Setup demo project
- [ ] **Step 2**: Run rdd-arch
- [ ] **Step 3**: Run rdd-planner
- [ ] **Step 4**: Run rdd-builder full
- [ ] **Step 5**: Append demo output to spec §9

### Task 18: Update proposal.md + tasks.md + design.md

- [ ] **Step 1**: Fill proposal.md
- [ ] **Step 2**: Fill tasks.md
- [ ] **Step 3**: Fill design.md
- [ ] **Step 4**: Validate via openspec CLI
- [ ] **Step 5**: Defer commit

### Task 19: Final smoke test + handoff to execute skill

- [ ] **Step 1**: Final verification
- [ ] **Step 2**: Update tasks.md (mark Wave 1 done)
- [ ] **Step 3**: Hand off to execute skill (already running)
- [ ] **Step 4**: Update proposal-suggestions.md
- [ ] **Step 5**: Single commit (per worktree discipline)