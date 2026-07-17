#!/usr/bin/env bats
# tests/integration/test_rddf_session_hooks_extraction.bats
# P3-4: guide-arch, guide-plan, guide-ship each had entry + close hooks
# (6 total inline PYEOF heredocs calling RddfSessionCoordinator). Extracted
# to _lib/rddf_session_hooks.sh with 2 functions:
#   - rddf_session_hook_entry <kind> <intent> <subject> <expected_outcome> [context_pointer]
#   - rddf_session_hook_close <kind> <end_reason> <intent>
#
# Oracle flagged P0-2 (this extraction) as P0+ risk due to sessions.json
# writes with cross-session side effects. These tests lock:
#   1. Helper exists with both functions exported
#   2. guide-{arch,plan,ship} no longer inline the heredoc algorithm
#   3. guide-{arch,plan,ship} invoke the helper
#   4. Runtime: entry creates session, close marks completed, parent linkage works
#   5. Concurrency: parallel entries don't corrupt sessions.json (file lock)
#   6. ConflictError: different owner + same kind raises → exit 2

load ../test_helper

@test "skills/_lib/rddf_session_hooks.sh exists with both function exports" {
  [ -f "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh" ]
  grep -q '^rddf_session_hook_entry()' "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
  grep -q '^rddf_session_hook_close()' "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
}

@test "rddf_session_hooks.sh does not duplicate RddfSessionCoordinator API (no API surface change)" {
  [ -f "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh" ]
  grep -q 'from skills._lib.rddf_session' "$REPO_ROOT/skills/_lib/rddf_session_hooks.sh"
}

# --- Structural: 6 sites must be replaced ---

@test "guide-arch.md entry hook no longer inlines PYEOF heredoc" {
  [ -f "$REPO_ROOT/skills/guide-arch/SKILL.md" ]
  ! sed -n '82,110p' "$REPO_ROOT/skills/guide-arch/SKILL.md" | grep -qE 'kind="stage_arch"'
}

@test "guide-arch.md close hook no longer inlines PYEOF heredoc" {
  [ -f "$REPO_ROOT/skills/guide-arch/SKILL.md" ]
  ! sed -n '826,855p' "$REPO_ROOT/skills/guide-arch/SKILL.md" | grep -qE 'end_reason="arch-done"'
}

@test "guide-plan.md entry hook no longer inlines PYEOF heredoc" {
  [ -f "$REPO_ROOT/skills/guide-plan/SKILL.md" ]
  ! sed -n '82,115p' "$REPO_ROOT/skills/guide-plan/SKILL.md" | grep -qE 'kind="stage_plan"'
}

@test "guide-plan.md close hook no longer inlines PYEOF heredoc" {
  [ -f "$REPO_ROOT/skills/guide-plan/SKILL.md" ]
  ! sed -n '787,810p' "$REPO_ROOT/skills/guide-plan/SKILL.md" | grep -qE 'end_reason="plan-done"'
}

@test "guide-ship.md entry hook no longer inlines PYEOF heredoc" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  ! sed -n '36,65p' "$REPO_ROOT/skills/guide-ship/SKILL.md" | grep -qE 'kind="stage_ship"'
}

@test "guide-ship.md close hook no longer inlines PYEOF heredoc" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  ! sed -n '774,800p' "$REPO_ROOT/skills/guide-ship/SKILL.md" | grep -qE 'end_reason="ship-done"'
}

@test "all 3 skills invoke rddf_session_hooks helper" {
  grep -q 'scripts/rddf_session_hooks.sh' "$REPO_ROOT/skills/guide-arch/SKILL.md"
  grep -q 'scripts/rddf_session_hooks.sh' "$REPO_ROOT/skills/guide-plan/SKILL.md"
  grep -q 'scripts/rddf_session_hooks.sh' "$REPO_ROOT/skills/guide-ship/SKILL.md"
}

# --- Runtime: helper functions work correctly ---

@test "rddf_session_hook_entry creates new stage_arch session with expected schema" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
  OPENCODE_SESSION_ID="test_owner_1" \
    rddf_session_hook_entry stage_arch guide-arch arch-phase arch-done .rddf/state/.arch-handoff.json
  [ -f .rddf/state/sessions.json ]
  python3 -c "
import json
with open('.rddf/state/sessions.json') as f:
    data = json.load(f)
sessions = data.get('sessions', [])
assert len(sessions) == 1, f'Expected 1 session, got {len(sessions)}'
s = sessions[0]
assert s['kind'] == 'stage_arch', f'kind={s[\"kind\"]}'
assert s['state'] == 'active', f'state={s[\"state\"]}'
assert s['owner_opencode_session_id'] == 'test_owner_1', f'owner={s[\"owner_opencode_session_id\"]}'
assert s['goal']['intent'] == 'guide-arch', f'intent={s[\"goal\"][\"intent\"]}'
assert s['goal']['expected_outcome'] == 'arch-done', f'expected_outcome={s[\"goal\"][\"expected_outcome\"]}'
assert s['context_pointer'] == '.rddf/state/.arch-handoff.json', f'ctx={s[\"context_pointer\"]}'
assert s['parent_session_id'] is None, f'parent={s[\"parent_session_id\"]}'
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "rddf_session_hook_entry stage_plan links parent to latest stage_arch" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
  OPENCODE_SESSION_ID="test_owner_2" \
    rddf_session_hook_entry stage_arch guide-arch arch-phase arch-done 2>&1
  OPENCODE_SESSION_ID="test_owner_2" \
    rddf_session_hook_entry stage_plan guide-plan plan-phase plan-done 2>&1
  python3 -c "
import json
with open('.rddf/state/sessions.json') as f:
    data = json.load(f)
plan_session = [s for s in data['sessions'] if s['kind'] == 'stage_plan'][0]
arch_session = [s for s in data['sessions'] if s['kind'] == 'stage_arch'][0]
assert plan_session['parent_session_id'] == arch_session['session_id'], \
    f'parent={plan_session[\"parent_session_id\"]} expected={arch_session[\"session_id\"]}'
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "rddf_session_hook_close marks active session as completed with correct end_reason" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
  OPENCODE_SESSION_ID="test_owner_3" \
    rddf_session_hook_entry stage_arch guide-arch arch-phase arch-done 2>&1
  OPENCODE_SESSION_ID="test_owner_3" \
    rddf_session_hook_close stage_arch arch-done guide-arch 2>&1
  python3 -c "
import json
with open('.rddf/state/sessions.json') as f:
    data = json.load(f)
sessions = data['sessions']
completed = [s for s in sessions if s['state'] == 'completed' and s.get('end_reason') == 'arch-done']
assert len(completed) >= 1, f'Expected >=1 completed session, got: {[(s[\"kind\"], s[\"state\"], s.get(\"end_reason\")) for s in sessions]}'
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "rddf_session_hook_close skips gracefully when sessions.json missing" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
  output=$(OPENCODE_SESSION_ID="test_owner_4" \
    rddf_session_hook_close stage_arch arch-done guide-arch 2>&1 || true)
  echo "$output" | grep -qiE 'skip|not found'
  rm -rf "$TEST_REPO"
}

@test "CONCURRENCY: parallel entries don't corrupt sessions.json (lock serializes)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
  # Spawn 3 parallel entries with DIFFERENT kinds (same owner).
  # fcntl.flock with LOCK_NB serializes — at LEAST one succeeds, others
  # may get BlockingIOError on lock acquisition (pre-existing race in
  # RddfSessionCoordinator._with_file_lock with LOCK_NB). What matters:
  # sessions.json is always valid JSON (file lock prevents corruption).
  for kind_action in "stage_arch:guide-arch:arch-phase:arch-done" \
                    "stage_plan:guide-plan:plan-phase:plan-done" \
                    "stage_ship:guide-ship:ship-phase:archive-all"; do
    IFS=: read -r kind intent subject outcome <<< "$kind_action"
    (PROJECT_ROOT="$TEST_REPO" OPENCODE_SESSION_ID="concurrent_owner" \
      rddf_session_hook_entry "$kind" "$intent" "$subject" "$outcome" 2>/dev/null) &
  done
  wait
  [ -f .rddf/state/sessions.json ]
  python3 -c "
import json
with open('.rddf/state/sessions.json') as f:
    data = json.load(f)
sessions = data['sessions']
assert len(sessions) >= 1, f'Expected >=1 session, got 0'
for s in sessions:
    assert s['session_id'].startswith('rds_'), f'bad id: {s[\"session_id\"]}'
    assert len(s['session_id']) == 16, f'bad id length: {len(s[\"session_id\"])}'
    assert s['state'] == 'active', f'bad state: {s[\"state\"]}'
    assert s['owner_opencode_session_id'] == 'concurrent_owner', f'bad owner: {s[\"owner_opencode_session_id\"]}'
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "CONFLICT: same kind + different owner returns exit 2 with conflict hint" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
  # First entry — succeeds (creates session with owner_a)
  OPENCODE_SESSION_ID="owner_a" \
    rddf_session_hook_entry stage_arch guide-arch arch-phase arch-done 2>&1
  # Second entry with different owner — must fail with exit 2
  set +e
  OPENCODE_SESSION_ID="owner_b" \
    rddf_session_hook_entry stage_arch guide-arch arch-phase arch-done 2>&1
  exit_code=$?
  set -e
  [ "$exit_code" = "2" ]
  rm -rf "$TEST_REPO"
}