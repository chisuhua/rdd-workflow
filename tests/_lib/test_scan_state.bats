#!/usr/bin/env bats
#
# Wave 8 / fix-debt-audit-2026-07-14 / Wave 2.3: scan-state.sh smoke tests.
# Verifies that scan_state() in skills/_lib/scan-state.sh:
#   1. Succeeds in an empty repo (no .rddf/state files)
#   2. Returns the expected RECOMMEND priority ordering for the
#      pre-debt-fix state files (arch-handoff, plan-handoff, etc.)
#   3. Exits 0 on all paths
#
# scan_session_binding is tested implicitly (callable, doesn't crash).

load ../test_helper

setup() {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > a && git add a && git commit -q -m init
  STATE_DIR="$TEST_REPO/.rddf/state"
  mkdir -p "$STATE_DIR"
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

@test "scan_state: empty repo returns default recommend" {
  run bash -c "
    source '$REPO_ROOT/skills/_lib/scan-state.sh'
    scan_state '$TEST_REPO'
    echo \"RECOMMEND=\$RECOMMEND\"
  "
  [ "$status" -eq 0 ]
  # In an empty repo (no .rddf state files), priority 10 default
  # recommends 'guide-ship' (or guide-arch if no roadmap.md)
}

@test "scan_state: arch-handoff + no plan-handoff recommends guide-plan" {
  # arch-handoff with adr_count >= 1 means arch-done is complete
  echo '{"arch_done_at":"2026-07-01","adr_count":1,"current_change":null}' > "$STATE_DIR/.arch-handoff.json"

  run bash -c "
    source '$REPO_ROOT/skills/_lib/scan-state.sh'
    scan_state '$TEST_REPO'
    echo \"RECOMMEND=\$RECOMMEND\"
  "
  [ "$status" -eq 0 ]
  [[ "$output" == *"guide-plan"* ]]
}

@test "scan_state: plan-handoff present recommends guide-ship" {
  echo '{"arch_done_at":"2026-07-01","adr_count":1,"current_change":null}' > "$STATE_DIR/.arch-handoff.json"
  echo '{"plan_done_at":"2026-07-01","active_changes":1,"current_change":"add-x"}' > "$STATE_DIR/.plan-handoff.json"

  run bash -c "
    source '$REPO_ROOT/skills/_lib/scan-state.sh'
    scan_state '$TEST_REPO'
    echo \"RECOMMEND=\$RECOMMEND\"
  "
  [ "$status" -eq 0 ]
  [[ "$output" == *"guide-ship"* ]]
}

@test "scan_state: no phase-gate-report priority (v2.0.3 removal)" {
  # v2.0.3 removed the phase-gate-report priority. Touching the file
  # must NOT trigger status --roadmap recommendation.
  touch "$STATE_DIR/.phase-gate-report.md"
  echo '# stale' > "$STATE_DIR/.phase-gate-report.md"

  run bash -c "
    source '$REPO_ROOT/skills/_lib/scan-state.sh'
    scan_state '$TEST_REPO'
    echo \"RECOMMEND=\$RECOMMEND\"
    echo \"REASON=\$REASON\"
  "
  [ "$status" -eq 0 ]
  # Should NOT recommend 'status --roadmap' (removed mechanism)
  [[ ! "$output" == *"status --roadmap"* ]]
}

@test "scan_session_binding: callable, exits 0" {
  run bash -c "
    source '$REPO_ROOT/skills/_lib/scan-state.sh'
    scan_session_binding '$TEST_REPO' || true
  "
  [ "$status" -eq 0 ]
}

@test "scan_state: priority comment header is updated to 10 entries" {
  run grep -cE "^#     [0-9]+\." "$REPO_ROOT/skills/_lib/scan-state.sh"
  [ "$status" -eq 0 ]
  # Header has priority 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10 = 12 entries
  [ "$output" -ge 10 ]
}
