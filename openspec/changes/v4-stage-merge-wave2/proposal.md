# v4 Stage Merge Wave 2: Deprecation Shim

## Why

Wave 2 of the v4 stage-merge architecture (per spec §4.2 + ADR-0043).

This Wave adds deprecation banners + shim routes so existing `guide-design` /
`guide-plan` / `guide-ship` skills continue to work while their users migrate
to `rdd-builder`. Old skills are preserved (not deleted); new users will
discover `rdd-builder` first.

Wave 3 (separate change) performs hard removal after ≥4 weeks + zero shim
usage telemetry for ≥7 consecutive days.

## What changes

**DEPRECATED banners** added to top 5 lines of:
- `skills/guide-design/SKILL.md`
- `skills/guide-plan/SKILL.md`
- `skills/guide-ship/SKILL.md`

**Shim routing** — `_lib/cli/{design,plan,ship}_cmd.py` modules modified to:
- Print stderr warning: `DEPRECATED: rddf guide-{design,plan,ship} → rddf builder. Shim will be removed in v4.x.2.`
- Append entry to `.rddf/state/.shim-usage.jsonl` (埋点 telemetry)
- Route to `rddf builder` CLI with appropriate args

**Telemetry file**: `.rddf/state/.shim-usage.jsonl` (append-only JSONL):
```json
{"timestamp": "2026-09-05T10:00:00Z", "source": "guide-design", "args": [...], "redirected_to": "rddf builder"}
```

**Migration doc**: `docs/migration-v3-to-v4.md` (NEW) — user-facing migration guide.

**Tests**:
- `tests/integration/test_legacy_guide_design_shim.bats` (≥3 tests)
- `tests/integration/test_legacy_guide_plan_shim.bats` (≥3 tests)
- `tests/integration/test_legacy_guide_ship_shim.bats` (≥3 tests)

## Impact

- Wave 1 (already merged): new skills available
- Wave 2 (this change): old skills continue working with deprecation warnings + telemetry
- Wave 3 (separate change): hard removal after trigger conditions
