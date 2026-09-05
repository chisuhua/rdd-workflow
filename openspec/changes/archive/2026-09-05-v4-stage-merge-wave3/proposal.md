# v4 Stage Merge Wave 3: Hard Removal

## Why

Wave 3 of the v4 stage-merge architecture (per spec §4.3 + ADR-0043).

Trigger conditions (per spec §4.3) — **OVERRIDDEN by user decision**:
- Primary: ≥4 calendar weeks since Wave 1 ship (≥2026-10-04) — NOT MET
- Secondary: shim usage zero for ≥7 consecutive days — NOT MET (Wave 2 just shipped)
- Tertiary: rdd doctor --check stage-merge zero users — NOT MET

User has explicitly authorized hard removal despite trigger conditions not
being met. This is acceptable for internal testing and decision validation,
but Wave 3 should not ship to production users until triggers are met.

## What changes

**DELETE** (legacy v3.0 5-phase artifacts):
- skills/guide-design/ (entire directory; ~21 files)
- skills/guide-plan/ (entire directory; ~15 files)
- skills/guide-ship/ (entire directory; ~12 files)
- tests/integration/test_guide_*.bats (~40-50 bats tests)
- tests/integration/test_legacy_guide_*_shim.bats (Wave 2 shim contract)
- _lib/shim_usage.py (telemetry no longer needed post-removal)

**UPDATE**:
- install.sh: drop guide-{design,plan,ship} from --global symlink list
- skills/INSTALL.md: drop guide-* entries (4-stage + verifier only)
- skills/_lib/discover_ship_changes.sh: drop guide-plan/guide-ship discovery
- skills/guide/scripts/scan-state.sh: drop guide-* stage refs
- _lib/cli/guide_cmd.py: recommend 4 stage skills (no guide-*)
- skills/guide/scripts/workflow_synthesizer.py: same
- tests/integration/test_global_install_external_project.bats: drop 4-skill, keep 3-stage + verifier
- AGENTS.md: drop 5-phase references
- README.md: update stage table (5-phase → 4-stage)
- docs/adr/README.md: add ADR-0044 (Wave 3 decision)
- rddf-session schema v3: drop guide-design/guide-plan/guide-ship stage fields

**NEW**:
- docs/adr/ADR-0044-v4-stage-merge-wave3-hard-removal.md (decision record)

## Impact

- v3.0 5-phase users (still on guide-* skills) will see error: skill not found
- v4.x 4-stage users continue to work normally
- Migration path documented in docs/migration-v3-to-v4.md (Wave 2)

Wave 3 ship gate: all 3 trigger conditions met + regression pass.
