# add-objective-tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **TDD discipline (per AGENTS.md Guide-Ship 执行契约):** Every task follows the canonical 5-step structure — Write the failing test → Run test to verify it fails → Write minimal implementation → Run test to verify it passes → Defer commit. Detailed per-task steps live in `openspec/changes/add-objective-tracking/tasks.md`.

**Goal:** Add a third roadmap-tracking artifact — `objective` files in `.rddf/roadmap/objectives/*.md` — for cross-sprint complex targets that need planner-owned source-of-truth narrative (deferred objectives, multi-change goals). Bridges the gap between feature fragments (derived view, zero maintenance) and openspec changes (single-change scope).

**Architecture:** Three-layer minimal footprint:
1. **Schema layer** — `_lib/schemas/objective_schema.json` (v1, 9 frontmatter fields, kind enum 5, N/A format rule)
2. **Python data layer** — `_lib/objective.py` (~200 LOC) — parser + validator + grace helper
3. **CLI layer** — `_lib/cli/objective_cmd.py` (~250 LOC) + 7 bash wrappers (`skills/roadmap/scripts/objective_*.sh`, ~30 LOC each, env-var pattern per Oracle C1)

**Tech Stack:** Python 3.11+ (stdlib only, no new deps), Bash 4+ (wrappers), JSON Schema (validation), bats-core (integration), pytest (unit).

**Single-writer contract:** Only rdd-planner writes objective files. `planner_stage_exit.sh` is the sole entry that refreshes AGENTS.md `<!-- AUTO-OBJECTIVES -->` sentinel. rdd-builder / rdd-verifier / rdd-arch do NOT touch objective files.

**PoC gate (per change ## Acceptance):** Both PoC objectives must exist + produce at least 1 sprint-review ledger row + 1 deps snapshot + 1 review_by date set.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/schemas/objective_schema.json` | JSON Schema v1: 9 required frontmatter fields, status enum (4), priority enum (3), kind enum (5), N/A format regex |
| `_lib/objective.py` | Public API: `parse_objective`, `validate_objective`, `derive_associations`, `grace_period_exceeded`. Stdlib only. |
| `_lib/cli/objective_cmd.py` | CLI handlers: cmd_list_objectives / cmd_show_objective / cmd_add_objective / cmd_revise_objective / cmd_archive_objective / cmd_deps_objective / cmd_snapshot_objective |
| `_lib/cli/__init__.py` | Register 7 routes in `_ROUTES` dict (1 line each) |
| `skills/roadmap/scripts/objective_list.sh` | Bash wrapper: list-objectives (env-var PROJECT_ROOT) |
| `skills/roadmap/scripts/objective_show.sh` | Bash wrapper: show-objective |
| `skills/roadmap/scripts/objective_add.sh` | Bash wrapper: add-objective (skeleton generation) |
| `skills/roadmap/scripts/objective_revise.sh` | Bash wrapper: revise-objective (interactive) |
| `skills/roadmap/scripts/objective_archive.sh` | Bash wrapper: archive-objective (move to archive/) |
| `skills/roadmap/scripts/objective_deps.sh` | Bash wrapper: deps-objective (calls `rddf deps`) |
| `skills/roadmap/scripts/objective_snapshot.sh` | Bash wrapper: snapshot-objective (writes §9.5 dated snapshot) |
| `skills/roadmap/SKILL.md` | Add "objective tracking" concept section + 7 CLI subcommand list |
| `skills/rdd-planner/scripts/planner_objective_revise.sh` | Interactive revise entrypoint under rdd-planner owns |
| `skills/rdd-planner/scripts/planner_stage_exit.sh` | Append `<!-- AUTO-OBJECTIVES -->` refresh (after existing AUTO-INDEX refresh) |
| `skills/rdd-planner/SKILL.md` | Add objectives governance + feature-vs-objective decision rules |
| `skills/rdd-doctor/scripts/checks/objective_lifecycle_check.py` | Lifecycle doctor: review_by grace + status consistency |
| `skills/rdd-doctor/scripts/checks/objective_structure_check.py` | Structure doctor: frontmatter + sections + kind enum + N/A format |
| `skills/rdd-doctor/scripts/doctor.sh` | Register 2 new categories in check dispatcher |
| `skills/rdd-doctor/scripts/checks/doctor_main.py` | Add 2 new category names |

### Documentation

| File | Responsibility |
|---|---|
| `docs/adr/ADR-NNNN-objective-tracking.md` | Architecture decision. Status: 已采纳. Includes 4-artifact distinction matrix + role boundary (per ADR-0028) + Oracle 2-round references |
| `AGENTS.md` | Add "Objective 工件" section: feature-vs-objective decision table + 5 ledger kinds + N/A format constraint |
| `README.md` | Add objective-tracking row in skill list |
| `.rddf/roadmap/objectives/objective-bypass-audit-hub-governance.md` | PoC #1 (deferred) — validates §9.2 + N/A + cross-repo snapshot |
| `.rddf/roadmap/objectives/objective-onboard-new-skill.md` | PoC #2 (active) — validates §11 ledger + §10 candidates |

### Tests

| File | Coverage |
|---|---|
| `tests/unit/test_objective_schema.py` | ≥10 tests: 9 required fields, status enum, priority enum, kind enum, N/A format, manual_deps array |
| `tests/unit/test_objective_parser.py` | ≥6 tests: parse happy / missing frontmatter / missing section / optional section / N/A detection / derivation |
| `tests/integration/test_objective_lifecycle.bats` | ≥4 tests: list, show, archive, grace warning |
| `tests/integration/test_objective_structure.bats` | ≥4 tests: doctor structure check (valid/invalid objective file), kind violation, N/A pattern |
| `tests/integration/test_rdd_planner_objective.bats` | ≥3 tests: stage_exit refreshes AUTO-OBJECTIVES, list shows PoC files, revise appends ledger row |

---

## Tasks (TDD red→green)

See `openspec/changes/add-objective-tracking/tasks.md` for detailed TDD task breakdown (7 tasks). Summary:

| Task | Scope | LOC |
|------|-------|-----|
| 1 | Schema v1 + `_lib/objective.py` parser/validator | ~280 |
| 2 | CLI handlers + bash wrappers + route registration | ~500 |
| 3 | Doctor checks (lifecycle + structure) | ~120 |
| 4 | rdd-planner integration (AUTO-OBJECTIVES sentinel + revise hook) | ~170 |
| 5 | PoC objective files (bypass-audit-hub-governance deferred + onboard-new-skill active) | ~100 |
| 6 | ADR + AGENTS.md + README | ~190 |
| 7 | Final regression + archive prep | ~50 |

**Total**: ~1410 LOC production + 880 LOC tests = ~2300 LOC new.

---

## Execution

This plan follows the standard TDD 5-step structure per AGENTS.md "Guide-Ship 执行契约":
1. Write failing tests (red)
2. Verify they fail
3. Implement minimal passing code (green)
4. Verify tests pass
5. Commit + update tasks.md

Each task in `tasks.md` follows this pattern with concrete file paths, test counts, and expected outputs.

**Worktree mode**: This change has parallel risk (touching `_lib/`, `skills/roadmap/`, `skills/rdd-planner/`, `skills/rdd-doctor/`, `docs/adr/`), so will use worktree isolation per rdd-builder auto-detection logic.

**Commit discipline**: Per AGENTS.md "Worktree Commit Flow":
- During P2 execute: do NOT commit per task (follow existing convention)
- After all tasks done: 1 atomic commit in worktree with conventional commit message
- After archive: openspec archive moves files, rdd-builder writes archive auto-commit

---

## Verification (per change ## Acceptance)

Before marking this change complete:

- [ ] All 7 tasks in `tasks.md` checked off
- [ ] `./test.sh --full --regression` shows zero new failures (baseline + new tests all green)
- [ ] `openspec validate add-objective-tracking --strict` exits 0
- [ ] `bash skills/rdd-doctor/scripts/doctor.sh` shows zero CRITICAL across 13 categories (11 existing + 2 new)
- [ ] Both PoC objectives exist + produce ≥1 sprint-review ledger row + ≥1 deps snapshot + ≥1 review_by set
- [ ] AGENTS.md AUTO-OBJECTIVES segment populated after `planner_stage_exit.sh` run
- [ ] `rddf roadmap list-objectives` shows both PoC objectives with correct status/priority

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Planner single-gate erosion (builder/executor writes objective files) | Enforced via test: `test_lifecycle_check_rejects_unauthorized_writes` (hash check on `_lib/objective.py` + bash wrappers) |
| §9.5 snapshot staleness | Time stamp + regenerate command mandatory in format; doctor warns on snapshots >30d old (deferred to v0.2) |
| N/A pattern abuse (planner writes "N/A — TODO" instead of real content) | Doctor regex enforces `N/A — .+` (≥1 char reason after em-dash) |
| AUTO-OBJECTIVES segment grows unbounded | v0.1 limits to summary table; v0.2 may add aggregate view (per objective) |
| PoC objectives left in active state after change archive | Tasks.md Step 7 explicitly verifies both PoCs are valid + PoC #1 can stay `deferred` (real deferral) |
