# rdd-planner Stage 1: Feedback Contract & ID Foundation — Design

**Date**: 2026-09-03
**Status**: Draft (awaiting user review)
**Author**: brainstorming session output (Sisyphus orchestration + Oracle review)
**Related ADRs**: ADR-0028 role-model, ADR-0034 rdd-verifier, ADR-0037 (to be created by this spec), ADR-0038 (deferred to Stage 2)
**Decisions Adopted**: D1a (4-phase progressive migration) + D2a (no design/plan merge) + D3a (rdd-arch slimming deferred to Stage 3)
**Supersedes**: None (additive contract; existing 226 `.rddf/improvements/*.md` files untouched)

## 1. Problem & Motivation

### 1.1 Observed gaps in current state

After auditing the codebase (see `bash` checks during brainstorming):

1. **Zero `roadmap_ref` in 226 existing improvement files** — proposal↔roadmap mapping is currently name-based or absent.
2. **Zero `## Feedback` sections** — no downstream consumer writes back to improvement files; current "approval" happens only via `proposal-suggestions.md` table edit.
3. **Zero `feedback` CLI** — `_lib/cli/` has 28 subcommands; none touches proposal feedback.
4. **30+ `iteration.corrupt.*` residual files** in `.rddf/state/` — direct evidence that multi-writer state files corrupt under concurrent writes.
5. **No stable ID linking improvement ↔ OpenSpec change ↔ AC verdict** — verifier currently key by name, which drifts after rename/archive.

### 1.2 Goal

Lay the **ID foundation** and **append-only feedback contract** that Stage 2 (`rdd-planner` as generator) and Stage 3 (`rdd-arch` renaming) will depend on, **without** committing to a six-phase architecture or merging `guide-design`+`guide-plan`.

This is the **smallest deliverable** that:
- Closes P3 (feedback ID) and P5 (revision loop termination) per Oracle review.
- Is fully backward compatible: no existing improvement file is modified.
- Can be adopted incrementally by `guide-design` / `guide-plan` / `rdd-verifier` over time.

### 1.3 Out of scope (explicit)

- ❌ `rdd-planner` skill implementation (Stage 2).
- ❌ `guide-arch → rdd-arch` rename or roadmap handover (Stage 3).
- ❌ `guide-design + guide-plan → rdd-builder` merge (Stage 4 — not happening per D2a).
- ❌ Modifying any existing `.rddf/improvements/*.md` file.
- ❌ Changing `proposal-suggestions.md` table format.
- ❌ Changing `proposal-approved.md` workflow.

## 2. Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Frontmatter schema for new improvements | Add `change:` (OpenSpec change name) + `revision_count` (int) + `max_revisions` (int, default 3) | Stable ID linking improvement↔change↔AC; aligned with verifier 3-retry ceiling (ADR-0034) |
| 2 | Feedback storage | Append-only `## Feedback` section in `.rddf/improvements/*.md` with strict write discipline | User chose option A; Oracle flagged merge-conflict risk → mitigated by single-writer CLI (D3) |
| 3 | Single writer of `## Feedback` | New `rddf feedback add` CLI is the only code path that may append | Prevents the 4 downstream skills (design/plan/ship/verifier) from racing on file edits |
| 4 | Loop termination | `revision_count` increments on each planner revise; `max_revisions=3` cap | Mirrors ADR-0034 verifier ceiling; forces human escalation at 3 |
| 5 | Change↔improvement ID resolution | improvement frontmatter `change:` is authoritative; fallback to basename equality if missing | New files use new contract; 226 existing files continue to work unchanged |
| 6 | Schema location | New `_lib/schemas/feedback_entry_schema.json` (v1) + extend improvement frontmatter schema (v2) | Follows existing `_lib/schemas/` convention; bump version per `iteration.json` precedent |
| 7 | Atomic writes | Use existing `_lib/core/atomic_write.py` + `_lib/core/lock.py` | Proven from existing state-vector implementation; prevents corruption |
| 8 | Backward compat | New fields are **opt-in**; missing `change:` / `revision_count` defaults to `0` / `3` | Zero risk to 226 existing files |
| 9 | CLI surface | `rddf feedback add <proposal> --from <src> --kind <k> --body @file [--ref-change <name>]` | Matches existing 28 CLI subcommand pattern in `_lib/cli/` |
| 10 | Testing | pytest unit + bats integration, all using `AC_LLM_MOCK`-style env vars (e.g., `RDD_PLANNER_MOCK=yes`) for CI; live tests opt-in | Mirrors ac-verifier testing convention (see `ac_verifier_mocks.py`) |

## 3. Architecture

### 3.1 Component diagram

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Downstream consumers (existing, no changes required yet)            │
│                                                                       │
│  guide-design ─┐                                                      │
│  guide-plan   ├─→ rddf feedback add <proposal> ...                    │
│  guide-ship   │            │                                          │
│  rdd-verifier ┘            ▼                                          │
│                  ┌─────────────────────┐                              │
│                  │ _lib/cli/feedback_  │  (NEW)                       │
│                  │     cmd.py          │                              │
│                  └─────────┬───────────┘                              │
│                            │                                          │
│                            ▼                                          │
│                  ┌─────────────────────┐                              │
│                  │ _lib/feedback_      │  (NEW)                       │
│                  │     appender.py     │                              │
│                  │   - validate        │                              │
│                  │   - check revision  │                              │
│                  │   - atomic write    │                              │
│                  └─────────┬───────────┘                              │
│                            │                                          │
│                            ▼                                          │
│        .rddf/improvements/<name>.md  (## Feedback section, append-only) │
│                                                                       │
│   ╔══════════════════════════════════════════════════════════════╗   │
│   ║ Atomic write via _lib/core/atomic_write.py + lock.py         ║   │
│   ║ (prevents the 30+ iteration.corrupt.* failure mode)          ║   │
│   ╚══════════════════════════════════════════════════════════════╝   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 File layout (additions only)

```text
_lib/
├── cli/
│   └── feedback_cmd.py                # NEW — rddf feedback add subcommand
├── feedback_appender.py               # NEW — append-only feedback writer
├── feedback_resolver.py               # NEW — proposal → change ID resolution
└── schemas/
    ├── feedback_entry_schema.json     # NEW — single feedback entry v1
    └── improvement_frontmatter_schema.json  # NEW — frontmatter fields (optional)

tests/
├── unit/
│   ├── test_feedback_appender.py      # NEW — pytest unit tests
│   └── test_feedback_resolver.py      # NEW
└── integration/
    └── test_feedback_cmd.bats         # NEW — bats CLI tests

docs/superpowers/specs/
└── 2026-09-03-rdd-planner-stage1-feedback-contract.md  # NEW (this file)

docs/adr/
└── ADR-0037-feedback-contract.md      # NEW — supersedes no existing ADR
```

### 3.3 Sequence: writing feedback

```text
User runs:
  $ rddf feedback add improve-foo \
      --from guide-design \
      --kind needs-revision \
      --body /tmp/feedback.md \
      --ref-change change-foo

Inside feedback_cmd.py:
  1. parse args → ProposalRef(name, change?, source, kind, body_text)
  2. resolve change via feedback_resolver:
     - if --ref-change: validate change exists in openspec/changes/
     - else: read improvement frontmatter, check `change:` field
     - else: fallback to basename equality (improvement name == change name)
  3. validate kind ∈ {needs-revision, ac-fail, rejected, blocked, noted}
  4. validate source ∈ {guide-design, guide-plan, guide-ship, rdd-verifier, human}
  5. delegate to feedback_appender.append_feedback():
     - acquire file lock (.rddf/improvements/<name>.md.lock)
     - read current file, parse frontmatter + body
     - check ## Feedback section exists; if not, append section header
     - increment revision_count if kind == needs-revision and last entry unresolved
     - if revision_count > max_revisions: return error "loop exceeded, escalate to human"
     - generate feedback_id = feedback-<UTC-date>-<seq>
     - append structured block under ## Feedback
     - atomic write back to disk
     - release lock
  6. print success summary with feedback_id, file path, revision_count
```

### 3.4 Improvement frontmatter v2 schema (additive)

```yaml
---
# Existing fields (unchanged, backward compat):
# priority, source, phase, category, type, created_at

# NEW fields (opt-in):
change: change-foo                            # OpenSpec change name (optional)
revision_count: 0                             # auto-managed by feedback_appender
max_revisions: 3                              # default 3, mirrors ADR-0034
last_feedback_id: feedback-20260903-001        # auto-managed
last_feedback_at: 2026-09-03T10:30:00+08:00   # auto-managed
feedback_status: none                         # none|needs-revision|rejected|resolved
---
```

**Default semantics** when fields missing: `revision_count=0`, `max_revisions=3`, `feedback_status=none`. All three are auto-managed by `feedback_appender`; users never edit them manually.

### 3.5 Feedback entry schema v1

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://rdd-workflow.local/schemas/feedback_entry_schema.json",
  "title": "FeedbackEntry",
  "type": "object",
  "required": ["feedback_id", "source", "kind", "created_at", "body"],
  "properties": {
    "feedback_id": {
      "type": "string",
      "pattern": "^feedback-[0-9]{8}-[0-9]{3,6}$",
      "description": "Globally unique within proposal; UTC date + monotonic seq"
    },
    "source": {
      "type": "string",
      "enum": ["guide-design", "guide-plan", "guide-ship", "rdd-verifier", "human"]
    },
    "kind": {
      "type": "string",
      "enum": ["needs-revision", "ac-fail", "rejected", "blocked", "noted"]
    },
    "ref_change": {
      "type": "string",
      "description": "OpenSpec change name (optional, for cross-reference)"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "body": {
      "type": "string",
      "minLength": 1,
      "maxLength": 10000
    },
    "resolution": {
      "type": "string",
      "enum": ["open", "resolved", "wont-fix"],
      "default": "open"
    },
    "resolved_at": {
      "type": "string",
      "format": "date-time"
    },
    "resolved_by": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### 3.6 Markdown rendering in `## Feedback`

```markdown
## Feedback

### feedback-20260903-001

- **source**: guide-design
- **kind**: needs-revision
- **created_at**: 2026-09-03T10:30:00+08:00
- **resolution**: open

#### Body

缺少对回归门失败 vs 新失败的区分规则。

#### Notes

- (planner 会在这里追加处理记录)
```

**Append discipline**:
- Each entry is a level-3 heading `### <feedback_id>`.
- Entries MUST be in chronological order (oldest first, newest last).
- Resolution changes are appended as `#### Notes` blocks, never editing prior entries.
- `feedback_appender` is the only code that writes here. Manual edits break the contract and are detected by `rdd doctor --category feedback` (deferred to Stage 2).

### 3.7 CLI surface

```bash
rddf feedback add <proposal-name> \
    --from <guide-design|guide-plan|guide-ship|rdd-verifier|human> \
    --kind <needs-revision|ac-fail|rejected|blocked|noted> \
    --body <text|@file> \
    [--ref-change <change-name>] \
    [--dry-run]

rddf feedback list <proposal-name>             # show all feedback entries
rddf feedback resolve <proposal-name> <id>     # mark entry resolved
rddf feedback show-schema                      # print JSON schema to stdout
```

**Exit codes**:
- `0` — success
- `1` — validation error (invalid source/kind, missing proposal, loop exceeded)
- `2` — I/O error (permission, disk full)
- `3` — lock contention (timeout acquiring `.lock` file)

### 3.8 Why a new schema version, not extending existing ones

`_lib/schemas/iteration.json` precedent: bumping version forces consumers to validate. By introducing `feedback_entry_schema.json v1` and extending improvement frontmatter to v2, we:
- Keep all 226 existing files on the v1 implicit frontmatter (no change).
- Make opt-in adoption explicit (new files declare `change:`).
- Give Stage 2 (planner) a clear contract to read from without grep-parsing.

## 4. Migration & Compatibility

### 4.1 Existing 226 files: zero impact

- Missing `change:` field → `feedback_resolver` falls back to basename equality.
- Missing `revision_count` → defaults to `0`.
- Missing `## Feedback` section → `feedback_appender` creates one on first write.
- All existing skills (`guide-design`, `rdd-doctor`, etc.) continue to work unchanged.

### 4.2 Consumer adoption (optional, post-Stage-1)

After Stage 1 ships, downstream skills **may** opt into the new CLI:

```python
# Before (existing):
write_text_to_improvement_file(...)

# After (opt-in):
from _lib.feedback_appender import append_feedback
append_feedback(
    proposal="add-foo",
    source="guide-design",
    kind="needs-revision",
    body="missing acceptance criteria",
    ref_change="add-foo",
)
```

No consumer is **required** to migrate in Stage 1. Stage 2 will introduce the first mandatory consumer (`rdd-planner`).

### 4.3 Loop termination enforcement

Per Oracle P5: when `revision_count > max_revisions`, `feedback_appender.append_feedback()` returns error code 1 with message:

```
Loop exceeded: revision_count=4 > max_revisions=3.
Escalate to human decision: defer, split, or reject.
Reference: ADR-0037 §3.6.
```

The CLI does NOT silently extend `max_revisions`. Users must manually edit the frontmatter or use `rddf feedback resolve` to clear open feedback before another revision can be recorded.

## 5. Testing Strategy

### 5.1 Unit tests (pytest, in `tests/unit/`)

| File | Test count target | Coverage |
|------|-------------------|----------|
| `test_feedback_appender.py` | ≥ 12 | atomic write, lock acquire, loop guard, schema validation, ID generation, missing section auto-create, frontmatter round-trip |
| `test_feedback_resolver.py` | ≥ 8 | explicit `--ref-change`, frontmatter `change:` field, basename fallback, missing improvement file, multiple changes per improvement |
| `test_feedback_cli.py` | ≥ 10 | arg parsing, dry-run, exit codes, schema output |

**CI default**: `RDD_PLANNER_MOCK=yes` (mirrors `AC_LLM_MOCK=yes`). All tests pass with no LLM/network dependency.

### 5.2 Integration tests (bats, in `tests/integration/`)

| File | Test count target | Coverage |
|------|-------------------|----------|
| `test_feedback_cmd.bats` | ≥ 8 | end-to-end CLI flow, lock contention, malformed input, JSON schema validation, regression test against the iteration-corrupt failure mode |

### 5.3 Live tests (opt-in, marked `@pytest.mark.live`)

Triggered by `RDD_PLANNER_LIVE=yes`:
- Concurrent writers from 4 simulated sources do not corrupt file (uses `&` + `wait`).
- Feedback ID collision check across 1000+ entries.

### 5.4 Regression gate

Per AGENTS.md "Archive 前全量回归门" rule: this change runs `./test.sh --full --regression` before merge. No new failures in `KNOWN_FAILURES.txt`.

## 6. Acceptance Criteria

Stage 1 is **done** when all are true:

- [ ] `_lib/cli/feedback_cmd.py` registered in `_lib/cli/__init__.py` + dispatchable as `rddf feedback ...`.
- [ ] `_lib/feedback_appender.py` exists with public `append_feedback()` function.
- [ ] `_lib/feedback_resolver.py` exists with public `resolve_change_id()` function.
- [ ] `_lib/schemas/feedback_entry_schema.json` v1 exists, validates against test fixtures.
- [ ] `_lib/schemas/improvement_frontmatter_schema.json` v2 exists (additive fields only).
- [ ] `tests/unit/test_feedback_*.py` ≥ 30 tests, all green under `RDD_PLANNER_MOCK=yes`.
- [ ] `tests/integration/test_feedback_cmd.bats` ≥ 8 tests, all green.
- [ ] `./test.sh --full --regression` exits 0 (no new failures vs baseline).
- [ ] `ADR-0037-feedback-contract.md` written and committed.
- [ ] All 4 CI quality gates (docs-audit → openspec-gate → ... → bats smoke) pass.
- [ ] One demo run recorded in `docs/superpowers/specs/2026-09-03-rdd-planner-stage1-feedback-contract.md` §7 (after-the-fact append).

## 7. Demo Run (record after implementation)

```bash
# Setup: create a test improvement file
mkdir -p .rddf/improvements
cat > .rddf/improvements/demo-improvements.md <<'EOF'
---
name: demo-improvements
priority: P2
source: human
created_at: 2026-09-03
---

# demo-improvements

## Background

Test fixture for feedback contract.

## Acceptance

- [ ] Feedback can be added.
EOF

# Run CLI
$ rddf feedback add demo-improvements \
    --from guide-design \
    --kind needs-revision \
    --body "缺少 planner 状态字段定义" \
    --ref-change demo-improvements

# Expected output:
# ✓ Feedback appended: feedback-20260903-001
#   File: .rddf/improvements/demo-improvements.md
#   Source: guide-design
#   Kind: needs-revision
#   Revision count: 1/3

# Verify the file
$ rddf feedback list demo-improvements
# feedback-20260903-001 | guide-design | needs-revision | open | 2026-09-03T10:30:00+08:00
```

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Concurrent writers still corrupt file despite atomic write | Use `_lib/core/lock.py` (proven in state-vector impl); add concurrent-write bats test as regression gate |
| Loop guard (`max_revisions=3`) too aggressive — users hit it on legitimate 4th revision | Document in `rddf feedback add --help`; users can edit frontmatter to raise cap; ADR-0037 §3.7 records this as deliberate design (mirrors verifier ceiling) |
| New `change:` field collides with existing frontmatter parsing in `propose` skill | `_lib/feedback_resolver` reads via PyYAML, NOT regex; propose skill unaffected (only reads name/title/sections) |
| 226 existing files lack `change:` field → resolver falls back to basename | Documented in §4.1; Stage 2 planner will backfill via `rddf planner sync` (out of Stage 1 scope) |
| Feedback append breaks existing skill that parses improvement markdown structure | Section header `## Feedback` is **append-only at end of file**; existing parsers (e.g., `add-improve`) read frontmatter + body via PyYAML, not line-by-line |

## 9. Non-Goals (explicit)

- ❌ Replacing or merging `guide-design` + `guide-plan` (Stage 4 — not happening per D2a).
- ❌ Renaming `guide-arch` to `rdd-arch` (Stage 3).
- ❌ Implementing `rdd-planner` (Stage 2).
- ❌ Modifying `.rddf/state/iteration.json` schema.
- ❌ Touching `proposal-suggestions.md` or `proposal-approved.md`.
- ❌ Auto-resolving feedback on approval (deferred; Stage 2 planner will own this).

## 10. Open Questions

1. **Should `feedback_appender` validate that `ref_change` exists in `openspec/changes/`?**
   - Proposal: Yes (cheap; prevents typo'd IDs). Resolver already opens the change dir.
   - Counter: Adds I/O on every feedback write.
   - **Recommendation**: Yes, in `--strict` mode (default OFF to keep writes fast).

2. **Should `revision_count` increment on `noted` kind, or only on `needs-revision`?**
   - Proposal: Only `needs-revision` and `ac-fail` count toward revision limit.
   - `noted` is informational and doesn't drive revise loops.

3. **Should we expose feedback read via API for `rdd-verifier` to query?**
   - Proposal: Stage 1 keeps it CLI/file-only. Stage 2 planner will add read API.
   - Verifier currently writes AC verdicts to `.rddf/state/.ac-verifier-report.json` (not feedback); cross-link is via `change:` field.

## 11. Related Files

- `_lib/cli/__init__.py` — register `feedback_cmd` subcommand
- `_lib/cli/roadmap_cmd.py` — reference for subcommand pattern
- `_lib/core/atomic_write.py` — atomic write primitive
- `_lib/core/lock.py` — file lock primitive
- `_lib/schemas/iteration_schema.json` — schema version bump precedent
- `tests/_lib/test_helper.bash` — bats helper integration
- `AGENTS.md` "Archive 前全量回归门" — regression gate rule
- `docs/adr/ADR-0028-role-model-per-phase.md` — role boundaries (planner must respect)
- `docs/adr/ADR-0034-rdd-verifier.md` — 3-retry ceiling precedent

## 12. Post-Merge Plan

After Stage 1 ships and is observed for ≥1 week in production:

- **Stage 2**: `rdd-planner` skill (3 commands: `sync` / `revise` / `audit`).
- **Stage 3**: `guide-arch → rdd-arch` rename + roadmap handover.
- **Stage 4**: Re-evaluate `guide-design + guide-plan` merge after ≥2 weeks of observation. **Likely outcome: NOT merged** per D2a.
- **Future**: `rdd doctor --category feedback` to detect manual edits to `## Feedback` regions.
