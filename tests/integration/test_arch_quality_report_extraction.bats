#!/usr/bin/env bats
# tests/integration/test_arch_quality_report_extraction.bats
# Round B extraction: guide-arch.md L564-L595 arch-quality-report invoker (~32 lines)
# extracted to skills/_lib/arch_quality_report.sh::run_arch_quality_report().
#
# Tests lock:
#   1. Helper file exists with run_arch_quality_report function.
#   2. guide-arch.md inline block markers removed.
#   3. guide-arch.md sources and invokes helper.
#   4. Helper writes JSON report with "passed" field when successful.

load ../test_helper

@test "arch_quality_report_helper_exists" {
  [ -f "$REPO_ROOT/skills/_lib/arch_quality_report.sh" ]
  bash -c "cd '$REPO_ROOT' && source skills/_lib/arch_quality_report.sh && declare -f run_arch_quality_report" | grep -q 'run_arch_quality_report'
}

@test "guide_arch_inline_quality_report_removed" {
  ! grep -q 'arch_quality_gate import ArchQualityReport' "$REPO_ROOT/skills/guide-arch.md"
}

@test "guide_arch_invokes_quality_report_helper" {
  grep -q 'source.*_lib/arch_quality_report.sh' "$REPO_ROOT/skills/guide-arch.md"
  grep -q 'run_arch_quality_report' "$REPO_ROOT/skills/guide-arch.md"
}

@test "run_arch_quality_report_creates_json_file" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/skills/_lib"
  mkdir -p "$tmpdir/.rddf/state"

  # Stub arch_quality_gate module so the import succeeds
  cat > "$tmpdir/skills/_lib/__init__.py" <<'PYEOF'
PYEOF
  cat > "$tmpdir/skills/_lib/arch_quality_gate.py" <<'PYEOF'
import json, os
from dataclasses import dataclass, field
@dataclass
class ArchQualityReport:
    passed: bool = True
    warnings: list = field(default_factory=list)
    failed_checks: list = field(default_factory=list)
    detail: dict = field(default_factory=dict)
    @classmethod
    def verify(cls, project_root):
        return cls(passed=True, warnings=[], failed_checks=[], detail={})
def is_strict_mode():
    return False
PYEOF

  bash -c "cd '$tmpdir' && PROJECT_ROOT='$tmpdir' bash -c \"source '$REPO_ROOT/skills/_lib/arch_quality_report.sh' && run_arch_quality_report\"" 2>&1 || true

  result=0
  if [ -f "$tmpdir/.rddf/state/.arch-quality-report.json" ]; then
    grep -q '"passed"' "$tmpdir/.rddf/state/.arch-quality-report.json" || result=1
  else
    result=1
  fi
  rm -rf "$tmpdir"
  [ "$result" -eq 0 ]
}
