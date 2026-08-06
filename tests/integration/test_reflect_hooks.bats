#!/usr/bin/env bats
# tests/integration/test_reflect_hooks.bats
#
# Integration tests for reflect_engine hooks in arch/plan/ship gate scripts.
# Verifies:
#   - SKIP_WORKFLOW_REFLECTION=1 disables all hooks
#   - Per-phase trigger logic works (ship/plan/arch)
#   - Timeout does not block analysis (non-blocking)
#   - Hook code present + guarded in 3 gate scripts

setup() {
  load ../test_helper
  load_lib reflect_hooks_helper

  # Use an isolated temp dir as project_root so dedup scanning does not
  # match real improvements/ files in the rdd-workflow repo itself.
  REFLECT_TMPDIR="$(mktemp -d)"
  export REFLECT_TMPDIR
}

teardown() {
  [ -n "${REFLECT_TMPDIR:-}" ] && rm -rf "$REFLECT_TMPDIR"
}

@test "reflect: SKIP_WORKFLOW_REFLECTION=1 disables all hooks" {
  SKIP_WORKFLOW_REFLECTION=1 python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.reflect_engine import ReflectEngine
e = ReflectEngine(phase='ship', project_root='$REFLECT_TMPDIR', dry_run=True)
r = e.analyze(failures=[{'type':'unrecovered_failure','error':'test'}])
assert r.action == 'skipped', f'expected skipped, got {r.action}'
"
}

@test "reflect: ship phase triggers on unrecovered_failure" {
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.reflect_engine import ReflectEngine
e = ReflectEngine(phase='ship', project_root='$REFLECT_TMPDIR', dry_run=True)
r = e.analyze(failures=[{'type':'unrecovered_failure','error':'timeout'}])
assert r.action == 'propose_issue', f'expected propose_issue, got {r.action} (reason={r.reason})'
"
}

@test "reflect: arch phase always log_friction" {
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.reflect_engine import ReflectEngine
e = ReflectEngine(phase='arch', project_root='$REFLECT_TMPDIR', dry_run=True)
r = e.analyze(failures=[{'type':'unrecovered_failure','error':'any'}])
assert r.action == 'log_friction', f'expected log_friction, got {r.action}'
"
}

@test "reflect: plan phase trigger on same root cause >= 2" {
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.reflect_engine import ReflectEngine
e = ReflectEngine(phase='plan', project_root='$REFLECT_TMPDIR', dry_run=True)
r = e.analyze(failures=[
  {'type':'gate_fail','gate':'plan-done','error':'quality-fail'},
  {'type':'gate_fail','gate':'plan-done','error':'quality-fail'},
])
assert r.action == 'propose_issue', f'expected propose_issue, got {r.action} (reason={r.reason})'
"
}

@test "reflect: timeout does not block analysis" {
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from unittest.mock import patch
from skills._lib.reflect_engine import ReflectEngine
e = ReflectEngine(phase='ship', project_root='$REFLECT_TMPDIR', timeout=0.01, dry_run=True)
with patch.object(e, '_do_analyze', side_effect=TimeoutError('simulated')):
    r = e.analyze(failures=[{'type':'unrecovered_failure','error':'test'}])
    assert r.action == 'error', f'expected error, got {r.action}'
    assert 'timeout' in r.reason.lower(), f'reason={r.reason}'
"
}

@test "reflect: hook code present in all 3 gate scripts" {
  for script in \
    "$REPO_ROOT/skills/guide-arch/scripts/write_arch_handoff.sh" \
    "$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh" \
    "$REPO_ROOT/_lib/archive.sh"; do
    assert_reflect_hook_present "$script"
    assert_skip_guard_present "$script"
    assert_non_blocking "$script"
  done
}
