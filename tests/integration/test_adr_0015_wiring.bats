#!/usr/bin/env bats
# tests/integration/test_adr_0015_wiring.bats
#
# Regression tests for ADR-0015 wiring (change: refine-adr-0015-wiring).
#
# ADR-0015 §后续待办 第一条 specifies:
#   "guide-plan.md 在 Phase 4 调用 validate_report.write_report() 刷新 report 文件"
#
# This change wires `openspec validate <change> --json` into guide-plan.md
# Phase 4 (plan-done) and persists the result via
# `skills/_lib/validate_report.py::write_report()` to
# `.rddf/state/openspec-validate.json`.
#
# These tests lock the contract:
#   1. validate_report.write_report is importable (API surface stable)
#   2. ADR-0015 status field is "已采纳" (not "待定")
#   3. ADR-0015 has a 修订记录 section documenting this change
#   4. guide-plan.md Phase 4 contains the ADR-0015 wiring block
#   5. The wiring block uses Oracle C1-safe env-var passing (no bash string interp)
#   6. The wiring block is positioned between run_plan_done_gate and write_plan_handoff
#
# Run: bats tests/integration/test_adr_0015_wiring.bats

load ../test_helper

@test "adr_0015: validate_report.py has write_report function importable" {
  # Lock API surface: write_report must be a callable taking (project_root, raw_report)
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.validate_report import write_report, load_report, normalize_report
assert callable(write_report)
assert callable(load_report)
assert callable(normalize_report)
print('OK')
"
}

@test "adr_0015: validate_report.py REPORT_PATH_TEMPLATE is .rddf/state/openspec-validate.json" {
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib import validate_report
assert validate_report.REPORT_PATH_TEMPLATE == '.rddf/state/openspec-validate.json'
print('OK')
"
}

@test "adr_0015: ADR-0015 status is 已采纳" {
  grep -q "状态\*\*: 已采纳" "$REPO_ROOT/docs/adr/ADR-0015-integrate-openspec-validate-as-plan-critic.md"
}

@test "adr_0015: ADR-0015 has 修订记录 section" {
  grep -q "### 修订记录" "$REPO_ROOT/docs/adr/ADR-0015-integrate-openspec-validate-as-plan-critic.md"
}

@test "adr_0015: ADR-0015 修订记录 mentions refine-adr-0015-wiring change" {
  grep -q "refine-adr-0015-wiring" "$REPO_ROOT/docs/adr/ADR-0015-integrate-openspec-validate-as-plan-critic.md"
}

@test "adr_0015: guide-plan.md Phase 4 has ADR-0015 wiring marker" {
  grep -q "ADR-0015: Persist openspec validate report" "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "adr_0015: guide-plan.md wiring uses openspec validate positional arg (not --change)" {
  # Per openspec 1.4.1 CLI: `openspec validate <name> --json` (positional)
  # NOT `openspec validate --change <name> --json`
  grep -q 'openspec validate "$change_name" --json' "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "adr_0015: guide-plan.md wiring calls validate_report.write_report" {
  grep -q "from skills._lib.validate_report import write_report" "$REPO_ROOT/skills/guide-plan/SKILL.md"
  grep -q "write_report(" "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "adr_0015: guide-plan.md wiring uses Oracle C1 env-var pattern (PY_PROJECT_ROOT)" {
  # Oracle C1: PROJECT_ROOT passed via env var, NOT bash string interpolation
  grep -q "PY_PROJECT_ROOT=\"\$PROJECT_ROOT\"" "$REPO_ROOT/skills/guide-plan/SKILL.md"
  grep -q 'os.environ\["PY_PROJECT_ROOT"\]' "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "adr_0015: guide-plan.md wiring is positioned after run_plan_done_gate" {
  # Extract line numbers and assert ordering
  gate_line=$(grep -n "run_plan_done_gate || exit 1" "$REPO_ROOT/skills/guide-plan/SKILL.md" | head -1 | cut -d: -f1)
  wiring_line=$(grep -n "ADR-0015: Persist openspec validate report" "$REPO_ROOT/skills/guide-plan/SKILL.md" | head -1 | cut -d: -f1)
  handoff_line=$(grep -n "write_plan_handoff || exit 1" "$REPO_ROOT/skills/guide-plan/SKILL.md" | head -1 | cut -d: -f1)

  [ -n "$gate_line" ] || { echo "run_plan_done_gate not found"; return 1; }
  [ -n "$wiring_line" ] || { echo "wiring marker not found"; return 1; }
  [ -n "$handoff_line" ] || { echo "write_plan_handoff not found"; return 1; }

  echo "gate=$gate_line wiring=$wiring_line handoff=$handoff_line"
  [ "$gate_line" -lt "$wiring_line" ]
  [ "$wiring_line" -lt "$handoff_line" ]
}

@test "adr_0015: guide-plan.md wiring is non-fatal (uses warnings, not exit 1)" {
  # The wiring block must NOT use `exit 1` or `return 1` on failure
  # Extract the wiring block and verify no hard-fail
  wiring_block=$(awk '/ADR-0015: Persist openspec validate report/,/^fi$/' "$REPO_ROOT/skills/guide-plan/SKILL.md")
  [ -n "$wiring_block" ] || { echo "wiring block not found"; return 1; }

  # Verify the block contains non-fatal indicators
  echo "$wiring_block" | grep -q "non-fatal"
  echo "$wiring_block" | grep -q "⚠️"

  # Verify the block does NOT contain `exit 1` or `return 1`
  if echo "$wiring_block" | grep -qE '(exit 1|return 1)'; then
    echo "FAIL: wiring block contains hard-fail (exit 1 / return 1):"
    echo "$wiring_block" | grep -nE '(exit 1|return 1)'
    return 1
  fi
}

@test "adr_0015: guide-plan.md wiring has TODO comment about long-term merge with gate.py" {
  grep -q "TODO(long-term): merge with gate.py::_check_openspec_validate" "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "adr_0015: design.md exists for refine-adr-0015-wiring change" {
  [ -f "$REPO_ROOT/openspec/changes/refine-adr-0015-wiring/design.md" ]
}

@test "adr_0015: tasks.md exists for refine-adr-0015-wiring change" {
  [ -f "$REPO_ROOT/openspec/changes/refine-adr-0015-wiring/tasks.md" ]
}

@test "adr_0015: end-to-end write_report + load_report roundtrip works" {
  # Smoke test: write_report produces a loadable file
  tmp_root="$BATS_TMPDIR/adr_0015_roundtrip"
  mkdir -p "$tmp_root/.rddf/state"
  python3 -c "
import sys, json, os
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.validate_report import write_report, load_report
raw = {
    'items': [{'id': 'test-change', 'type': 'change', 'valid': True}],
    'summary': {'totals': {'items': 1, 'passed': 1, 'failed': 0}},
}
path = write_report('$tmp_root', raw)
assert path.endswith('.rddf/state/openspec-validate.json')
loaded = load_report('$tmp_root')
assert loaded is not None
assert loaded['passed'] is True
assert loaded['version'] == 1
assert loaded['failed_items'] == []
print('roundtrip OK')
"
  rm -rf "$tmp_root"
}
