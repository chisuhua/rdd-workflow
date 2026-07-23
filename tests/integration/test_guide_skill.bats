#!/usr/bin/env bats
# tests/integration/test_guide_skill.bats
#
# Structural / metadata coverage for skills/guide/SKILL.md.
# Locks the frontmatter (name + user-invocable), the "无状态/只读不写"
# self-declarations, the 6-priority scan (RECOMMEND= branches), and
# that all RECOMMEND values are valid delegations.
#
# Run: bats tests/integration/test_guide_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/guide/SKILL.md"
}

@test "guide_skill has correct frontmatter" {
  [ "$(skill_field "$f" name)" = "guide" ]
  [ "$(skill_meta_field "$f" user-invocable)" = "true" ]
}

@test "guide_skill declares itself interactive and read-only/no-openspec" {
  # v2.1: upgraded to interactive entry point — no longer claims "无状态推荐器"
  # but must still emphasize no file writes, no openspec CLI calls.
  grep -q '交互式' "$f"
  grep -q '不持久化' "$f"
  grep -q '不调用 openspec CLI' "$f"
  grep -q '不修改任何文件' "$f"
}

@test "guide_skill scan covers all priority branches (RECOMMEND count)" {
  # v2.0.3: 12 priority branches (1, 1.5, 2, 2.5, 3-10). phase-gate-report
  # (was branch 4) removed in v2.0.3 — see fix-debt-audit-2026-07-14.
  rec_count=$(grep -cE '^[[:space:]]*RECOMMEND=' "$REPO_ROOT/skills/guide/scripts/scan-state.sh")
  [ "$rec_count" -ge 11 ]
}

@test "guide_skill delegates only to 3-phase skills (RECOMMEND whitelist)" {
  # v2.0.1+: RECOMMEND assignments live in scan-state.sh, not guide.md.
  # Whitelist covers all 3-phase arch->plan->ship values + guide-spec alias.
  bad=$(grep -E '^[[:space:]]*RECOMMEND=' "$REPO_ROOT/skills/guide/scripts/scan-state.sh" | \
        grep -vE 'RECOMMEND="(guide-plan|guide-arch|guide-ship|status --roadmap)"' || true)
  [ -z "$bad" ]
}

@test "guide_skill integrates workflow_synthesizer with fallback to scan_state" {
  # v2.1: guide.md MUST call the Python synthesizer and retain scan_state
  # as fallback (backward compatibility). The synthesizer produces a
  # structured WorkflowRecommendation that overrides RECOMMEND/REASON
  # when Python is available; on any error, scan_state's baseline wins.
  local skill_file="$REPO_ROOT/skills/guide/SKILL.md"
  assert_file_exists "$skill_file"

  # Must reference the new synthesizer module
  assert_file_contains "$skill_file" "workflow_synthesizer"
  assert_file_contains "$skill_file" "synthesize"

  # Must retain scan_state fallback (backward compat)
  assert_file_contains "$skill_file" "scan_state"
  assert_file_contains "$skill_file" "scan-state.sh"

  # Must reference the RECOMMEND/REASON contract
  assert_file_contains "$skill_file" "RECOMMEND"
  assert_file_contains "$skill_file" "REASON"
}

@test "guide_skill synthesizer module exists and is importable" {
  # The synthesizer module MUST exist and import cleanly.
  local synth_file="$REPO_ROOT/skills/_lib/workflow_synthesizer.py"
  assert_file_exists "$synth_file"

  # Must import without error
  run python3 -c "import sys; sys.path.insert(0, '$REPO_ROOT'); from skills._lib.workflow_synthesizer import synthesize, WorkflowRecommendation, PhaseStatus; print('ok')"
  [ "$status" -eq 0 ]
  [ "$output" = "ok" ]
}
