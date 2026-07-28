# fix-skill-dual-root-paths — Tasks

## Phase 1: Infrastructure

- [x] 1.1 Create `skills/_lib/skill_root.sh` with `resolve_rdd_skill_dir()` and `resolve_rdd_lib_dir()` functions
- [x] 1.2 Modify `install.sh` — add `_lib` symlink in `install_global_symlinks()`
- [x] 1.3 Run `install.sh --global` to update global installation with `_lib` symlink
- [x] 1.4 Verify: `ls ~/.agents/skills/_lib/skill_root.sh` exists

## Phase 2: SKILL.md Updates (8 files)

- [x] 2.1 `guide-plan/SKILL.md` — replace 10 `source "$PROJECT_ROOT/skills/..."` with resolved paths
- [x] 2.2 `guide-ship/SKILL.md` — replace 21 `source "$PROJECT_ROOT/skills/..."` with resolved paths
- [x] 2.3 `deps/SKILL.md` — replace 2 `source "$PROJECT_ROOT/skills/..."` with resolved paths
- [x] 2.4 `execute/SKILL.md` — replace 1 `source "$PROJECT_ROOT/skills/..."` with resolved paths
- [x] 2.5 `feature/SKILL.md` — replace 1 `source "$PROJECT_ROOT/skills/..."` with resolved paths
- [x] 2.6 `propose/SKILL.md` — replace 2 `source "$PROJECT_ROOT/skills/..."` with resolved paths
- [x] 2.7 `roadmap/SKILL.md` — replace 1 `source "$PROJECT_ROOT/skills/..."` with resolved paths
- [x] 2.8 `status/SKILL.md` — replace 2 `source "$PROJECT_ROOT/skills/..."` with resolved paths
- [x] 2.9 Verify: `grep -r 'PROJECT_ROOT/skills/' skills/*/SKILL.md` returns zero matches

## Phase 3: Shell Scripts Updates (5 files)

- [x] 3.1 `guide-arch/scripts/arch_done_gate.sh` — replace `_lib` reference with `resolve_rdd_lib_dir()`
- [x] 3.2 `guide-arch/scripts/arch_env_check.sh` — replace `_lib` reference with `resolve_rdd_lib_dir()`
- [x] 3.3 `guide-arch/scripts/write_arch_handoff.sh` — replace `_lib` reference with `resolve_rdd_lib_dir()`
- [x] 3.4 `guide-plan/scripts/plan_done_gate.sh` — replace cross-skill references with `resolve_rdd_skill_dir()`
- [x] 3.5 `guide-plan/scripts/plan_intake.sh` — replace `_lib` reference with `resolve_rdd_lib_dir()`
- [x] 3.6 Verify: `grep -r 'PROJECT_ROOT/skills/' skills/*/scripts/` returns zero matches

## Phase 4: Verification

- [x] 4.1 rdd-workflow project-local verification: run `skill_use("guide-plan")` in rdd-workflow project
- [x] 4.2 PTX-EMU global verification: run `skill_use("guide-plan")` in PTX-EMU project
- [x] 4.3 Regression check: all existing tests pass (`bats tests/`)
- [x] 4.4 Commit all changes
