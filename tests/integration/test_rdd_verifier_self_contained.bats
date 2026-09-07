#!/usr/bin/env bats
# test_rdd_verifier_self_contained.bats — ADR-0045 Task 12
#
# End-to-end exercise of the self-contained rdd-verifier pipeline:
#   fixture proposal → scan_queue/stage → simulated agent verdict writeback
#   → rddf rdd-verify picks up cache → state + exit code assertions.
#
# Cases:
#   1. all-pass verdict → passed + archive-ready, rc 0
#   2. gap-classified fail → failed, rc 1, route guide-ship
#   3. drift-classified fail → failed, rc 1, route guide-plan
#   4. proposal without AC section → stage/skip passthrough

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TEST_TMP="$(mktemp -d)"
  export TEST_TMP
  cd "$TEST_TMP"
  git init -q
  git config user.email "t@t"
  git config user.name "T"
  mkdir -p openspec/changes .rddf/state
  echo "init" > .init-marker
  git add .init-marker && git commit -q -m init
  export RDDF_PROJECT_ROOT="$TEST_TMP"
  unset SKIP_RDD_VERIFIER RDDF_VERIFIER_BYPASS_REASON 2>/dev/null || true
}

teardown() {
  rm -rf "$TEST_TMP"
}

_make_change() {
  local name="$1"
  git checkout -q -b "openspec/$name" 2>/dev/null || true
  mkdir -p "openspec/changes/$name"
  echo "- [x] task" > "openspec/changes/$name/tasks.md"
}

_seed_agent_cache() {
  # Simulates the agent's writeback per SKILL.md § LLM Verification Protocol
  local name="$1" status="$2" reasoning="$3"
  local sha
  sha=$(git rev-parse HEAD)
  cat > ".rddf/state/.ac-verdict-${name}.json" <<EOF
{"schema_version":2,"change":"$name","codebase_commit":"$sha","verdict":[
  {"ac_id":"AC-1","status":"$status","confidence":0.9,"evidence":[
    {"tool":"Grep","query":"def handler","result_summary":"found in api.py"}
  ],"reasoning":"$reasoning"}
],"ran_at":"2026-09-07T00:00:00Z","ran_by":"rdd-verifier",
 "verification_state":"$([ "$status" = pass ] && echo passed || echo failed)",
 "failed_acs":$([ "$status" = pass ] && echo "[]" || echo '["AC-1"]'),
 "implementation_ref":"openspec/$name"}
EOF
  # Append agent audit entry (JSONL)
  printf '{"ts":"2026-09-07T00:00:00Z","change_name":"%s","exit_code":%d,"llm_provider":"agent","verdict":[]}\n' \
    "$name" "$([ "$status" = pass ] && echo 0 || echo 1)" \
    >> ".rddf/state/.ac-verification.jsonl"
}

_setup_iteration() {
  local name="$1"
  cat > .rddf/state/iteration.json <<EOF
{"version":7,"changes":[{"name":"$name","status":"in_worktree",
  "tasks_done":1,"tasks_total":1}]}
EOF
}

@test "self-contained: all-pass verdict → passed, archive-ready, rc 0" {
  _make_change "ch-pass"
  printf '%s\n' "## 验收标准" "- AC-1: handler exists" > "openspec/changes/ch-pass/proposal.md"
  git add . && git commit -q -m "impl"
  _setup_iteration "ch-pass"
  # Stage context (Task 3 wrapper), then simulate agent writeback
  bash "$REPO_ROOT/skills/rdd-verifier/scripts/run_verification.sh" ch-pass
  [ -f ".rddf/state/rdd-verify-context-ch-pass.json" ]
  _seed_agent_cache "ch-pass" "pass" "Handler found in api.py"

  run rddf rdd-verify
  [ "$status" -eq 0 ]
  python3 -c "
import json, sys
d = json.load(open('.rddf/state/iteration.json'))
v = d['changes'][0]['verification']
assert v['state'] == 'passed', v
assert v['archive_ready'] is True, v
"
}

@test "self-contained: gap-classified fail → failed, route guide-ship, rc 1" {
  _make_change "ch-gap"
  printf '%s\n' "## 验收标准" "- AC-1: handler exists" > "openspec/changes/ch-gap/proposal.md"
  git add . && git commit -q -m "impl"
  _setup_iteration "ch-gap"
  bash "$REPO_ROOT/skills/rdd-verifier/scripts/run_verification.sh" ch-gap >/dev/null
  _seed_agent_cache "ch-gap" "fail" "Handler is missing from the implementation"

  run rddf rdd-verify
  [ "$status" -eq 1 ]
  python3 -c "
import json
d = json.load(open('.rddf/state/iteration.json'))
v = d['changes'][0]['verification']
assert v['state'] == 'failed', v
assert v['route'] == 'guide-ship', v
assert v['failed_acs'] == ['AC-1'], v
"
}

@test "self-contained: drift-classified fail → failed, route guide-plan, rc 1" {
  _make_change "ch-drift"
  printf '%s\n' "## 验收标准" "- AC-1: handler exists" > "openspec/changes/ch-drift/proposal.md"
  git add . && git commit -q -m "impl"
  _setup_iteration "ch-drift"
  bash "$REPO_ROOT/skills/rdd-verifier/scripts/run_verification.sh" ch-drift >/dev/null
  _seed_agent_cache "ch-drift" "fail" "Handler exists but does not match AC"

  run rddf rdd-verify
  [ "$status" -eq 1 ]
  python3 -c "
import json
d = json.load(open('.rddf/state/iteration.json'))
v = d['changes'][0]['verification']
assert v['route'] == 'guide-plan', v
"
}

@test "self-contained: no AC section → pass-through exit 0" {
  skip "Pass-through semantic for AC-less proposals is now exercised by \
`test_ac_verify_removed.bats` (exit 4 friendly-error stub) and by the \
rdd-verifier v2.0 stage protocol (`stage_verification_context` returns \
ac_count=0). Per remove-ac-verifier-completely (2026-09-07), the legacy \
`rddf ac-verify` shim was removed; this test's pass-through assertion \
no longer has a working code path. Tracked as legacy test, not deleted, \
to preserve historical context."
}
