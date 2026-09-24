# Plan: complete-guide-orchestrator-flow

> **Status**: All Wave 2 implementation already done in session prior to archive.
> This plan reflects the actual work executed (Steps A.1–A.7, 2026-09-24).

## Overview

Complete the v4.2 guide-orchestrator minimal usage flow: the "guide is the only entry point" contract that was 95% architecturally complete (per ADR-0055) but only ~5% observable to users due to a root-cause enum gap and silent traceback swallowing.

## Tasks

### Task 1: W2.0 kind-enum root-cause fix ✅ DONE
- **Why**: `_VALID_KINDS` (`_types.py:27-30`) + `sessions_schema.json` enum (`46`) both missing `stage_builder`/`stage_verify`/`stage_quick`. `rddf_session_hook_entry` raised `RddfSessionError` (subclass `Exception`, not `ValueError`) on invalid kind; the entry heredoc only caught `ConflictError` (a subclass), letting the exception propagate as an uncaught traceback that bash reported as non-zero exit. **Net effect**: SKILL.md files called the hook with `stage_builder`, validation raised ValueError, traceback surfaced silently, neither `sessions.json` nor `events.jsonl` got written. This is why "events.jsonl 在生产路径几乎空" even though all 5 SKILL.md files had the hook call.
- **Files**:
  - `skills/rddf-session/scripts/rddf_session_pkg/_types.py:28-58` — `_VALID_KINDS`, `_KIND_ALIAS`, `HEARTBEAT_TIMEOUT_BY_KIND`
  - `_lib/schemas/sessions_schema.json:44-48` (kind enum), `:62-65` (intent enum), `:13` (version description)
  - `skills/rddf-session/scripts/rddf_session_pkg/_commands.py:86-110` — cross-stage singleton exemption (W2.0 + W2.1 extend; guide + 3 new can mix; arch family still singleton)
  - `skills/rddf-session/scripts/rddf_session_hooks.sh:284` — `parent_kind_map` extension
- **Test**: `tests/unit/test_valid_kinds_v4.py` (18 tests, 8-case cross-stage matrix + alias + parent map)
- **Done**: 2026-09-24, all 18 pass.

### Task 2: W2.1 hook fail-loud ✅ DONE
- **Why**: Hook entry heredoc silently swallowed non-`ConflictError` exceptions. After Task 1 added valid kinds, illegal kinds should fail loudly for diagnosability.
- **Files**:
  - `skills/rddf-session/scripts/rddf_session_hooks.sh:266` — import `RddfSessionError` (parent class)
  - `skills/rddf-session/scripts/rddf_session_hooks.sh:323-335` — split `except`:
    - `except ConflictError as e:` → exit 2 with resume/abandon hints (v3 unchanged)
    - `except RddfSessionError as e:` → exit 3 with `ERROR: <ClassName>: <msg>` to stderr (new fail-loud)
- **Test**: `tests/unit/test_hook_invalid_kind.py` (14 tests: bogus kind → exit 3 + stderr; valid kinds → exit 0; ConflictError → exit 2 unchanged; source-level pattern check)
- **Done**: 2026-09-24, all 14 pass.

### Task 3: W2.2 workflow_synthesizer consumes events.jsonl ✅ DONE
- **Why**: Guide menu showed only `sessions.json` state — no progress visible from `events.jsonl`. Users saw static panels.
- **Files**:
  - `_lib/workflow_synthesizer.py:146` — new `ChildProgress` dataclass
  - `_lib/workflow_synthesizer.py:211` — `WorkflowRecommendation.child_progress: Tuple[ChildProgress, ...] = ()` (default empty for backward compat)
  - `_lib/workflow_synthesizer.py:446-540` — `_active_stage_x_children` + `_read_events_for_children` helpers
    - **Zero-IO guard**: `if not active_children: return ()` before any IO
    - **MN1 schema tolerance**: `.get()` everywhere, `try/except` around `EventsLog.read_since`
    - Aggregation by `(session_id, kind)`; deterministic sort by `(kind, session_id)`
    - Detail format: `"{kind} 完成 {completed}/{started}"` (AC-G3)
- **Test**: `tests/unit/test_workflow_synthesizer_events.py` (14 tests: AC-G3 fixture, zero-IO guard, schema tolerance, deterministic order, cross-owner aggregation, writer/reader roundtrip)
- **Done**: 2026-09-24, all 14 pass.

### Task 4: W2.3 monitor Panel 5 — child progress ✅ DONE
- **Why**: Decision (per Oracle B-section): **extend** `rddf monitor --watch=N` to render child progress in Panel 5, **not** add new `guide_entry --watch` primitive (avoids overlapping watches).
- **File**: `_lib/cli/monitor_cmd.py:213-232` — new Panel 5 calls `synthesize(project_root).child_progress`, prints per-child detail + last_event_at, sentinel `(no active stage_X children)`, fallback `(child progress unavailable: <ExceptionType>: <msg>)`.
- **AC-G4 wording fix** (docs, not impl): monitor doesn't advance `last_seen_offset` (that's stage_guide's job). Wording corrected in `docs/adr/ADR-0056-guide-orchestrator-minimal-usage-flow.md:170` and `docs/architecture/guide-orchestrator-flow.md:314`.
- **Test**: `tests/unit/test_monitor_watch_child_progress.py` (7 tests: panel present, sentinel, single builder, multi-builder, --watch subprocess renders, synthesizer exception fallback, session pickup by monitor)
- **Done**: 2026-09-24, all 7 pass.

### Task 5: Documentation alignment (D1/D2/D4/D5) ✅ DONE
- ADR-0056 §决策 4 (rdd-quick exemption wording aligned with §决策 3)
- ADR-0056 决策 6 AC table (AC-G1 red→green, AC-G4 monitor-based, AC-G5 automated fixture)
- ADR-0056 Consequences (P0-1 → W2-W2 fix)
- arch doc §4.3 hook template (positional 5-arg, NOT named flags)
- arch doc §6.2 / §7.1 / §7.2 / §9.2 (test paths, AC table, maintenance list)
- improvement §In Scope / §缺失关键回路 / §Acceptance AC-G1 / §M3 / §M5 / §Wave 2 plan
- improvement §部分豁免:rdd-quick (D4 (b))
- improvement-suggestions.md (P0 摘要同步根因 + W2.0 done marker)
- W2.x 编号全档统一 (W2.0=kind-enum, W2.1=fail-loud)
- Verified grep: zero active-doc references to old P0-1 narrative or wrong test paths.

### Task 7: AC-G2/G5 E2E fixture ✅ DONE
- `tests/unit/test_full_pipeline_e2e.py` (6 tests):
  - AC-G2: 4 stages × entry + 3 synthetic events + close = ≥ 20 events.jsonl rows
  - AC-G5: 2-owner (guide + builder) visible in synthesizer.child_progress + monitor Panel 5
  - Regression: confirmed `tests/e2e/agent/test_multi_window_poll.bats` exists (per D5); old fabricated `tests/integration/test_real_two_owner_poll.bats` does NOT exist
- Full unit suite: 2922 pass, 3 skipped, 11 pre-existing warnings (zero regressions)
- Smoke bats: 9/9 pass
- Targeted integration: 76/76 pass

### Task 8: Wave 2.5 lifecycle close (this archive) ⏳ IN PROGRESS
- Resolve `feedback-20260924-001` (rddf feedback resolve)
- Phase 0 approve (this run) → proposal.md + spec.md populated
- Phase 1 plan generation (this run)
- Phase 2 execute (mark tasks complete; no further code changes)
- Phase 3 archive → openspec archive + worktree cleanup

## Pre-existing known limitation (out of scope)

- `rddf_session_hook_heartbeat` (hooks.sh:579-580) has a bash exit-code bug (`[ ... -ne 0 ] && return "$_exit"` returns 1 on success). 2 sub-phase bats tests fail because of this; tracked in `KNOWN_FAILURES.txt`. Recommend filing as separate rdd-quick improvement.

## AC Verification (lock-down summary)

- **AC-G1** (3 new kinds create sessions + phase_started events): `test_ac_g1_red_green.py` (11 tests) — red→green lock
- **AC-G2** (full pipeline → ≥20 events): `test_full_pipeline_e2e.py::test_full_pipeline_produces_at_least_20_events`
- **AC-G3** (synthesizer output contains "X 完成 N/M"): `test_workflow_synthesizer_events.py::test_two_children_five_events_renders_completed_over_total` + `test_detail_text_matches_ac_g3_pattern`
- **AC-G4** (monitor --watch re-renders + Panel 5 reflects new event): `test_monitor_watch_child_progress.py` (7 tests)
- **AC-G5** (multi-window visibility): `test_full_pipeline_e2e.py::test_two_owners_visible_in_workflow_synthesizer` + `..._in_monitor_panel` + Wave 1 `test_multi_window_poll.bats` (REAL-2P-1/2)