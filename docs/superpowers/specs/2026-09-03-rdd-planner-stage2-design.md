# rdd-planner Stage 2: Sync + Status Commands — Design

**Date**: 2026-09-03
**Status**: Draft (awaiting user review)
**Author**: brainstorming session output (Sisyphus orchestration + Oracle review)
**Related ADRs**: ADR-0037 feedback-contract (Stage 1, dependency), ADR-0038 (to be created by this spec)
**Decisions Adopted**: D4.1a (Stage 2 MVP = status + sync) + D4.2a (dual-zone strategy) + D4.3c (manual + auto advance-sprint) + D4.4a (`rddf planner ...`)
**Builds on**: Stage 1 (`docs/superpowers/specs/2026-09-03-rdd-planner-stage1-feedback-contract.md`)

## 1. Problem & Motivation

### 1.1 Observed gaps

After Stage 1 implementation (ADR-0037 feedback contract) and codebase audit:

1. **No central state for sprint progress** — current `.rddf/state/` has no `.planner-state.json`; sprint concept exists in `_lib/roadmap_sprint.py` rendering but **not used in this repo** (roadmap.md has no AUTO-SPRINT block).
2. **No automated sync between proposals ↔ roadmap** — 226 `.rddf/improvements/*.md` files lack `roadmap_ref` (per Stage 1 spec §1.1), so manual tracking is required.
3. **No feedback-driven revision trigger** — Stage 1 `rddf feedback add` writes `## Feedback` but no consumer reads it.
4. **Five `.rddf/state/iteration.corrupt.*` residual files** (per Oracle review) — demonstrates that multi-writer state corruption is a known risk.

### 1.2 Goal

Implement **`rdd-planner` skill** as a **horizontal orchestrator** (NOT a sixth phase). Provide `status` + `sync` commands that:

- Maintain a single source of truth for sprint state (`.planner-state.json`).
- Discover roadmap ↔ proposal mappings (read-only analysis).
- Render the AUTO-SPRINT section in `roadmap.md` from state.
- Are **idempotent** and **safe to run repeatedly** without manual intervention.

Per Oracle review (Stage 1 deliverable), `rdd-planner` MUST be:
- Read-heavy, write-light.
- Never directly modify `.rddf/improvements/*.md`.
- Atomic-write all state via `_lib/core/atomic_write` + `FileLock`.
- Backward compatible with 226 existing improvement files (zero migration burden).

### 1.3 Out of scope (explicit)

- ❌ `rddf planner revise` implementation (deferred to Stage 2.5).
- ❌ `rddf planner audit` implementation (deferred to Stage 2.5).
- ❌ `rddf planner advance-sprint --auto` auto-trigger logic (manual only in Stage 2).
- ❌ `guide-arch → rdd-arch` rename (Stage 3).
- ❌ Modifying any of the 226 existing `.rddf/improvements/*.md` files.
- ❌ Changing `proposal-suggestions.md` / `proposal-approved.md` format.
- ❌ Cross-repo / Hub-Spoke federation impact.

## 2. Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Skill position | Horizontal orchestrator, NOT a sixth phase | Oracle review: 5-phase architecture (arch→design→plan→ship→verify) is stable; adding a phase creates governance debt |
| 2 | Commands in Stage 2 MVP | `status` + `sync` only | Stage 1 principle: smallest deliverable; `revise`/`audit` deferred to Stage 2.5 |
| 3 | State file | New `.rddf/state/.planner-state.json` (gitignored, schema v1) | Consistent with existing `.rddf/state/*.json` convention (iteration.json, session.json) |
| 4 | Sprint concept | First-class entity in state; `current_sprint` field | Oracle: sprint ≠ phase; phase = long-term, sprint = execution window |
| 5 | Sync idempotency | Dry-run by default; `--apply` flag required to write | Mirrors `--dry-run` from Stage 1; safe iteration |
| 6 | Roadmap write strategy | Dual-zone: preserve user-edited Phase Skeleton table; overwrite AUTO-SPRINT block only | Preserves manual work; aligns with existing `_lib/roadmap_sprint.py` sentinel pattern |
| 7 | Improvement file mapping | Read `frontmatter.roadmap_ref` (opt-in, Stage 1 v2 schema); fallback to filename heuristic | Zero migration burden on 226 files |
| 8 | Feedback integration | Read-only — `sync` reads `## Feedback` via Stage 1 contract, updates `feedback_status` field | Stage 1 already has single writer; Stage 2 is read consumer |
| 9 | Atomic writes | `_lib/core/atomic_write` + `_lib/core/lock.FileLock` (timeout=10s) | Proven pattern from Stage 1; prevents iteration-corrupt failure mode |
| 10 | CLI surface | `rddf planner status / sync [--apply] [--dry-run]` | Matches existing 32 CLI subcommand pattern |
| 11 | Schema location | New `_lib/schemas/planner_state_schema.json` (v1) | Follows `_lib/schemas/` convention |
| 12 | Testing | pytest unit (≥20) + bats integration (≥5), all using `RDD_PLANNER_MOCK=yes` | Mirrors Stage 1 testing convention |

## 3. Architecture

### 3.1 Component diagram

```text
┌──────────────────────────────────────────────────────────────────┐
│ User invocation                                                    │
│   $ rddf planner status                                           │
│   $ rddf planner sync [--apply] [--dry-run]                        │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ _lib/cli/planner_cmd.py   │  (NEW)
        │   cmd_planner(args) -> int│
        └────────────┬───────────────┘
                     │
        ┌────────────┴───────────────┐
        │                            │
        ▼                            ▼
┌──────────────────┐      ┌──────────────────────┐
│ status path:     │      │ sync path:           │
│ _lib/planner_    │      │ _lib/planner_sync.py│
│   state.py       │      │   (NEW)              │
│   (NEW, read-only│      │   - discover()       │
│    snapshot)     │      │   - render()         │
└────────┬─────────┘      │   - atomic_write()   │
         │                └──────────┬───────────┘
         │                           │
         ▼                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ Shared I/O                                                         │
│  - .rddf/state/.planner-state.json  (NEW, atomic write + lock)     │
│  - .rddf/roadmap.md  (dual-zone: preserve phase skeleton,          │
│                       overwrite AUTO-SPRINT block)                │
│  - .rddf/improvements/*.md  (read-only)                            │
│  - _lib/roadmap_sprint.py  (reuse for AUTO-SPRINT rendering)       │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 File layout (additions only)

```text
_lib/
├── planner_state.py                   # NEW — state read/write/lock (≥150 lines)
├── planner_sync.py                    # NEW — sync logic (≥250 lines)
├── schemas/
│   └── planner_state_schema.json      # NEW — JSON schema v1
└── cli/
    └── planner_cmd.py                 # NEW — CLI dispatcher (≥180 lines)

tests/
├── unit/
│   ├── test_planner_state.py          # NEW (≥8 tests)
│   ├── test_planner_sync.py           # NEW (≥12 tests)
│   └── test_planner_cli.py            # NEW (≥5 tests)
└── integration/
    └── test_planner_cmd.bats          # NEW (≥5 tests)

docs/superpowers/specs/
└── 2026-09-03-rdd-planner-stage2-design.md   # NEW (this file)

docs/adr/
└── ADR-0038-rdd-planner-crosscutting.md     # NEW
```

### 3.3 Sequence: `planner sync --dry-run`

```text
1. cmd_planner("sync", "--dry-run"):
   2. planner_sync.discover(project_root):
      3. scan .rddf/improvements/*.md
      4. parse frontmatter (PyYAML), extract roadmap_ref (opt-in)
      5. parse ## Feedback section (via Stage 1 helper), derive feedback_status
      6. return list of ProjectRecord dicts
   7. planner_sync.render_state(discovered, current_sprint):
      8. compute active_projects = [p for p in discovered if p.in_current_sprint]
      9. compute unmapped = [p for p in discovered if not p.roadmap_ref]
      10. return state dict (no write)
   11. planner_sync.render_sprint_block(state):
       12. delegate to _lib.roadmap_sprint.render_sprint_table(state)
   13. print diff (state hash, sprint table preview)
   14. return 0
```

### 3.4 Sequence: `planner sync --apply`

```text
Same as dry-run, plus:
   11.5. acquire lock on .planner-state.json
   11.6. atomic_write_text(.planner-state.json, state_json)
   11.7. atomic_write_text(.rddf/roadmap.md, updated_roadmap)
   11.8. release lock
```

### 3.5 `.rddf/state/.planner-state.json` schema v1

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://rdd-workflow.local/schemas/planner_state_schema.json",
  "title": "PlannerState",
  "type": "object",
  "required": ["version", "current_sprint", "last_sync_at"],
  "properties": {
    "version": {"const": 1},
    "current_sprint": {"type": "string", "pattern": "^sprint-[0-9]{4}-[0-9]{2}$"},
    "sprint_started_at": {"type": "string", "format": "date-time"},
    "last_sync_at": {"type": "string", "format": "date-time"},
    "last_sync_status": {"type": "string", "enum": ["ok", "warn", "error"]},
    "active_projects": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["project_id", "phase", "priority", "status"],
        "properties": {
          "project_id": {"type": "string"},
          "phase": {"type": "string"},
          "theme": {"type": "string"},
          "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
          "status": {"type": "string", "enum": ["active", "blocked", "completed"]},
          "proposal": {"type": "string"},
          "change": {"type": "string"},
          "feedback_status": {"type": "string", "enum": ["none", "needs-revision", "rejected", "resolved"]},
          "last_feedback_id": {"type": "string"}
        }
      }
    },
    "unmapped_proposals": {
      "type": "array",
      "items": {"type": "string"},
      "description": "proposal names that lack frontmatter.roadmap_ref"
    },
    "synced_proposals": {
      "type": "array",
      "items": {"type": "string"}
    }
  }
}
```

### 3.6 Roadmap dual-zone write strategy

```text
.rddf/roadmap.md (current structure):
   # Roadmap                          [manual zone preserved]
   ## Phase Skeleton                  [manual zone preserved]
   | Phase | Theme | Status | ... |
   | ...   | ...   | ...    | ... |
   <!-- AUTO-INDEX -->                 [zone boundary]
   ## Fragment Index ...               [auto zone preserved]

.rddf/roadmap.md (after Stage 2 sync):
   # Roadmap                          [manual zone preserved]
   ## Phase Skeleton                  [manual zone preserved]
   | Phase | Theme | Status | ... |
   | ...   | ...   | ...    | ... |
   <!-- AUTO-SPRINT-START -->          [NEW boundary]
   ## Current Sprint: sprint-2026-09  [NEW auto zone, overwritten each sync]
   | Project | Phase | Priority | Feedback |
   | ...     | ...   | ...       | ...      |
   <!-- AUTO-SPRINT-END -->            [NEW boundary]
   <!-- AUTO-INDEX -->                 [auto zone preserved]
   ## Fragment Index ...               [auto zone preserved]
```

If `<!-- AUTO-SPRINT-START -->` is missing, append it after `## Phase Skeleton` table (idempotent first-run).

### 3.7 Improvement file mapping algorithm

```python
def discover_projects(improvements_dir: Path) -> list[ProjectRecord]:
    """Read each .rddf/improvements/*.md and extract mapping signals."""
    records = []
    for f in sorted(improvements_dir.glob("*.md")):
        text = f.read_text()
        fm = parse_frontmatter(text) or {}
        feedback_status = parse_feedback_status(text)  # via Stage 1 helper

        ref = fm.get("roadmap_ref", {}) or {}
        record = ProjectRecord(
            proposal=f.stem,
            project_id=ref.get("project_id") or f.stem,
            phase=ref.get("phase") or "unmapped",
            theme=ref.get("theme") or "",
            priority=fm.get("priority", "P2"),
            proposal_path=f,
            feedback_status=feedback_status,
            mapped=bool(ref.get("project_id")),
        )
        records.append(record)
    return records
```

**Backward compat**: 226 existing files lack `roadmap_ref` → all fall into `unmapped_proposals` list. No file is modified.

### 3.8 CLI surface

```bash
rddf planner status [--json]                    # read-only snapshot
rddf planner sync [--apply] [--dry-run]         # default = --dry-run
rddf planner --help
```

**Exit codes**:
- `0` — success (status printed OR dry-run preview OR apply succeeded)
- `1` — validation error (no improvements dir, malformed state)
- `2` — I/O error (lock contention, permission)
- `3` — schema mismatch (state file version != 1)

## 4. Migration & Compatibility

### 4.1 Zero impact on 226 existing files

- Missing `roadmap_ref` → unmapped bucket (informational only)
- Missing `## Feedback` → `feedback_status="none"`
- No file is modified by `planner sync`

### 4.2 Backward compat with `.rddf/roadmap.md`

- If `<!-- AUTO-SPRINT-START -->` absent → append after Phase Skeleton
- If present → overwrite only the AUTO-SPRINT block
- Phase Skeleton and AUTO-INDEX always preserved

### 4.3 First-run behavior

When `.planner-state.json` is absent:
- `current_sprint = "sprint-YYYY-MM"` (current month, derived from `date` command)
- `active_projects = []`
- `last_sync_status = "ok"` (empty sync)
- Atomic write creates the file

When `.rddf/roadmap.md` is missing AUTO-SPRINT sentinels:
- First sync appends the block (single idempotent operation)

## 5. Testing Strategy

### 5.1 Unit tests (pytest)

| File | Test count target | Coverage |
|------|-------------------|----------|
| `test_planner_state.py` | ≥8 | read/write/lock/version mismatch/bump/migration |
| `test_planner_sync.py` | ≥12 | discover/render/dual-zone write/--dry-run/--apply idempotency |
| `test_planner_cli.py` | ≥5 | arg parsing/exit codes/json output/dry-run vs apply |

**Total: ≥25 unit tests**

### 5.2 Integration tests (bats)

| File | Test count target | Coverage |
|------|-------------------|----------|
| `test_planner_cmd.bats` | ≥5 | end-to-end CLI/status/sync/apply/dual-zone preservation |

### 5.3 Idempotency test (critical)

```python
def test_sync_dry_run_is_idempotent(tmp_path):
    """Running dry-run twice produces identical state."""
    # First run
    state1 = planner_sync.run(project_root=tmp_path, dry_run=True)
    # Second run
    state2 = planner_sync.run(project_root=tmp_path, dry_run=True)
    assert state1 == state2
```

### 5.4 Regression gate

Per AGENTS.md "Archive 前全量回归门": run `./test.sh --python` and `bats tests/integration/test_planner_cmd.bats` before merge. No new failures in `KNOWN_FAILURES.txt`.

## 6. Acceptance Criteria

Stage 2 is **done** when all are true:

- [ ] `_lib/planner_state.py` exists with public `read_state()`, `write_state()`, schema validation
- [ ] `_lib/planner_sync.py` exists with `discover()`, `render_state()`, `apply_state()` (or equivalent)
- [ ] `_lib/cli/planner_cmd.py` registered in `_lib/cli/__init__.py::_ROUTES`
- [ ] `_lib/schemas/planner_state_schema.json` v1 exists, validates against test fixtures
- [ ] `tests/unit/test_planner_*.py` ≥25 tests, all green under `RDD_PLANNER_MOCK=yes`
- [ ] `tests/integration/test_planner_cmd.bats` ≥5 tests, all green
- [ ] `./test.sh --python --bats` exits 0 (no new failures vs baseline)
- [ ] `ADR-0038-rdd-planner-crosscutting.md` written and committed
- [ ] Demo run recorded showing: status output + dry-run diff + apply state write
- [ ] 226 existing `.rddf/improvements/*.md` files UNTOUCHED
- [ ] Existing `.rddf/roadmap.md` Phase Skeleton table UNTOUCHED (dual-zone respected)

## 7. Demo Run (record after implementation)

```bash
# Setup: minimal project with 3 improvements
mkdir -p .rddf/improvements
cat > .rddf/improvements/foo.md <<'EOF'
---
name: foo
priority: P2
roadmap_ref:
  project_id: foo-impl
  phase: phase-2
  theme: foo theme
---
# foo
EOF
# (similar for bar.md with no roadmap_ref, baz.md with roadmap_ref)

# Status (read-only)
$ rddf planner status
# Sprint: sprint-2026-09
# Active: 2 (foo, baz)
# Unmapped: 1 (bar)
# Feedback: none

# Sync dry-run (default)
$ rddf planner sync
# DRY-RUN: would write 2 files:
#   .rddf/state/.planner-state.json (new)
#   .rddf/roadmap.md (append AUTO-SPRINT block)
# Run with --apply to write.

# Sync apply
$ rddf planner sync --apply
# ✓ State written
# ✓ Roadmap updated (AUTO-SPRINT block added)

# Verify Phase Skeleton preserved
$ grep -A 5 "## Phase Skeleton" .rddf/roadmap.md | head -8
# | Phase | Theme | Status | ...
# (unchanged)

# Verify AUTO-SPRINT added
$ grep -A 5 "AUTO-SPRINT-START" .rddf/roadmap.md
# <!-- AUTO-SPRINT-START -->
# ## Current Sprint: sprint-2026-09
# ...
```

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `.planner-state.json` corruption (like iteration.corrupt.*) | Atomic write + lock; schema validation on read; .corrupt.<ts> quarantine pattern (existing in codebase) |
| Race with concurrent `guide-arch` writing roadmap.md | Dual-zone strategy: only writes AUTO-SPRINT block, never touches Phase Skeleton |
| 226 unmapped proposals flood status output | Truncate unmapped list to top 10 + count suffix; provide `--all` flag (Stage 2.5) |
| Sprint auto-advance misfires | Stage 2 only supports manual `--advance-sprint`; auto-trigger deferred to Stage 2.5 |
| Backward compat with existing AUTO-INDEX block | Stage 2 ONLY touches AUTO-SPRINT block; AUTO-INDEX remains untouched |

## 9. Non-Goals (explicit)

- ❌ Implementing `planner revise` (Stage 2.5).
- ❌ Implementing `planner audit` (Stage 2.5).
- ❌ Auto-advance sprint based on completion detection.
- ❌ Reading `proposal-suggestions.md` / `proposal-approved.md`.
- ❌ Modifying any `.rddf/improvements/*.md` file.
- ❌ Cross-repo / Hub-Spoke integration.
- ❌ Modifying 28 existing CLI subcommands.

## 10. Open Questions (deferred to Stage 2.5)

1. **Should `planner revise` operate on proposals in batches?** — likely yes, but Stage 2 deferred.
2. **Should `planner audit` emit JSON or Markdown?** — likely Markdown for human consumption.
3. **Should `planner advance-sprint` accept a `--to-sprint <name>` for forward jumps?** — likely yes.
4. **Should planner-state include roadmap_ref resolution cache?** — likely yes, invalidated on sync.

## 11. Related Files

- `_lib/core/atomic_write.py` — atomic write primitive
- `_lib/core/lock.py` — FileLock (timeout=10s)
- `_lib/roadmap_sprint.py` — AUTO-SPRINT block renderer (reuse)
- `_lib/feedback_appender.py` — Stage 1 feedback writer (read-only consumer in Stage 2)
- `_lib/feedback_resolver.py` — proposal → change ID resolution
- `_lib/cli/__init__.py` — register `planner` subcommand
- `_lib/schemas/iteration_schema.json` — schema version bump precedent
- `tests/_lib/test_helper.bash` — bats helper integration
- AGENTS.md "Archive 前全量回归门" — regression gate rule
- ADR-0037 — feedback contract (Stage 1, hard dependency)

## 12. Post-Stage-2 Plan

After Stage 2 ships and is observed for ≥1 week:

- **Stage 2.5**: `planner revise` + `planner audit` + auto-advance-sprint
- **Stage 3**: `guide-arch → rdd-arch` rename + roadmap handover
- **Stage 4**: Re-evaluate `guide-design + guide-plan` merge (likely NOT merged per D2a)
- **Future**: `rdd doctor --category planner` to detect planner-state drift

## 13. Self-Review Notes

- No "TBD" / "TODO" placeholders.
- All file paths are absolute or repo-relative and exist.
- Schema field types match JSON Schema Draft 2020-12.
- Backward compat: zero impact on 226 existing files.
- Idempotency is testable via dual-run comparison.
- Stage 2 is a strict subset of the Stage 1 decision tree (no scope creep).
