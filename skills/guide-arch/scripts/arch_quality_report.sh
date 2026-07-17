#!/usr/bin/env bash
# skills/_lib/arch_quality_report.sh — extracted from guide-arch.md L564-L595
# Exports: run_arch_quality_report()
#
# Runs arch quality gate (4 warning-level checks) via ArchQualityReport.verify()
# and writes .rddf/state/.arch-quality-report.json.
# Honors STRICT_ARCH_GATE=yes env var to upgrade warnings to failures (exit 1).
#
# Oracle C1 safe: python3 - "$PROJECT_ROOT" arg-passing, PYEOF heredoc
# (no bash string interp into Python code).

run_arch_quality_report() {
  local PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT

  python3 - "$PROJECT_ROOT" <<'PYEOF'
import sys, json, os
sys.path.insert(0, sys.argv[1])
from skills._lib.arch_quality_gate import ArchQualityReport, is_strict_mode
project_root = sys.argv[1]
report = ArchQualityReport.verify(project_root)
out_path = os.path.join(project_root, ".rddf", "state", ".arch-quality-report.json")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "passed": report.passed,
        "warnings": report.warnings,
        "failed_checks": report.failed_checks,
        "detail": report.detail,
        "strict_mode": is_strict_mode(),
    }, f, ensure_ascii=False, indent=2)
if report.warnings or report.failed_checks:
    mode = "STRICT" if is_strict_mode() else "WARN"
    print(f"\n⚠️  架构质量门 ({mode}):")
    for w in report.warnings:
        print(f"  - [WARN] {w}: {report.detail[w].get('severity')}")
    for f in report.failed_checks:
        print(f"  - [FAIL] {f}: {report.detail[f].get('severity')}")
    if is_strict_mode():
        sys.exit(1)
else:
    print("\n✅ 架构质量门: 全部通过 (warning 级)")
PYEOF
}