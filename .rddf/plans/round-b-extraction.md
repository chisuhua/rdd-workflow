# Round B: Inline Bash Extraction Plan (Round B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract ~480 lines of inline bash from 4 skill files (`guide-arch.md`, `guide-plan.md`, `status.md`, `execute.md`) into `_lib/` helpers, following the established pattern (bash wrapper + optional Python helper + bats/pytest tests).

**Architecture:** Each task follows the Round A pattern: thin bash wrapper in `_lib/` with optional Python helper. Each helper has single public function. Tests lock the contract. Bug fixes from review loops preserve correctness.

**Tech Stack:** bash (wrappers), Python 3.11+ (for non-trivial helpers), bats-core (integration), pytest (unit)

---

## Tasks (10 total, prioritized by impact)

| # | Skill | Lines | Purpose | Helper | Tests |
|---|-------|-------|---------|--------|-------|
| 1 | guide-arch.md L436-L492 | 55 | Gap analysis generator | `arch_gap_analysis.sh` | 8 bats |
| 2 | guide-arch.md L668-L705 | 36 | arch-done dual gate | `arch_done_gate.sh` | 6 bats |
| 3 | guide-plan.md L527-L564 | 36 | Phase 3 deps-candidates generator | `plan_deps_candidates.sh` | 6 bats |
| 4 | guide-plan.md L287-L337 | 49 | Queue viz (delegates to iteration) | `plan_queue_overview.sh` | 6 bats |
| 5 | guide-plan.md L341-L373 | 31 | Feature progress view (delegates to iteration) | `plan_feature_progress.sh` | 5 bats |
| 6 | status.md L134-L178 | 43 | render_status() Mode A | `status_render_mode_a.sh` | 6 bats |
| 7 | execute.md L465-L506 | 40 | tasks.md writeback (awk) | `tasks_writeback.sh` | 6 bats |
| 8 | execute.md L406-L453 | 45 | Roadmap progress writer (SECURITY SMELL) | `update_roadmap_progress.{sh,py,env.py}` | 6 unit + 6 bats |
| 9 | execute.md L301-L388 | 86 | Step 7 report + iteration sync + scan | `execute_step7_report.{sh,py,env.py}` | 6 unit + 8 bats |
| 10 | guide-arch.md L828-L859 | 30 | arch-quality-report invoker | `arch_quality_report.sh` (mostly thin wrapper) | 4 bats |

**Total**: ~451 lines extracted, 11 new helpers, ~80+ new tests.

**Priority order** (by ROI):
1. **Task 8 (SECURITY)**: Roadmap progress writer has bash `$VAR` interpolation in Python heredoc (Oracle C1 risk). MUST fix.
2. **Tasks 1-7**: Standard extractions, follow Round A pattern.
3. **Task 10**: Thin wrapper, low priority.
4. **Tasks 4, 5**: Mostly already delegate to iteration module, low priority.

---

## Task 1: guide-arch.md gap analysis generator (L436-L492, 55 lines)

**Problem:** guide-arch.md L436-L492 (~55 lines) is a bash code block that generates gap analysis documents using a heredoc with placeholders for change name, slug, etc.

**Files:**
- Create: `skills/_lib/arch_gap_analysis.sh` — bash wrapper exposing `generate_gap_analysis()`
- Modify: `skills/guide-arch.md` (remove L436-L492 inline block)
- Test: `tests/integration/test_arch_gap_analysis_extraction.bats` (8 tests)

**Helper signature:**
```bash
# skills/_lib/arch_gap_analysis.sh
# generate_gap_analysis <name> <slug> — writes docs/architecture/<slug>-gap-analysis.md
generate_gap_analysis() {
  local NAME="$1" SLUG="$2"
  local PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  mkdir -p "$PROJECT_ROOT/docs/architecture"
  cat > "$PROJECT_ROOT/docs/architecture/${SLUG}-gap-analysis.md" <<EOF
# Gap Analysis: ${NAME}
...
EOF
}
```

- [ ] Step 1: Write failing bats tests (8 tests)
  - Helper exists with `generate_gap_analysis` function
  - guide-arch.md L436-L492 inline block removed
  - guide-arch.md invokes helper via `source`
  - Helper creates file in `docs/architecture/<slug>-gap-analysis.md`
  - File contains expected sections (e.g., "差距分析:", "建议:")
  - Honors `PROJECT_ROOT` env var
  - mkdir-p before write
  - Handles existing file gracefully (overwrites or errors)

- [ ] Step 2: Implement helper
  - Read L436-L492 inline block to capture exact content
  - Extract heredoc content
  - Replace bash interpolation with `cat <<EOF` (preserved)
  - Add `mkdir -p` before write
  - Add `chmod +x` script

- [ ] Step 3: Run tests GREEN
  - `bats tests/integration/test_arch_gap_analysis_extraction.bats` → 8/8 PASS

- [ ] Step 4: Migrate guide-arch.md (remove L436-L492)
  - Replace with: `source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/arch_gap_analysis.sh" && generate_gap_analysis "$NAME" "$SLUG"`

- [ ] Step 5: Full regression
  - `python3 -m pytest tests/ -q --tb=line && bats tests/integration/test_arch_gap_analysis_extraction.bats`

- [ ] Step 6: Commit
  - `git add skills/_lib/arch_gap_analysis.sh skills/guide-arch.md tests/integration/test_arch_gap_analysis_extraction.bats`
  - Subject: `refactor(arch): extract gap analysis generator to _lib/arch_gap_analysis.sh`

---

## Task 2: guide-arch.md arch-done dual gate (L668-L705, 36 lines)

**Problem:** arch-done phase validates ADR count >= 1 AND roadmap.md exists.

**Files:**
- Create: `skills/_lib/arch_done_gate.sh` — bash wrapper exposing `check_arch_done_gate()`
- Modify: `skills/guide-arch.md` (remove L668-L705)
- Test: `tests/integration/test_arch_done_gate_extraction.bats` (6 tests)

**Helper signature:**
```bash
# skills/_lib/arch_done_gate.sh
# check_arch_done_gate: Returns 0 if ADR count >= 1 AND roadmap exists, else 1
check_arch_done_gate() {
  local PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  # ... ADR count + roadmap existence checks ...
}
```

- [ ] Step 1: Write failing bats tests (6 tests)
  - Helper exists
  - Inline block removed
  - Helper invoked
  - Passes when ADRs exist + roadmap present
  - Fails when no ADRs
  - Fails when roadmap missing

- [ ] Step 2: Implement helper
  - Use `local ADR_COUNT` + `local ROADMAP_EXISTS`
  - Return 1 on failure, 0 on success
  - Use `${ROADMAP_PATH:-roadmap.md}` from handoff

- [ ] Step 3: Run tests GREEN
- [ ] Step 4: Migrate guide-arch.md
- [ ] Step 5: Full regression
- [ ] Step 6: Commit

---

## Task 3: guide-plan.md deps-candidates generator (L527-L564, 36 lines)

**Problem:** Phase 3 generates `.rddf/state/.deps-candidates.json` (list of changes to analyze) then invokes `skill_use("deps")`.

**Files:**
- Create: `skills/_lib/plan_deps_candidates.sh` — bash wrapper
- Modify: `skills/guide-plan.md` (remove L527-L564)
- Test: 6 bats tests

**Helper signature:**
```bash
# skills/_lib/plan_deps_candidates.sh
# generate_deps_candidates: Builds .deps-candidates.json from active changes
generate_deps_candidates() {
  # Lists changes in openspec/changes/*/ (excluding archive/)
  # Writes JSON list to .rddf/state/.deps-candidates.json
}
```

- [ ] Steps 1-6: Same pattern

---

## Task 4: guide-plan.md queue overview (L287-L337, 49 lines)

**Problem:** Shows planned / blocked / ready-for-ship changes via iteration module.

**Files:**
- Create: `skills/_lib/plan_queue_overview.sh` — bash wrapper
- Modify: `skills/guide-plan.md`
- Test: 6 bats tests

**Helper signature:**
```bash
# skills/_lib/plan_queue_overview.sh
# show_queue_overview: Prints planned/blocked/ready-for-ship counts via iteration module
show_queue_overview() {
  # Delegates to skills._lib.iteration module
}
```

- [ ] Steps 1-6: Same pattern

---

## Task 5: guide-plan.md feature progress view (L341-L373, 31 lines)

**Problem:** Shows per-feature progress via iteration.feature_progress.

**Files:**
- Create: `skills/_lib/plan_feature_progress.sh` — bash wrapper
- Modify: `skills/guide-plan.md`
- Test: 5 bats tests

- [ ] Steps 1-6: Same pattern

---

## Task 6: status.md render_status() Mode A (L134-L178, 43 lines)

**Problem:** Mode A renders iteration.json status with filesystem fallback.

**Files:**
- Create: `skills/_lib/status_render_mode_a.sh` — bash wrapper exposing `render_status_mode_a()`
- Modify: `skills/status.md` (remove L134-L178)
- Test: 6 bats tests

- [ ] Steps 1-6: Same pattern

---

## Task 7: execute.md tasks.md writeback (L465-L506, 40 lines)

**Problem:** Two awk-based methods for marking tasks done in tasks.md.

**Files:**
- Create: `skills/_lib/tasks_writeback.sh` — bash wrapper
- Modify: `skills/execute.md`
- Test: 6 bats tests

**Helper signature:**
```bash
# skills/_lib/tasks_writeback.sh
# mark_task_done <tasks_file> <task_id>: Marks the Nth checkbox as [x]
# Uses awk with index() for precise match OR bulk gsub as fallback
```

- [ ] Steps 1-6: Same pattern

---

## Task 8: execute.md roadmap progress writer (L406-L453, 45 lines) — **SECURITY PRIORITY**

**Problem:** Bash code uses `python3 -c "..."` with `$CHANGE_NAME` interpolated into the Python source (Oracle C1 risk). This is the security smell flagged in the explore agent's report.

**Files:**
- Create: `skills/_lib/update_roadmap_progress.py` — Python function
- Create: `skills/_lib/update_roadmap_progress_env.py` — env-var launcher
- Create: `skills/_lib/update_roadmap_progress.sh` — bash wrapper
- Modify: `skills/execute.md` (remove L406-L453)
- Test: `tests/unit/test_update_roadmap_progress.py` (6 tests)
- Test: `tests/integration/test_update_roadmap_progress_extraction.bats` (6 tests)

**Helper signature:**
```python
# skills/_lib/update_roadmap_progress.py
def update_roadmap_progress(project_root: str, change_name: str) -> dict:
    """Read roadmap-meta.yaml, update change's progress, write back."""
    # Read YAML (use simple key=value parsing or PyYAML if available)
    # Update or insert change entry
    # Write back
```

- [ ] Step 1: Write failing Python unit tests (6 tests)
  - `test_basic_update`
  - `test_yaml_round_trip`
  - `test_append_new_change`
  - `test_nonexistent_file_creates`
  - `test_preserves_other_changes`
  - `test_yaml_parsing_no_pyyaml`

- [ ] Step 2: Write failing bats tests (6 tests)
  - Helper exists + function exported
  - Inline block removed
  - Helper invoked
  - Oracle C1: NO bash $VAR inside python heredoc
  - Reads + writes roadmap-meta.yaml correctly
  - Updates only target change (preserves others)

- [ ] Step 3: Implement Python helper
  - Use env-var passing ONLY (no bash string interpolation)
  - Support both PyYAML (if installed) and simple text parser
  - Same pattern as `plan_done_gate.py`

- [ ] Step 4: Implement bash wrapper
- [ ] Step 5: Run all tests → all PASS
- [ ] Step 6: Migrate execute.md
- [ ] Step 7: Commit

---

## Task 9: execute.md Step 7 report (L301-L388, 86 lines)

**Problem:** Final report after execution: progress summary, iteration.json sync, other-worktree discovery.

**Files:**
- Create: `skills/_lib/execute_step7_report.py` — Python function
- Create: `skills/_lib/execute_step7_report_env.py` — launcher
- Create: `skills/_lib/execute_step7_report.sh` — bash wrapper
- Modify: `skills/execute.md`
- Test: 6 unit + 8 bats tests

- [ ] Steps 1-7: Same pattern as Task 8

---

## Task 10: guide-arch.md arch-quality-report invoker (L828-L859, 30 lines)

**Problem:** Mostly a thin wrapper around `arch_quality_gate.py::ArchQualityReport.verify()`.

**Files:**
- Create: `skills/_lib/arch_quality_report.sh` — bash wrapper exposing `run_arch_quality_report()`
- Modify: `skills/guide-arch.md`
- Test: 4 bats tests

**Helper signature:**
```bash
# skills/_lib/arch_quality_report.sh
# run_arch_quality_report: Invokes arch_quality_gate.py::ArchQualityReport.verify() and writes .arch-quality-report.json
run_arch_quality_report() {
  python3 -m skills._lib.arch_quality_gate ...
}
```

- [ ] Steps 1-6: Same pattern

---

## Execution

**Approach**: Subagent-driven (per Round A workflow). Each task: implementer → spec review → code quality review → fix → re-review. Continue without pause unless BLOCKED.

**Critical path**: Task 8 (security) → Tasks 1-7 (standard) → Tasks 9-10 (Python helpers).

**Final phase**: Full regression, AGENTS.md update, cleanup.

---

Plan complete. Two execution options:
1. **Subagent-Driven (recommended)** — continue Round A pattern, dispatch fresh subagent per task
2. **Inline Execution** — execute in this session

Round A used Option 1 with great success. Recommend continuing with Option 1.

Which approach?