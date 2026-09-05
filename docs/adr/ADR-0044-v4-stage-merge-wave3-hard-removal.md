# ADR-0044: v4 Stage Merge Wave 3 — Hard Removal of guide-* Skills

> **Status**: 已采纳 (2026-09-04)
> **Date**: 2026-09-04
> **决策者**: sisyphus + user override

## Context

Wave 3 of the v4 stage-merge architecture (per spec §4.3 + ADR-0043). Removes
all v3.0 5-phase artifacts now that Wave 1 (new skills) and Wave 2
(deprecation shim) have shipped.

**Trigger condition OVERRIDE**: Per spec §4.3, Wave 3 should not proceed until
**all 3** conditions hold:
1. ≥4 calendar weeks since Wave 1 ship (≥2026-10-04) — **NOT MET** (0 days elapsed)
2. `.shim-usage.jsonl` zero entries for ≥7 consecutive days — **NOT MET** (Wave 2 just shipped)
3. `rdd doctor --check stage-merge` zero users — **NOT MET** (no data yet)

User has explicitly authorized hard removal despite triggers not being met.
This ADR documents the override decision and the justification.

## Decision

Proceed with hard removal in Wave 3, on the rationale that:
- Internal testing and decision-validation use case
- All new functionality is in place (Wave 1+2 shipped)
- Migration documentation exists (Wave 2: `docs/migration-v3-to-v4.md`)
- Reversibility: v3.0 skills can be restored from git history if needed
- Real production users should NOT see Wave 3 until triggers are met
  (this is a "test/internal" deployment, not a public release)

### What gets DELETED

- `skills/guide-design/` (entire directory; ~21 files)
- `skills/guide-plan/` (entire directory; ~15 files)
- `skills/guide-ship/` (entire directory; ~12 files)
- `tests/integration/test_guide_*.bats` (17 test files)
- `tests/integration/test_legacy_guide_*_shim.bats` (1 file, Wave 2 contract)
- `_lib/shim_usage.py` (Wave 2 telemetry, no longer needed post-removal)
- `tests/unit/test_shim_usage.py` (7 tests for shim_usage)

### What gets UPDATED

- `install.sh`: drop guide-* from verbose usage text; SUB_SKILLS auto-loop
  picks up remaining skills automatically
- `skills/INSTALL.md`: drop guide-* entries (Wave 2 already did this)
- `tests/integration/test_global_install_external_project.bats`: replace
  4-stage skill list with 3-stage + verifier
- `AGENTS.md`: replace "5-phase v3.0+" with "4-stage v4.0+"
- `docs/adr/README.md`: add ADR-0044 entry

### What gets NOT UPDATED (deferred follow-up)

- `skills/_lib/discover_ship_changes.sh`: has `guide-plan/guide-ship` discovery
  patterns; runtime harmless if not triggered
- `skills/guide/scripts/scan-state.sh`: has guide-* stage references
- `_lib/cli/guide_cmd.py`: recommends guide-* skills
- `skills/guide/scripts/workflow_synthesizer.py`: same
- `README.md`: 5-phase references in user-facing copy

These are follow-up cleanup items that do not block Wave 3 ship. They
will be addressed in a separate `_chore(v3.0-cleanup):` commit to keep
this Wave focused on user-facing changes (skill + test deletion).

### What gets NEW

- `docs/adr/ADR-0044-v4-stage-merge-wave3-hard-removal.md` (this file)
- `openspec/changes/v4-stage-merge-wave3/{proposal,tasks}.md`

## Consequences

### Positive

- v3.0 5-phase architecture artifacts removed from main branch
- Old skills no longer discoverable via `skill_use("guide-*")` (error: not found)
- New 4-stage v4.x architecture is the only path forward
- Migration guide available at `docs/migration-v3-to-v4.md`
- Reduction in repo size (~76 files removed)

### Negative / Risks

- **Override of trigger conditions** — production users should NOT apply this
  branch until ≥4 weeks + zero shim usage for ≥7 days. This commit is for
  internal testing.
- **V3.0 skill references in remaining code** — `discover_ship_changes.sh`,
  `scan-state.sh`, `guide_cmd.py`, `workflow_synthesizer.py`, `README.md`
  still reference guide-* internally. They will silently no-op when the
  removed skills are invoked, but the references are dead code.
- **rddf-session intent mappings** — legacy `guide-design` / `guide-plan`
  / `guide-ship` intent names are no longer supported. Any session record
  using them will fail to resolve. Per spec §3.5, the Wave 2 shim mapped
  them to `rdd-builder`; in Wave 3 this shim is gone, so historical sessions
  lose their intent binding.
- **No automated rollback** — restoring v3.0 skills requires git revert
  + manual rebuild of test files.

### Compatibility

- ❌ `skill_use("guide-design")` → error: skill not found
- ❌ `skill_use("guide-plan")` → error: skill not found
- ❌ `skill_use("guide-ship")` → error: skill not found
- ❌ `rddf-session` intent `guide-design/plan/ship` → no resolution
- ✅ `skill_use("rdd-arch")` / `rdd-planner` / `rdd-builder` / `rdd-verifier` — unchanged
- ✅ `rddf builder run <change>` — unchanged
- ✅ `rddf planner status/sync/feedback/etc.` — unchanged
- ✅ `rddf rdd-verify` — unchanged

## References

- Spec §4.3: `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md`
- ADR-0043: `docs/adr/ADR-0043-rdd-workflow-v4-stage-merge.md` (Wave 1+2 decision)
- Migration guide: `docs/migration-v3-to-v4.md` (Wave 2)
- Wave 2 shim telemetry: `_lib/shim_usage.py` (Wave 2, now removed)

## Implementation

Single commit on `openspec/v4-stage-merge-wave3` branch:
- DELETE: 3 skill directories + 17 test files + 1 shim test + 2 shim libs (~76 files)
- UPDATE: install.sh + INSTALL.md + global install test + AGENTS.md + ADR README
- NEW: ADR-0044 + openspec/changes/v4-stage-merge-wave3/{proposal,tasks}.md

Follow-up: `_chore(v3.0-cleanup):` commit for dead-code references in
discover_ship_changes.sh, scan-state.sh, guide_cmd.py, workflow_synthesizer.py, README.md.